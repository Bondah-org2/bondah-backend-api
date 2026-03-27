from .models import Notification, DeviceRegistration
from .firebase_utils import send_push_notification


def notify_user(user, title, message, data=None):
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
    ).values_list("push_token", flat=True)

    # 3. Send push notification to each device
    for token in tokens:
        send_push_notification(
            token=token,
            title=title,
            body=message,
            data=data or {},
        )

    return notification
