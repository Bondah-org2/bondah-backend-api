from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from dating.models import ProductRevenueRecord


class FraudService:

    MAX_DAILY_PRIVATE = 5

    @staticmethod
    def check_private_visibility(user):
        since = timezone.now() - timedelta(hours=24)

        count = ProductRevenueRecord.objects.filter(
            product_type="private_visibility",
            created_at__gte=since,
            bondmaker=user,
        ).count()

        if count > FraudService.MAX_DAILY_PRIVATE:
            raise ValidationError("Suspicious activity detected.")
