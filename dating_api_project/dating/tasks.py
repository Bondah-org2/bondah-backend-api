import logging

from celery import shared_task
from pybreaker import CircuitBreakerError

logger = logging.getLogger(__name__)
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Visibility, Notification, DeviceRegistration
from .brevo_utils import send_email
from django.template.loader import render_to_string
from django.conf import settings
from django.core.management import call_command


@shared_task
def expire_visibilities():
    """
    Converts approved visibilities to expired after expires_at.
    """
    expired_count = Visibility.objects.filter(
        status="approved", expires_at__lte=timezone.now()
    ).update(
        status="expired"
    )

    return f"{expired_count} visibilities expired."


@shared_task
def notify_user(user_id, title, message, data=None):
    from .firebase_utils import send_push_notification
    from .expo_utils import send_push_notification as expo_send_push_notif

    User = get_user_model()
    user = User.objects.get(id=user_id)
    # 1. Save notification in DB
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
    )

    # 2. Fetch active tokens for the user
    tokens = DeviceRegistration.objects.filter(
        user=user,
        is_active=True
    ).only("push_token", "token_type")

    # 3. Send push notification to each device
    for token in tokens:
        try:
            if token.token_type == "expo":
                expo_send_push_notif(
                    token=token.push_token,
                    title=title,
                    body=message,
                    data=data or {}
                )
            else:
                send_push_notification(
                    token=token.push_token,
                    title=title,
                    body=message,
                    data=data or {},
                )
        except CircuitBreakerError:
            logger.error("Firebase circuit breaker is open — push notification not sent to user %s", user_id)
            break
        except Exception as e:
            logger.error("Push notification failed for user %s: %s", user_id, e, exc_info=True)

    return notification.id

@shared_task
def send_otp_email(email, otp, user_name: str = "there", subject: str = "Verify your email"):
    html_body = render_to_string("emails/otp_verification.html", {"user_name": user_name, "otp_code": list(str(otp))})
    plain_text = (
        f"Hello {user_name}, \n\n"
        f"Your verification code is: {otp}\n\n"
        "If you didn't request this code, please ignore this email."
    )
    try:
        send_email(
            recipient_email=email,
            subject=subject,
            html_content=html_body,
            plain_text=plain_text,
        )
    except CircuitBreakerError:
        logger.error("Email circuit breaker is open — OTP email not sent to %s", email)
    except Exception as e:
        logger.error("Failed to send OTP email to %s: %s", email, e, exc_info=True)
        raise

@shared_task
def send_bondmaker_approval_email(name: str, email: str):
    html_body = render_to_string("emails/bondmaker_approval.html", {"bondmaker_name": name})
    plain_text = f"Hello {name}, \n\nYour BondMaker application has been accepted."
    try:
        send_email(
            recipient_email=email,
            subject="Your Bondmaker Application Has Been Approved 🎉",
            html_content=html_body,
            plain_text=plain_text,
        )
    except CircuitBreakerError:
        logger.error("Email circuit breaker is open — approval email not sent to %s", email)
    except Exception as e:
        logger.error("Failed to send approval email to %s: %s", email, e, exc_info=True)
        raise

@shared_task
def send_bondmaker_rejection_email(name: str, email: str, reason: str | None = "Portfolio did not meet current community standards."):
    html_body = render_to_string("emails/bondmaker_rejection.html", {"bondmaker_name": name, "reason": reason})
    plain_text = f"Hello {name}, \n\nYour BondMaker application has been rejected.\nReason: {reason or 'Not specified'}"
    try:
        send_email(
            recipient_email=email,
            subject="Your Bondmaker Application Has Been Rejected",
            html_content=html_body,
            plain_text=plain_text,
        )
    except CircuitBreakerError:
        logger.error("Email circuit breaker is open — rejection email not sent to %s", email)
    except Exception as e:
        logger.error("Failed to send rejection email to %s: %s", email, e, exc_info=True)
        raise


@shared_task
def send_password_reset_email(email, otp, user_name: str = "there", ip_address: str = "Unknown", user_agent: str = "Unknown device", reset_time: str = ""):
    html_body = render_to_string(
        "emails/password_reset.html",
        {
            "user_name": user_name,
            "otp_code": list(str(otp)),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "reset_time": reset_time,
        }
    )
    plain_text = (
        f"Hello {user_name},\n\n"
        f"Your password reset OTP is: {otp}\n\n"
        f"Request details:\n"
        f"  Time: {reset_time}\n"
        f"  IP Address: {ip_address}\n"
        f"  Device: {user_agent}\n\n"
        "If you didn't request this, please secure your account immediately."
    )
    try:
        send_email(
            recipient_email=email,
            subject="Reset Your Bondah Password",
            html_content=html_body,
            plain_text=plain_text,
        )
    except CircuitBreakerError:
        logger.error("Email circuit breaker is open — password reset email not sent to %s", email)
    except Exception as e:
        logger.error("Failed to send password reset email to %s: %s", email, e, exc_info=True)
        raise

@shared_task
def run_delete_underage_accounts():
    call_command("delete_underage_accounts")



CHAT_PUSH_PREVIEWS = {
    "image": "Sent a photo",
    "video": "Sent a video",
    "voice_note": "Sent a voice message",
}


def _chat_push_body(message):
    if message.message_type == "text":
        text = (message.content or "").strip()
        return text if len(text) <= 120 else f"{text[:117]}..."
    return CHAT_PUSH_PREVIEWS.get(message.message_type, "Sent a message")


@shared_task
def send_chat_message_push(message_id):
    """
    Push a new chat message to every other member's devices.

    Delivery itself never depends on this task: the message is already stored
    and every device catches up through sync. Skips members who muted the chat,
    turned push off, or have this chat open right now. Unlike notify_user, no
    Notification rows are written, so chats don't flood the notification inbox.
    """
    from exponent_server_sdk import (
        DeviceNotRegisteredError,
        PushClient,
        PushMessage,
        PushServerError,
    )
    from django.db.models import Q
    from requests.exceptions import ConnectionError as RequestsConnectionError, HTTPError

    from .firebase_utils import send_push_notification as send_fcm_push
    from .models import ChatParticipant, Message
    from .services import presence

    message = (
        Message.objects.select_related("sender", "chat")
        .filter(pk=message_id)
        .first()
    )
    if not message or message.is_deleted or message.sender_id is None:
        return 0

    chat = message.chat
    recipient_ids = list(
        chat.participants.exclude(id=message.sender_id).values_list("id", flat=True)
    )
    if not recipient_ids:
        return 0

    now = timezone.now()
    muted_ids = set(
        ChatParticipant.objects.filter(chat=chat, user_id__in=recipient_ids)
        .filter(Q(notifications_enabled=False) | Q(mute_until__gt=now))
        .values_list("user_id", flat=True)
    )
    push_off_ids = set(
        get_user_model()
        .objects.filter(id__in=recipient_ids, push_notifications_enabled=False)
        .values_list("id", flat=True)
    )
    targets = [
        uid
        for uid in recipient_ids
        if uid not in muted_ids
        and uid not in push_off_ids
        and not presence.is_viewing(uid, chat.id)
    ]
    if not targets:
        return 0

    title = message.sender.name or "New message"
    body = _chat_push_body(message)
    data = {
        "type": "chat_message",
        "chat_id": chat.id,
        "message_id": message.id,
        "seq": message.seq,
    }

    sent = 0
    devices = DeviceRegistration.objects.filter(user_id__in=targets, is_active=True)
    for device in devices:
        try:
            if device.token_type == "expo":
                response = PushClient().publish(
                    PushMessage(
                        to=device.push_token,
                        title=title,
                        body=body,
                        data=data,
                        sound="default",
                    )
                )
                # Raises DeviceNotRegisteredError for uninstalled apps
                response.validate_response()
            else:
                send_fcm_push(
                    token=device.push_token, title=title, body=body, data=data
                )
            sent += 1
        except DeviceNotRegisteredError:
            DeviceRegistration.objects.filter(pk=device.pk).update(is_active=False)
        except CircuitBreakerError:
            logger.error("Push circuit breaker open; chat push for message %s stopped", message_id)
            break
        except (PushServerError, RequestsConnectionError, HTTPError):
            logger.warning("Chat push failed for device %s", device.pk, exc_info=True)
        except Exception:
            logger.error("Unexpected chat push error for device %s", device.pk, exc_info=True)
    return sent
