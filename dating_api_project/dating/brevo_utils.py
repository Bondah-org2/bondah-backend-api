"""
Utilities for Brevo email service
"""

import logging
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from django.conf import settings

logger = logging.getLogger(__name__)


def send_email(recipient_email: str, subject: str, html_content: str, plain_text: str = ""):
    """
    Send a transactional email using Brevo API.
    """
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = settings.BREVO_API_KEY

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    try:
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": recipient_email}],
            sender={"email": settings.DEFAULT_FROM_EMAIL, "name": "Bondah"},
            subject=subject,
            html_content=html_content,
            text_content=plain_text,
        )
        api_instance.send_transac_email(send_smtp_email)
        logger.info(f"Email sent via Brevo to {recipient_email}")

    except ApiException as e:
        logger.error(f"Brevo API error sending to {recipient_email}: {e}", exc_info=True)
        raise


