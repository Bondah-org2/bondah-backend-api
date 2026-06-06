import logging

from celery import shared_task

logger = logging.getLogger(__name__)
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Visibility, Notification, DeviceRegistration
from .firebase_utils import send_push_notification
from .expo_utils import send_push_notification as expo_send_push_notif
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


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

    return notification.id

@shared_task
def send_otp_email(email, otp, user_name: str = "there", subject: str = "Verify your email"):
    # Render HTML
    html_body = render_to_string("emails/otp_verification.html", {"user_name": user_name, "otp_code": list(str(otp))})

    # Plain text fallback
    plain_text = (
        f"Hello {user_name}, \n\n"
        f"Your verification code is: {otp}\n\n"
        "If you didn't request this code, please ignore this email."
    )

    # Build and send email
    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain_text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email]
    )

    msg.attach_alternative(html_body, "text/html")
    msg.send()

@shared_task
def send_bondmaker_approval_email(name: str, email: str):
    # Render HTML
    html_body = render_to_string(
        "emails/bondmaker_approval.html",
        {"bondmaker_name": name}
    )

    plain_text = (
        f"Hello {name}, \n\n"
        f"Your BondMaker application have been accepted."
    )

    # Build and send email
    msg = EmailMultiAlternatives(
        subject="Your Bondmaker Application Has Been Approved 🎉",
        body=plain_text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email]
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()

@shared_task
def send_bondmaker_rejection_email(name: str, email: str, reason: str | None = "Portfolio did not meet current community standards."):
    # Render HTML
    html_body = render_to_string(
        "emails/bondmaker_rejection.html",
        {"bondmaker_name": name, "reason": reason}
    )

    plain_text = (
        f"Hello {name}, \n\n"
        f"Your BondMaker application have been rejected."
    )

    # Build and send email
    msg = EmailMultiAlternatives(
        subject="Your Bondmaker Application Has Been Rejected",
        body=plain_text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email]
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()


@shared_task
def send_password_reset_email(email, otp, user_name: str = "there", ip_address: str = "Unknown", user_agent: str = "Unknown device", reset_time: str = ""):
    # Render HTML
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

    msg = EmailMultiAlternatives(
        subject="Reset Your Bondah Password",
        body=plain_text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email]
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()

