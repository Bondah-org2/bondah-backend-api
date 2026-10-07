"""Seed the Pro and Prime store subscriptions sold through RevenueCat.

Product IDs are the same on both stores and must match App Store Connect,
Google Play and the RevenueCat offering. Prices are reference values; the app
shows the store's localized price. Older plans are deactivated, not deleted,
so existing subscription rows keep their plan.

Subscriptions without a store transaction are ended: before rebuild phase 0
any user could create an "active" subscription through the API without
paying, and those rows must not unlock the new paid features.
"""

from decimal import Decimal

from django.db import migrations

PLANS = [
    # product_id, tier, display name, duration, price, features
    ("bondah_pro_monthly", "pro", "Bondah Pro", "1_month", "9.99", False, False),
    ("bondah_pro_3month", "pro", "Bondah Pro", "3_months", "24.99", False, False),
    ("bondah_prime_monthly", "prime", "Bondah Prime", "1_month", "19.99", True, True),
    ("bondah_prime_3month", "prime", "Bondah Prime", "3_months", "49.99", True, True),
]


def seed(apps, schema_editor):
    SubscriptionPlan = apps.get_model("dating", "SubscriptionPlan")
    product_ids = []
    for product_id, tier, display, duration, price, read_receipt, global_access in PLANS:
        product_ids.append(product_id)
        SubscriptionPlan.objects.update_or_create(
            apple_product_id=product_id,
            defaults={
                "google_product_id": product_id,
                "name": tier,
                "display_name": display,
                "duration": duration,
                "price_usd": Decimal(price),
                "price_bondcoins": 0,
                "unlimited_swipes": True,
                "undo_swipes": True,
                "unlimited_unwind": False,
                "read_receipt": read_receipt,
                "global_access": global_access,
                "is_active": True,
            },
        )
    SubscriptionPlan.objects.exclude(apple_product_id__in=product_ids).update(is_active=False)


def end_unpaid_subscriptions(apps, schema_editor):
    from django.utils import timezone

    UserSubscription = apps.get_model("dating", "UserSubscription")
    UserSubscription.objects.filter(
        status="active", original_transaction_id__isnull=True
    ).update(status="expired", end_date=timezone.now(), auto_renew=False)


class Migration(migrations.Migration):

    dependencies = [
        ("dating", "0070_store_subscriptions"),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
        migrations.RunPython(end_unpaid_subscriptions, migrations.RunPython.noop),
    ]
