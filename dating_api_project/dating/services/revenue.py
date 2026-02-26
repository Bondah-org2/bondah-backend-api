from decimal import Decimal
from django.db import transaction
from dating.models import ProductRevenueRecord

COIN_USD_VALUE = Decimal("3.0")
PLATFORM_PERCENT = Decimal("0.70")


class RevenueEngine:

    @staticmethod
    def process(product_type, obj_id, bondmaker, coins):
        with transaction.atomic():

            real_revenue_usd = Decimal(coins) * COIN_USD_VALUE

            platform_share = (real_revenue_usd * PLATFORM_PERCENT).quantize(
                Decimal("0.01")
            )

            bondmaker_share = (real_revenue_usd - platform_share).quantize(
                Decimal("0.01")
            )

            ProductRevenueRecord.objects.create(
                product_type=product_type,
                object_id=obj_id,
                bondmaker=bondmaker,
                coins_used=coins,
                real_revenue_usd=real_revenue_usd,
                platform_share_usd=platform_share,
                bondmaker_share_usd=bondmaker_share,
            )

            return platform_share, bondmaker_share
