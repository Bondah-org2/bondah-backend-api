from .models import Notification
from .firebase_utils import send_push_notification


def notify_user(user, title, message, data=None):
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
    )

    send_push_notification(
        user,
        title=title,
        body=message,
        data=data or {},
    )

    return notification
