import requests
from django.core.exceptions import ValidationError
from .wallet_service import credit_wallet
from ..models import BondcoinPackage, WalletTransaction
from google.oauth2 import service_account
from googleapiclient.discovery import build
from django.conf import settings

APPLE_VERIFY_URL = "https://buy.itunes.apple.com/verifyReceipt"
GOOGLE_VERIFY_URL = (
    "https://androidpublisher.googleapis.com/androidpublisher/v3/applications"
)
APPLE_PROD_URL = "https://buy.itunes.apple.com/verifyReceipt"
APPLE_SANDBOX_URL = "https://sandbox.itunes.apple.com/verifyReceipt"

APPLE_SHARED_SECRET = "xxxx"
APPLE_BUNDLE_ID = "com.bondah.app"

GOOGLE_PACKAGE_NAME = "com.bondah.app"


def process_apple_purchase(user, receipt_data, package: BondcoinPackage):
    payload = {
        "receipt-data": receipt_data,
        "password": APPLE_SHARED_SECRET,
    }

    response = requests.post(APPLE_PROD_URL, json=payload)
    data = response.json()

    # If sandbox receipt sent to prod
    if data.get("status") == 21007:
        response = requests.post(APPLE_SANDBOX_URL, json=payload)
        data = response.json()

    if data.get("status") != 0:
        raise ValidationError("Invalid Apple receipt")

    latest_receipt = data["receipt"]["in_app"][-1]

    transaction_id = latest_receipt["transaction_id"]
    product_id = latest_receipt["product_id"]
    bundle_id = data["receipt"]["bundle_id"]

    # 1. Check bundle id
    if bundle_id != settings.APPLE_BUNDLE_ID:
        raise ValidationError("Invalid bundle id")

    # 2. Check product id matches package
    if product_id != package.apple_product_id:
        raise ValidationError("Product mismatch")

    # 3. Prevent duplicate
    if WalletTransaction.objects.filter(reference_id=transaction_id).exists():
        raise ValidationError("Duplicate Apple transaction")

    return transaction_id


def process_google_purchase(user, purchase_token, package: BondcoinPackage):
    credentials = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/androidpublisher"],
    )

    service = build("androidpublisher", "v3", credentials=credentials)

    result = (
        service.purchases()
        .products()
        .get(
            packageName=settings.GOOGLE_PACKAGE_NAME,
            productId=package.google_product_id,
            token=purchase_token,
        )
        .execute()
    )

    if result["purchaseState"] != 0:
        raise ValidationError("Invalid Google purchase")

    order_id = result["orderId"]

    if WalletTransaction.objects.filter(reference_id=order_id).exists():
        raise ValidationError("Duplicate Google transaction")

    return order_id
