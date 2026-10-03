from rest_framework import serializers
from dating.languages import SUPPORTED_LANGUAGES
from ..models import TranslationLog
from drf_spectacular.utils import extend_schema_field


class TranslationRequestSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=5000)
    source_language = serializers.CharField(required=False, default="auto")
    target_language = serializers.CharField()

    def validate_target_language(self, value):
        if value not in SUPPORTED_LANGUAGES:
            raise serializers.ValidationError(
                f"Unsupported language: {value}. Supported languages: {', '.join(SUPPORTED_LANGUAGES.keys())}"
            )
        return value

    def validate_source_language(self, value):
        if value not in SUPPORTED_LANGUAGES:
            raise serializers.ValidationError(
                f"Unsupported source language: {value}. Supported languages: {', '.join(SUPPORTED_LANGUAGES.keys())}"
            )
        return value


class TranslationResponseSerializer(serializers.ModelSerializer):
    source_language_name = serializers.SerializerMethodField()
    target_language_name = serializers.SerializerMethodField()

    class Meta:
        model = TranslationLog
        fields = [
            "id",
            "source_text",
            "translated_text",
            "source_language",
            "target_language",
            "source_language_name",
            "target_language_name",
            "character_count",
            "translation_time",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    @extend_schema_field(serializers.CharField())
    def get_source_language_name(self, obj) -> str:
        return SUPPORTED_LANGUAGES.get(obj.source_language, obj.source_language)

    @extend_schema_field(serializers.CharField())
    def get_target_language_name(self, obj) -> str:
        return SUPPORTED_LANGUAGES.get(obj.target_language, obj.target_language)


class SupportedLanguagesSerializer(serializers.Serializer):
    languages = serializers.DictField()


class TranslationStatsResponseSerializer(serializers.Serializer):
    total_translations = serializers.IntegerField()
    approved_translations = serializers.IntegerField()
    pending_translations = serializers.IntegerField()
    rejected_translations = serializers.IntegerField()
    user_id = serializers.IntegerField(required=False)
    username = serializers.CharField(max_length=150, required=False)

    class Meta:
        # Optional, for documentation or hints
        fields = [
            "total_translations",
            "approved_translations",
            "pending_translations",
            "rejected_translations",
            "user_id",
            "username",
        ]
