"""Seed the BondCoin catalog sold through RevenueCat.

Store product IDs are bondah_coins_<amount> on both stores; the same IDs must
exist in App Store Connect, Google Play and the RevenueCat offering. Prices
are $0.089 per coin and are a reference only: the app always shows the
store's localized price. Packages not in this list are deactivated, not
deleted, so old ledger rows keep their references.
"""

from decimal import Decimal

from django.db import migrations

COIN_PRICE_USD = Decimal("0.089")
PACKAGES = [10, 30, 50, 100, 300, 500, 800, 1200, 2000]
POPULAR = 100


def seed(apps, schema_editor):
    BondcoinPackage = apps.get_model("dating", "BondcoinPackage")
    product_ids = []
    for amount in PACKAGES:
        product_id = f"bondah_coins_{amount}"
        product_ids.append(product_id)
        BondcoinPackage.objects.update_or_create(
            apple_product_id=product_id,
            defaults={
                "name": f"{amount} BondCoins",
                "google_product_id": product_id,
                "bondcoin_amount": amount,
                "price_usd": (COIN_PRICE_USD * amount).quantize(Decimal("0.01")),
                "is_popular": amount == POPULAR,
                "is_active": True,
            },
        )
    BondcoinPackage.objects.exclude(apple_product_id__in=product_ids).update(is_active=False)


class Migration(migrations.Migration):

    dependencies = [
        ("dating", "0067_coin_escrow_revenuecat"),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
