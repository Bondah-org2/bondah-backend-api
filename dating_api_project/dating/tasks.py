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

