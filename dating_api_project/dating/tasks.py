from celery import shared_task
from django.utils import timezone
from .models import Visibility


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
