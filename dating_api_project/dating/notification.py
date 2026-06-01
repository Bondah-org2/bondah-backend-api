from .models import Notification, DeviceRegistration
from django.core.mail import send_mail
from django.conf import settings

def send_kyc_email(user, status, reason=None):
    try:
        if status == "approved":
            subject = "Bondmaker Application Approved 🎉"
            message = (
                f"Hello {user.name or 'User'},\n\n"
                "Congratulations! Your bondmaker application has been approved.\n"
                "You can now start using all bondmaker features.\n\n"
                "Best regards,\nYour Team"
            )
        else:
            subject = "Bondmaker Application Rejected"
            message = (
                f"Hello {user.name or 'User'},\n\n"
                "We regret to inform you that your bondmaker application was rejected.\n"
                f"Reason: {reason or 'Not specified'}\n\n"
                "You can reapply after making necessary corrections.\n\n"
                "Best regards,\nYour Team"
            )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

    except Exception as e:
        print("Email error:", e)
