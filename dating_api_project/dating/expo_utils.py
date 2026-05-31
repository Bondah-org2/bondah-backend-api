from .models import DeviceRegistration
import logging
import logging
from typing import Optional

from exponent_server_sdk import (
    PushClient,
    PushMessage,
    PushServerError,
    DeviceNotRegisteredError
)

logger = logging.getLogger(__name__)

def send_push_notification(token: str, title: str, body: str, data: Optional[dict] = None):
    """
    Sends a push notification to a specific Expo Push Token.
    """
    if not token:
        return None
    
    message = PushMessage(
            to=token,
            title=title,
            body=body,
            data=data
        )

    try:
        response = PushClient().publish(message)
        logger.info(f"Notification Status: {response.status}")
        return response
    
    except PushServerError as exc:
        # Handle formatting or validation errors
        logger.info(f"Server Error: {exc.errors}")
    
    except DeviceNotRegisteredError:
        # Clean up this token from your database; the user uninstalled the app
        DeviceRegistration.objects.filter(
            push_token=token,
            is_active=True
        ).update(is_active=False)

        logger.error("Device is no longer registered.")
    
    except Exception as e:
        logger.info(f"An unexpected error occurred: {e}")
