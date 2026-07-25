"""
Utilities for Brevo email service
"""

import logging
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from django.conf import settings

from .circuit_breakers import email_breaker


logger = logging.getLogger(__name__)


@email_breaker
def send_email(recipient_email: str, subject: str, html_content: str, plain_text: str = ""):
    """
    Send a transactional email using Brevo API.
    If BREVO_API_KEY is not configured, logs the email instead of sending it.
    """
    api_key = getattr(settings, "BREVO_API_KEY", None)
    if not api_key:
        logger.info(
            "[EMAIL LOG - no Brevo key] To: %s | Subject: %s | Body: %s",
            recipient_email,
            subject,
            plain_text or html_content,
        )
        return

    if not getattr(settings, "ENABLE_EMAIL_SENDING", False):
        logger.info(
            "[EMAIL LOG - sending disabled] To: %s | Subject: %s | Body: %s",
            recipient_email,
            subject,
            plain_text or html_content,
        )
        return

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = api_key

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


