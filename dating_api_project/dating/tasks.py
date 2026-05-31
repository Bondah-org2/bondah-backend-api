from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Visibility, Notification, DeviceRegistration
from .firebase_utils import send_push_notification
from .expo_utils import send_push_notification as expo_send_push_notif


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
