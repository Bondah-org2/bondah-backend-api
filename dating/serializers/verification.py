from rest_framework import serializers
from django.db import transaction
from ..models import LivenessVerification, UserVerificationStatus, DocumentVerification, SelfieVerification
from typing import List, Dict, Any

from ..media_refs import MediaRefsMixin


# =============================================================================
# DOCUMENT VERIFICATION SERIALIZERS (NEW FROM FIGMA)
# =============================================================================
class DocumentVerificationSerializer(serializers.ModelSerializer):
    """Serializer for document verification"""

    name = serializers.CharField(source="user.name", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    date_of_birth = serializers.DateField(source="user.date_of_birth", read_only=True)

    class Meta:
        model = DocumentVerification
        fields = [
            "id",
            "user",
            "name",
            "username",
            "document_type",
            "email",
            "date_of_birth",
            "status",
            "front_image_url",
            "back_image_url",
            "uploaded_at",
            "processed_at",
            "verified_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "user_name",
            "status",
            "uploaded_at",
            "verified_at",
            "updated_at",
        ]


class DocumentVerificationListSerializer(serializers.ModelSerializer):
    """Serializer for document verification"""

    user_name = serializers.CharField(source="user.name", read_only=True)
    date_of_birth = serializers.DateField(source="user.date_of_birth", read_only=True)
    relationship_status = serializers.CharField(
        source="user.relationship_status", read_only=True)
    qualification = serializers.CharField(
        source="user.education_level", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    profile_picture = serializers.URLField(
        source="user.profile_picture", read_only=True)

    class Meta:
        model = DocumentVerification
        fields = [
            "id",
            "user",
            "profile_picture",
            "user_name",
            "email",
            "date_of_birth",
            "status",
            "uploaded_at",
            "relationship_status",
            "qualification",
        ]
        read_only_fields = [
            "id",
            "user",
            "user_name",
            "email",
            "date_of_birth",
            "status",
            "uploaded_at",
            "experience",
            "relationship_status",
            "qualification",
        ]


class SelfieVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SelfieVerification
        fields = [
            "id",
            "selfie_image_url",
            "created_at",
        ]


class DocumentVerificationCreateSerializer(MediaRefsMixin, serializers.ModelSerializer):
    """Serializer for creating document verification requests"""

    media_ref_fields = {
        "front_image_url": ("id_document",),
        "back_image_url": ("id_document",),
    }

    front_image_url = serializers.CharField(max_length=500)
    back_image_url = serializers.CharField(max_length=500, required=False, allow_blank=True)

    class Meta:
        model = DocumentVerification
        fields = ["id",
                  "document_type",
                  "front_image_url",
                  "back_image_url",
                  ]

    def validate(self, attrs):
        user = self.context["request"].user

        from ..services import onboarding_service

        blocker = onboarding_service.apply_blocker(user)
        if blocker:
            raise serializers.ValidationError({"code": blocker[0], "detail": blocker[1]})

        if DocumentVerification.objects.filter(
            user=user,
            status__in=["pending", "approved"]
        ).exists():
            raise serializers.ValidationError(
                "You already have an active verification request"
            )

        # Runs the media reference checks from MediaRefsMixin
        return super().validate(attrs)

    def create(self, validated_data):
        """Create document verification with current user"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["user"] = request.user
        return super().create(validated_data)


class LivenessVerificationSerializer(serializers.ModelSerializer):
    """Serializer for Liveness Verification records"""

    user_email = serializers.EmailField(source="user.email", read_only=True)
    is_expired = serializers.SerializerMethodField()
    can_retry = serializers.SerializerMethodField()

    class Meta:
        model = LivenessVerification
        fields = [
            "id",
            "user",
            "user_email",
            "session_id",
            "status",
            "actions_required",
            "actions_completed",
            "confidence_score",
            "face_quality_score",
            "is_live_person",
            "spoof_detected",
            "spoof_type",
            "verification_method",
            "provider",
            "started_at",
            "completed_at",
            "expires_at",
            "attempts_count",
            "max_attempts",
            "is_expired",
            "can_retry",
        ]
        read_only_fields = [
            "user",
            "started_at",
            "completed_at",
            "confidence_score",
            "face_quality_score",
            "is_live_person",
            "spoof_detected",
            "provider",
        ]

    def get_is_expired(self, obj) -> bool:

        return obj.is_expired()

    def get_can_retry(self, obj) -> bool:

        return obj.can_retry()


class UserVerificationStatusSerializer(serializers.ModelSerializer):
    """Serializer for User Verification Status"""

    user_email = serializers.EmailField(source="user.email", read_only=True)
    verification_badges = serializers.SerializerMethodField()

    class Meta:
        model = UserVerificationStatus
        fields = [
            "id",
            "user",
            "user_email",
            "email_verified",
            "phone_verified",
            "liveness_verified",
            "identity_verified",
            "verification_level",
            "verified_badge",
            "trusted_member",
            "email_verified_at",
            "phone_verified_at",
            "liveness_verified_at",
            "created_at",
            "updated_at",
            "verification_badges",
        ]
        read_only_fields = [
            "user",
            "verification_level",
            "verified_badge",
            "created_at",
            "updated_at",
        ]

    def get_verification_badges(self, obj) -> List[Dict[str, Any]]:

        """Return user's verification badges for display"""
        badges = []
        if obj.email_verified:
            badges.append({"type": "email", "name": "Email Verified", "icon": "📧"})
        if obj.phone_verified:
            badges.append({"type": "phone", "name": "Phone Verified", "icon": "📱"})
        if obj.liveness_verified:
            badges.append(
                {"type": "liveness", "name": "Identity Verified", "icon": "✅"}
            )
        if obj.identity_verified:
            badges.append({"type": "full", "name": "Fully Verified", "icon": "🏆"})
        if obj.trusted_member:
            badges.append({"type": "trusted", "name": "Trusted Member", "icon": "⭐"})
        return badges


class SelfieSubmissionSerializer(MediaRefsMixin, serializers.ModelSerializer):
    media_ref_fields = {"selfie_image_url": ("selfie",)}

    document_verification_id = serializers.IntegerField(write_only=True)
    selfie_image_url = serializers.CharField(max_length=500)

    class Meta:
        model = SelfieVerification
        fields = [
            "id",
            "document_verification_id",
            "selfie_image_url",
            "status"
        ]
        read_only_fields = ["status"]

    def validate_document_verification_id(self, value):
        user = self.context["request"].user

        try:
            document = DocumentVerification.objects.get(id=value, user=user)
        except DocumentVerification.DoesNotExist:
            raise serializers.ValidationError("Invalid document verification")
        if document.status != "pending":
            # A reviewed ID can't take a new selfie; scan a new ID first
            raise serializers.ValidationError("This ID was already reviewed. Scan your ID again.")

        return document  # Return the document object itself

    def create(self, validated_data):
        user = self.context["request"].user
        document = validated_data.pop("document_verification_id")

        # Use transaction.atomic to prevent race conditions
        with transaction.atomic():
            # Check again inside transaction to prevent duplicates
            if SelfieVerification.objects.select_for_update().filter(
                user=user, document_verification=document
            ).exists():
                raise serializers.ValidationError(
                    "Selfie already submitted for this document"
                )

            selfie = SelfieVerification.objects.create(
                user=user,
                document_verification=document,
                status="pending",
                **validated_data
            )
        return selfie
