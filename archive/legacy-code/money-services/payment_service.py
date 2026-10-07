"""Store purchase verification for BondCoin packages.

Coins are credited through the ledger with the store's own transaction ID as
the idempotency key, so a receipt can only ever be redeemed once, by one
account. (Phase 1 of the rebuild moves this to RevenueCat webhooks.)
"""

import logging
from decimal import Decimal

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import BondcoinPackage, RevenueRecord
from . import wallet_service

logger = logging.getLogger(__name__)

# Apple and Google take 30% on most consumable sales. Phase 1 records the real
# fee per transaction from RevenueCat.
STORE_FEE_RATE = Decimal("0.30")


class PurchaseError(ValidationError):
    pass


# ---------------------------------------------------------------- Apple


def _post_apple(url, payload):
    try:
        response = requests.post(
            url, json=payload, timeout=settings.STORE_REQUEST_TIMEOUT_SECONDS
        )
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Apple receipt verification unreachable: %s", exc)
        raise PurchaseError("Could not reach the App Store. Please try again.")


def apple_transaction_ids(receipt_data: str, package: BondcoinPackage) -> list[str]:
    """Verify an App Store receipt and return the transaction IDs in it for this package."""
    if not receipt_data:
        raise PurchaseError("Missing App Store receipt.")
    if not package.apple_product_id:
        raise PurchaseError("This package is not available on the App Store.")

    payload = {
        "receipt-data": receipt_data,
        "password": settings.APPLE_SHARED_SECRET,
        "exclude-old-transactions": True,
    }
    data = _post_apple(settings.APPLE_PROD_URL, payload)
    if data.get("status") == 21007:  # sandbox receipt sent to production
        data = _post_apple(settings.APPLE_SANDBOX_URL, payload)

    if data.get("status") != 0:
        raise PurchaseError("Invalid App Store receipt.")

    receipt = data.get("receipt") or {}
    if receipt.get("bundle_id") != settings.APPLE_BUNDLE_ID:
        raise PurchaseError("Receipt is for a different app.")

    transaction_ids = [
        str(item["transaction_id"])
        for item in receipt.get("in_app", [])
        if item.get("product_id") == package.apple_product_id
        and item.get("transaction_id")
        and not item.get("cancellation_date")
    ]
    if not transaction_ids:
        raise PurchaseError("No purchase of this package was found in the receipt.")
    return transaction_ids


# ---------------------------------------------------------------- Google


def _google_purchases_api():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    credentials = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/androidpublisher"],
    )
    return build("androidpublisher", "v3", credentials=credentials, cache_discovery=False).purchases().products()


def google_order_id(user, purchase_token: str, package: BondcoinPackage, api=None) -> str:
    """Verify a Play purchase token and return its order ID."""
    if not purchase_token:
        raise PurchaseError("Missing Google Play purchase token.")
    if not package.google_product_id:
        raise PurchaseError("This package is not available on Google Play.")

    api = api or _google_purchases_api()
    try:
        result = api.get(
            packageName=settings.GOOGLE_PACKAGE_NAME,
            productId=package.google_product_id,
            token=purchase_token,
        ).execute()
    except Exception as exc:  # googleapiclient raises HttpError and transport errors
        logger.warning("Google purchase verification failed: %s", exc)
        raise PurchaseError("Could not verify the Google Play purchase.")

    if result.get("purchaseState") != 0:
        raise PurchaseError("This Google Play purchase is not completed.")

    # When the app tags purchases with the account ID, enforce it.
    account_id = result.get("obfuscatedExternalAccountId")
    if account_id and account_id != str(user.id):
        raise PurchaseError("This purchase belongs to another account.")

    order_id = result.get("orderId")
    if not order_id:
        raise PurchaseError("Google Play returned no order ID.")
    return order_id


def consume_google_purchase(purchase_token: str, package: BondcoinPackage, api=None) -> None:
    """Consume the purchase so it can be bought again and Google won't auto-refund it.

    Runs after the coins are credited; failure is logged, not raised, because the
    ledger key already prevents a second credit and the app retries consumption.
    """
    try:
        api = api or _google_purchases_api()
        api.consume(
            packageName=settings.GOOGLE_PACKAGE_NAME,
            productId=package.google_product_id,
            token=purchase_token,
        ).execute()
    except Exception as exc:
        logger.error("Google purchase consume failed for package %s: %s", package.id, exc)


# ---------------------------------------------------------------- fulfilment


def _credit_store_transaction(user, package, store: str, store_transaction_id: str) -> bool:
    """Credit one store transaction. Returns True if coins were added now."""
    with transaction.atomic():
        try:
            result = wallet_service.credit(
                user,
                package.bondcoin_amount,
                kind="purchase",
                idempotency_key=f"purchase:{store}:{store_transaction_id}",
                reference_id=store_transaction_id,
            )
        except ValidationError:
            # Already redeemed by another account: never credit it twice.
            logger.warning(
                "Store transaction %s:%s replayed by user %s",
                store, store_transaction_id, user.id,
            )
            return False

        if not result.created:
            return False

        amount_usd = package.price_usd
        store_fee = (amount_usd * STORE_FEE_RATE).quantize(Decimal("0.01"))
        RevenueRecord.objects.create(
            user=user,
            store=store,
            product_id=str(package.id),
            transaction_id=f"{store}:{store_transaction_id}",
            amount_usd=amount_usd,
            store_fee_usd=store_fee,
            net_revenue_usd=(amount_usd - store_fee).quantize(Decimal("0.01")),
            coins_awarded=package.bondcoin_amount,
        )
        return True


def fulfill_purchase(user, *, package, platform, receipt_data=None, purchase_token=None) -> int:
    """Verify a store purchase and credit its coins. Returns the coins added by this call."""
    if platform == "apple":
        transaction_ids = apple_transaction_ids(receipt_data, package)
        credited = sum(
            _credit_store_transaction(user, package, "apple", tx_id)
            for tx_id in transaction_ids
        )
        return credited * package.bondcoin_amount

    if platform == "google":
        api = _google_purchases_api()
        order_id = google_order_id(user, purchase_token, package, api=api)
        credited = _credit_store_transaction(user, package, "google", order_id)
        consume_google_purchase(purchase_token, package, api=api)
        return package.bondcoin_amount if credited else 0

    raise PurchaseError("Unsupported platform.")
