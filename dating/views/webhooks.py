import hmac
import logging

from django.conf import settings
from django.db import IntegrityError, transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import RevenueCatEvent
from ..tasks import process_revenuecat_event

logger = logging.getLogger(__name__)


@extend_schema(exclude=True)
class RevenueCatWebhookView(APIView):
    """Receives RevenueCat events. Stores each one, then applies it in Celery.

    Authenticated by the shared secret RevenueCat sends in the Authorization
    header. Answers 200 quickly (RevenueCat retries anything else), and a
    redelivered event is recognised by its ID and not applied twice.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        expected = settings.REVENUECAT_WEBHOOK_AUTH
        if not expected:
            logger.error("RevenueCat webhook called but REVENUECAT_WEBHOOK_AUTH is not set")
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)

        supplied = request.headers.get("Authorization", "")
        if supplied.startswith("Bearer "):
            supplied = supplied[len("Bearer "):]
        if not hmac.compare_digest(supplied.encode(), expected.encode()):
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        event = request.data.get("event") if isinstance(request.data, dict) else None
        if not isinstance(event, dict) or not event.get("id"):
            return Response({"detail": "Missing event."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                row = RevenueCatEvent.objects.create(
                    event_id=str(event["id"])[:100],
                    event_type=str(event.get("type", ""))[:50],
                    app_user_id=str(event.get("app_user_id") or "")[:255],
                    environment=str(event.get("environment") or "")[:20],
                    payload=request.data,
                )
                transaction.on_commit(lambda: process_revenuecat_event.delay(row.pk))
        except IntegrityError:
            pass  # redelivery of an event we already have

        return Response(status=status.HTTP_200_OK)
