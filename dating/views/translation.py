from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum
from rest_framework import status
from rest_framework import generics
from ..models import TranslationLog
from ..serializers import TranslationRequestSerializer, TranslationResponseSerializer, TranslationStatsResponseSerializer
from django.db.models import Avg
from deep_translator import GoogleTranslator
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from dating.openapi.response_serializers import CustomErrorResponseSerializer, SupportedLanguagesResponseSerializer
from django.db.models import Count


LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "auto": "Auto-detect",
    # ... include all other supported languages here
}


@extend_schema(
    tags=["Translation"],
    )
class TranslationView(generics.GenericAPIView):
    serializer_class = TranslationRequestSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=TranslationRequestSerializer,
        responses={
            200: TranslationResponseSerializer,
            500: CustomErrorResponseSerializer,
        },
        description="Translate text from source language to target language",
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data["text"]
        source = serializer.validated_data.get("source_language", "auto")
        target = serializer.validated_data["target_language"]

        try:
            # Perform translation
            translator = GoogleTranslator(source=source, target=target)
            translated_text = translator.translate(text)

            # Log translation
            log = TranslationLog.objects.create(
                source_text=text,
                translated_text=translated_text,
                source_language=source,
                target_language=target,
                character_count=len(text),
                translation_time=0,
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )

            response_serializer = TranslationResponseSerializer(log)
            return Response(
                {
                    "message": "Translation successful",
                    "status": "success",
                    "data": response_serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"message": f"Translation failed: {str(e)}", "status": "error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    operation_id="supported_languages",
    summary="Get supported languages",
    responses=SupportedLanguagesResponseSerializer,
)
def get(self, request, *args, **kwargs):
    translator = GoogleTranslator()
    languages = translator.get_supported_languages(as_dict=True)
    serializer = SupportedLanguagesResponseSerializer(
        {"languages": languages, "total": len(languages)}
    )
    return Response(
        {
            "message": "Supported languages retrieved",
            "status": "success",
            "data": serializer.data,
        },
        status=status.HTTP_200_OK,
    )


@extend_schema(
    tags=["Translation"],
    )
class TranslationHistoryView(generics.ListAPIView):
    """
    Retrieve the latest 50 translation logs.
    """

    serializer_class = TranslationResponseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Order by most recent and limit to 50
        return TranslationLog.objects.order_by("-created_at")[:50]

    @extend_schema(
        operation_id="translation_history",
        summary="Get latest translations",
        description="Retrieve the 50 most recent translation logs.",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "status": {"type": "string"},
                    "data": {
                        "type": "array",
                        "items": TranslationResponseSerializer,
                    },
                },
            }
        },
    )
    def list(self, request, *args, **kwargs):
        """Override list to include message and status in response"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "message": "History retrieved",
                "status": "success",
                "data": serializer.data,
            }
        )


@extend_schema(
    tags=["Translation"],
    )
class TranslationStatsView(APIView):
    @extend_schema(responses={200: TranslationStatsResponseSerializer})
    def get(self, request):
        # Aggregate statistics
        total_translations = TranslationLog.objects.count()
        total_characters = (
            TranslationLog.objects.aggregate(total_chars=Sum("character_count"))[
                "total_chars"
            ]
            or 0
        )
        avg_time = (
            TranslationLog.objects.aggregate(avg_time=Avg("translation_time"))[
                "avg_time"
            ]
            or 0
        )

        # Popular target languages
        popular_targets = (
            TranslationLog.objects.values("target_language")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        # Popular source languages
        popular_sources = (
            TranslationLog.objects.values("source_language")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        # Serialize language counts
        popular_targets_serialized = [
            {"language": item["target_language"], "count": item["count"]}
            for item in popular_targets
        ]
        popular_sources_serialized = [
            {"language": item["source_language"], "count": item["count"]}
            for item in popular_sources
        ]

        stats_data = {
            "total_translations": total_translations,
            "total_characters_translated": total_characters,
            "average_translation_time": round(avg_time, 3),
            "popular_target_languages": popular_targets_serialized,
            "popular_source_languages": popular_sources_serialized,
        }

        response_data = {
            "status": "success",
            "message": "Translation statistics retrieved successfully",
            "stats": stats_data,
        }

        # Use DRF serializer for consistent output & OpenAPI docs
        serializer = TranslationStatsResponseSerializer(response_data)
        return Response(serializer.data, status=status.HTTP_200_OK)
