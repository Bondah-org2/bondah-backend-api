from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from lang import SUPPORTED_LANGUAGES
from django.utils.timezone import now
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import make_password
from django.shortcuts import get_object_or_404
from django.db import transaction
from datetime import date
from rest_framework.validators import UniqueValidator
from django.db.models import Q
from .constants import QUESTION_UI_CONFIG
from .models import (
    User,
    NewsletterSubscriber,
    PuzzleVerification,
    Waitlist,
    Job,
    JobApplication,
    AdminUser,
    AdminOTP,
    TranslationLog,
    SocialAccount,
    DeviceRegistration,
    LocationHistory,
    UserMatch,
    LocationPermission,
    LivenessVerification,
    UserVerificationStatus,
    EmailVerification,
    PhoneVerification,
    UserRoleSelection,
    UserInterest,
    UserProfileView,
    UserInteraction,
    SearchQuery,
    RecommendationEngine,
    Chat,
    Message,
    VoiceNote,
    Call,
    ChatParticipant,
    ChatReport,
    Post,
    PostComment,
    PostInteraction,
    CommentInteraction,
    PostReport,
    Story,
    StoryView,
    StoryInteraction,
    PostShare,
    FeedSearch,
    LiveSession,
    LiveParticipant,
    UserSocialHandle,
    UserSecurityQuestion,
    DocumentVerification,
    SubscriptionPlan,
    UserSubscription,
    BondcoinPackage,
    WalletTransaction,
    Wallet,
    GiftCategory,
    VirtualGift,
    GiftTransaction,
    LiveGift,
    LiveJoinRequest,
    PaymentMethod,
    PaymentTransaction,
    PaymentWebhook,
    BondmakerSubscription,
    SuggestedMatch,
    Visibility,
    MatchRequest,
    Notification,
    PasswordResetOTP,
    Specialisation,
    BondCirclePost,
    BondCirclePostComment,
    BondCirclePostLike,
    BondCircle,
    BondCircleMember,
)
from drf_spectacular.utils import extend_schema_field
from typing import List, Dict, Any, Optional
from .location_utils import calculate_distance, calculate_match_score
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from .services.visibility_services import VisibilityService
from .notification import notify_user
from .models.username import (
    UsernameValidation,
    clean_and_validate_username,
    validate_username_format,
)


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "password",
            "gender",
            "age",
            "location",
            "is_matchmaker",
            "bio",
            "profile_picture",
            "profile_gallery",
            "education_level",
            "height",
            "zodiac_sign",
            "languages",
            "relationship_status",
            "smoking_preference",
            "drinking_preference",
            "pet_preference",
            "exercise_frequency",
            "have_kids",
            "personality_type",
            "love_language",
            "communication_style",
            "hobbies",
            "interests",
            "marriage_plans",
            "no_of_kids",
            "future_kids",
            "religion_importance",
            "religion",
            "dating_type",
            "open_to_long_distance",
            "looking_for",
            "push_notifications_enabled",
            "email_notifications_enabled",
            "preferred_language",
            "bondcoin_balance",
        ]
        read_only_fields = [
            "id",
            "bondcoin_balance",  # Financial data should be read-only
            "is_matchmaker",  # Admin privilege should be read-only
        ]

    def validate_profile_picture(self, value):
        """Validate profile picture URL for security"""
        if value:
            return self._validate_image_url(value, "profile_picture")
        return value

    def validate_bio(self, value):
        """Sanitize bio text for XSS prevention"""
        if value:
            return self._sanitize_text_input(value)
        return value

    def validate_name(self, value):
        """Sanitize name for XSS prevention"""
        if value:
            return self._sanitize_text_input(value)
        return value

    def _validate_image_url(self, url, field_name):
        """Common validation for image URLs"""
        import re
        from urllib.parse import urlparse

        if not url:
            return url

        # Check URL format
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise serializers.ValidationError(f"Invalid {field_name} URL format.")
        except Exception:
            raise serializers.ValidationError(f"Invalid {field_name} URL format.")

        # Allow only HTTPS
        if parsed.scheme != "https":
            raise serializers.ValidationError(f"{field_name} must use HTTPS protocol.")

        # Check for suspicious patterns
        suspicious_patterns = [
            r"\.exe$",
            r"\.bat$",
            r"\.cmd$",
            r"\.scr$",
            r"\.pif$",
            r"\.com$",
            r"\.vbs$",
            r"\.js$",
            r"\.jar$",
            r"<script",
            r"javascript:",
            r"data:",
            r"vbscript:",
        ]

        url_lower = url.lower()
        for pattern in suspicious_patterns:
            if re.search(pattern, url_lower):
                raise serializers.ValidationError(
                    f"Potentially malicious content detected in {field_name}."
                )

        # Check file extensions (allow common image formats)
        allowed_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]
        path_lower = parsed.path.lower()
        if not any(path_lower.endswith(ext) for ext in allowed_extensions):
            raise serializers.ValidationError(
                f"{field_name} must be a valid image file (jpg, png, gif, webp, bmp)."
            )

        return url

    def _sanitize_text_input(self, text):
        """Sanitize text input to prevent XSS attacks"""
        import re
        import html

        if not text:
            return text

        # Escape HTML entities
        text = html.escape(text, quote=True)

        # Remove or escape potentially dangerous patterns
        dangerous_patterns = [
            r"<script[^>]*>.*?</script>",  # Script tags
            r"javascript:",  # JavaScript URLs
            r"vbscript:",  # VBScript URLs
            r"data:",  # Data URLs
            r"on\w+\s*=",  # Event handlers
        ]

        for pattern in dangerous_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)

        return text

    def create(self, validated_data):
        # Set username to email if not provided
        if "username" not in validated_data or not validated_data.get("username"):
            validated_data["username"] = validated_data["email"]
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user


class NotificationSettingsSerializer(serializers.ModelSerializer):
    """Serializer for notification settings"""

    class Meta:
        model = User
        fields = ["push_notifications_enabled", "email_notifications_enabled"]

    def update(self, instance, validated_data):
        """Update notification settings"""
        instance.push_notifications_enabled = validated_data.get(
            "push_notifications_enabled", instance.push_notifications_enabled
        )
        instance.email_notifications_enabled = validated_data.get(
            "email_notifications_enabled", instance.email_notifications_enabled
        )
        instance.save()
        return instance


class LanguageSettingsSerializer(serializers.ModelSerializer):
    """Serializer for language settings"""

    class Meta:
        model = User
        fields = ["preferred_language"]

    def update(self, instance, validated_data):
        """Update language settings"""
        instance.preferred_language = validated_data.get(
            "preferred_language", instance.preferred_language
        )
        instance.save()
        return instance


# =============================================================================
# LIVE SESSION SERIALIZERS (NEW)
# =============================================================================


class LiveSessionSerializer(serializers.ModelSerializer):
    """Serializer for live sessions"""

    user_name = serializers.CharField(source="user.name", read_only=True)
    user_profile_picture = serializers.URLField(
        source="user.profile_picture", read_only=True
    )
    is_active = serializers.BooleanField(read_only=True)
    current_duration = serializers.DurationField(
        source="get_current_duration", read_only=True
    )

    class Meta:
        model = LiveSession
        fields = [
            "id",
            "user",
            "user_name",
            "user_profile_picture",
            "title",
            "description",
            "subject_matter",
            "start_time",
            "end_time",
            "status",
            "duration_limit_minutes",
            "viewers_count",
            "likes_count",
            "stream_url",
            "thumbnail_url",
            "is_active",
            "current_duration",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "user_name",
            "user_profile_picture",
            "start_time",
            "end_time",
            "viewers_count",
            "likes_count",
            "is_active",
            "current_duration",
            "created_at",
            "updated_at",
        ]


class LiveSessionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating live sessions"""

    class Meta:
        model = LiveSession
        fields = ["title", "description", "duration_limit_minutes"]

    def create(self, validated_data):
        """Create live session with current user"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["user"] = request.user
        return super().create(validated_data)


class LiveParticipantSerializer(serializers.ModelSerializer):
    """Serializer for live session participants"""

    user_name = serializers.CharField(source="user.name", read_only=True)
    user_profile_picture = serializers.URLField(
        source="user.profile_picture", read_only=True
    )

    class Meta:
        model = LiveParticipant
        fields = [
            "id",
            "session",
            "user",
            "user_name",
            "user_profile_picture",
            "role",
            "joined_at",
            "left_at",
        ]
        read_only_fields = [
            "id",
            "user_name",
            "user_profile_picture",
            "joined_at",
            "left_at",
        ]

    def create(self, validated_data):
        """Create participant with current user"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["user"] = request.user
        return super().create(validated_data)


# =============================================================================
# SOCIAL MEDIA HANDLES SERIALIZERS (NEW FROM FIGMA)
# =============================================================================


class UserSocialHandleSerializer(serializers.ModelSerializer):
    """Serializer for user social media handles"""

    class Meta:
        model = UserSocialHandle
        fields = ["id", "platform", "handle", "url", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserSocialHandleCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating user social media handles"""

    class Meta:
        model = UserSocialHandle
        fields = ["platform", "handle", "url"]

    def create(self, validated_data):
        """Create social handle with current user"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["user"] = request.user
        return super().create(validated_data)


# =============================================================================
# SECURITY QUESTIONS SERIALIZERS (NEW FROM FIGMA)
# =============================================================================


class UserSecurityQuestionSerializer(serializers.ModelSerializer):
    """Serializer for user security questions"""

    class Meta:
        model = UserSecurityQuestion
        fields = [
            "id",
            "question_type",
            "response_text",
            "response_choice",
            "is_public",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserSecurityQuestionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating user security question responses"""

    class Meta:
        model = UserSecurityQuestion
        fields = ["question_type", "response_text", "response_choice", "is_public"]

    def create(self, validated_data):
        """Create security question response with current user"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["user"] = request.user
        return super().create(validated_data)


# =============================================================================
# DOCUMENT VERIFICATION SERIALIZERS (NEW FROM FIGMA)
# =============================================================================


class DocumentVerificationSerializer(serializers.ModelSerializer):
    """Serializer for document verification"""

    user_name = serializers.CharField(source="user.name", read_only=True)
    is_verified = serializers.BooleanField(read_only=True)
    extracted_name = serializers.CharField(source="get_extracted_name", read_only=True)
    extracted_date_of_birth = serializers.CharField(
        source="get_extracted_date_of_birth", read_only=True
    )
    extracted_document_number = serializers.CharField(
        source="get_extracted_document_number", read_only=True
    )

    class Meta:
        model = DocumentVerification
        fields = [
            "id",
            "user",
            "user_name",
            "document_type",
            "status",
            "front_image_url",
            "back_image_url",
            "extracted_data",
            "verification_score",
            "is_authentic",
            "rejection_reason",
            "verification_service",
            "service_response",
            "uploaded_at",
            "processed_at",
            "verified_at",
            "updated_at",
            "is_verified",
            "extracted_name",
            "extracted_date_of_birth",
            "extracted_document_number",
        ]
        read_only_fields = [
            "id",
            "user",
            "user_name",
            "status",
            "extracted_data",
            "verification_score",
            "is_authentic",
            "rejection_reason",
            "service_response",
            "uploaded_at",
            "processed_at",
            "verified_at",
            "updated_at",
            "is_verified",
            "extracted_name",
            "extracted_date_of_birth",
            "extracted_document_number",
        ]


class DocumentVerificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating document verification requests"""

    front_image_url = serializers.URLField()
    back_image_url = serializers.URLField(required=False, allow_blank=True)

    class Meta:
        model = DocumentVerification
        fields = ["document_type", "front_image_url", "back_image_url"]

    def validate_front_image_url(self, value):
        """Validate front image URL for security"""
        return self._validate_image_url(value, "front_image_url")

    def validate_back_image_url(self, value):
        """Validate back image URL for security"""
        if value:
            return self._validate_image_url(value, "back_image_url")
        return value

    def _validate_image_url(self, url, field_name):
        """Common validation for image URLs"""
        import re
        from urllib.parse import urlparse

        # Check URL format
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise serializers.ValidationError(f"Invalid {field_name} URL format.")
        except Exception:
            raise serializers.ValidationError(f"Invalid {field_name} URL format.")

        # Allow only HTTPS
        if parsed.scheme != "https":
            raise serializers.ValidationError(f"{field_name} must use HTTPS protocol.")

        # Check for suspicious patterns
        suspicious_patterns = [
            r"\.exe$",
            r"\.bat$",
            r"\.cmd$",
            r"\.scr$",
            r"\.pif$",
            r"\.com$",
            r"\.vbs$",
            r"\.js$",
            r"\.jar$",
            r"<script",
            r"javascript:",
            r"data:",
            r"vbscript:",
        ]

        url_lower = url.lower()
        for pattern in suspicious_patterns:
            if re.search(pattern, url_lower):
                raise serializers.ValidationError(
                    f"Potentially malicious content detected in {field_name}."
                )

        # Check file extensions (allow common image formats)
        allowed_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]
        path_lower = parsed.path.lower()
        if not any(path_lower.endswith(ext) for ext in allowed_extensions):
            raise serializers.ValidationError(
                f"{field_name} must be a valid image file (jpg, png, gif, webp, bmp)."
            )

        return url

    def create(self, validated_data):
        """Create document verification with current user"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["user"] = request.user
        return super().create(validated_data)


# =============================================================================
# USERNAME VALIDATION SERIALIZERS (NEW FROM FIGMA)
# =============================================================================


class CreateUsernameSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=30)

    def validate_username(self, value):
        user = self.context["request"].user

        # User already has username
        if user.username:
            raise serializers.ValidationError(
                "Username is already set. You cannot change it here."
            )

        clean_username = value.strip().lstrip("@")

        # Validate format
        try:
            validate_username_format(clean_username)
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

        # Check availability
        is_valid, message, suggestions = UsernameValidation.validate_username(
            clean_username
        )

        # Attach result for use in create()
        self._username_check = {
            "is_valid": is_valid,
            "message": message,
            "suggestions": suggestions,
            "clean_username": clean_username,
        }

        return clean_username

    def create(self, validated_data):
        check = self._username_check
        user = self.context["request"].user

        # If username is taken → DO NOT create
        if not check["is_valid"]:
            raise serializers.ValidationError(
                {
                    "message": check["message"],
                    "suggestions": check["suggestions"],
                }
            )

        # Create username
        user.username = check["clean_username"]
        user.save(update_fields=["username"])

        return user


class UsernameUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username"]

    def validate_username(self, value):
        user = self.context["request"].user
        return clean_and_validate_username(value, exclude_user_id=user.id)


class NewsletterSubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscriber
        fields = ["id", "email", "date_subscribed"]
        read_only_fields = ["date_subscribed"]

    def to_representation(self, instance):
        # Return the exact message format the frontend expects
        return {"message": "Subscription successful!", "status": "success"}


class PuzzleVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PuzzleVerification
        fields = ["id", "user", "question", "user_answer", "is_correct"]
        read_only_fields = ["question", "is_correct"]


# class CoinTransactionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = CoinTransaction
#         fields = ["id", "user", "transaction_type", "amount", "created_at"]
#         read_only_fields = ["created_at"]


class WaitlistSerializer(serializers.ModelSerializer):
    firstName = serializers.CharField(source="first_name", write_only=True)
    lastName = serializers.CharField(source="last_name", write_only=True)

    class Meta:
        model = Waitlist
        fields = ["id", "firstName", "lastName", "email", "date_joined"]
        read_only_fields = ["date_joined"]

    def to_representation(self, instance):
        # Return the success message format as specified
        return {
            "message": "You've successfully joined the waitlist!",
            "status": "success",
        }


class NewsletterWelcomeEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    name = serializers.CharField(max_length=100, required=False, default="")


class WaitlistConfirmationEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    firstName = serializers.CharField(max_length=100)
    lastName = serializers.CharField(max_length=100)


class GenericEmailSerializer(serializers.Serializer):
    to_email = serializers.EmailField()
    subject = serializers.CharField(max_length=200)
    message = serializers.CharField()
    template_name = serializers.CharField(required=False, default="")


# class JobListSerializer(serializers.ModelSerializer):
#     jobType = serializers.CharField(source="job_type")
#     salaryRange = serializers.CharField(source="salary_range")
#     createdAt = serializers.DateTimeField(source="created_at")

#     class Meta:
#         model = Job
#         fields = [
#             "id",
#             "title",
#             "jobType",
#             "category",
#             "status",
#             "salaryRange",
#             "createdAt",
#         ]


class UserLoginRequestSerializer(serializers.Serializer):
    firebase_token = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(required=False)


class UserLogoutRequestSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(required=False)


# class JobDetailSerializer(serializers.ModelSerializer):
#     jobType = serializers.CharField(source="job_type")
#     salaryRange = serializers.CharField(source="salary_range")
#     createdAt = serializers.DateTimeField(source="created_at")

#     class Meta:
#         model = Job
#         fields = [
#             "id",
#             "title",
#             "jobType",
#             "category",
#             "status",
#             "description",
#             "location",
#             "salaryRange",
#             "requirements",
#             "createdAt",
#         ]


# class JobApplicationSerializer(serializers.ModelSerializer):
#     # Input fields (write)
#     jobId = serializers.IntegerField(write_only=True)
#     firstName = serializers.CharField(source="first_name")
#     lastName = serializers.CharField(source="last_name")
#     email = serializers.EmailField()
#     phone = serializers.CharField()
#     resumeUrl = serializers.URLField(
#         write_only=True, required=False, allow_blank=True, source="resume_url"
#     )
#     coverLetter = serializers.CharField(
#         write_only=True, required=False, allow_blank=True, source="cover_letter"
#     )
#     experienceYears = serializers.IntegerField(
#         source="experience_years", required=False
#     )
#     currentCompany = serializers.CharField(
#         source="current_company", required=False, allow_blank=True
#     )
#     expectedSalary = serializers.CharField(
#         source="expected_salary", required=False, allow_blank=True
#     )

#     # Output fields (read-only, camelCase)
#     appliedAt = serializers.DateTimeField(source="applied_at", read_only=True)
#     resumeUrlOut = serializers.SerializerMethodField()
#     coverLetterOut = serializers.SerializerMethodField()

#     class Meta:
#         model = JobApplication
#         fields = [
#             "id",
#             "jobId",
#             "firstName",
#             "lastName",
#             "email",
#             "phone",
#             "resumeUrl",
#             "coverLetter",
#             "resumeUrlOut",
#             "coverLetterOut",
#             "experienceYears",
#             "currentCompany",
#             "expectedSalary",
#             "status",
#             "appliedAt",
#         ]
#         read_only_fields = [
#             "id",
#             "status",
#             "appliedAt",
#             "resumeUrlOut",
#             "coverLetterOut",
#         ]

#     # Output camelCase methods
#     def get_resumeUrlOut(self, obj) -> str | None:
#         return obj.resume_url

#     def get_coverLetterOut(self, obj) -> str | None:
#         return obj.cover_letter

#     # Validation
#     def validate(self, data):
#         job_id = data.get("jobId") or data.get("job", {}).get("id")
#         try:
#             job = Job.objects.get(id=job_id)
#             if job.status != "open":
#                 raise serializers.ValidationError(
#                     "This job is not currently accepting applications."
#                 )
#         except Job.DoesNotExist:
#             raise serializers.ValidationError("Job not found.")

#         email = data.get("email")
#         if JobApplication.objects.filter(job=job, email=email).exists():
#             raise serializers.ValidationError("You have already applied for this job.")

#         data["job"] = job  # attach Job instance for creation
#         return data

#     # Ensure jobId is removed before saving
#     def create(self, validated_data):
#         validated_data.pop("jobId", None)
#         return super().create(validated_data)

#     # Optional: standard success response
#     def to_representation(self, instance):
#         return {
#             "message": "Job application submitted successfully!",
#             "status": "success",
#             "applicationId": instance.id,
#         }


class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class AdminOTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6)


class AdminTokenRefreshSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class AdminLogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(required=False)


class TokensSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


# class ResendOTPSerializer(serializers.Serializer):
#     type = serializers.ChoiceField(choices=["email", "phone"])
#     identifier = serializers.CharField(required=False)
#     phone_number = serializers.CharField(required=False)
#     country_code = serializers.CharField(default="+1", required=False)


class TokenRefreshRequestSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class FirebaseMatchSerializer(serializers.Serializer):
    matched_uid = serializers.CharField(
        max_length=128,
        required=True,
        help_text="Firebase UID of the user to match with",
    )

    def validate_matched_uid(self, value):
        # Optional: add custom validation rules, e.g., ensure UID format
        if not value.strip():
            raise serializers.ValidationError("matched_uid cannot be empty")
        return value


class AdminJobCreateSerializer(serializers.ModelSerializer):
    jobType = serializers.CharField(source="job_type")
    salaryRange = serializers.CharField(source="salary_range")
    requirements = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )

    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "jobType",
            "category",
            "status",
            "description",
            "location",
            "salaryRange",
            "requirements",
            "responsibilities",
            "benefits",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        # Convert requirements list to JSON
        requirements = validated_data.pop("requirements", [])
        job = Job.objects.create(**validated_data, requirements=requirements)
        return job


class AdminJobUpdateSerializer(serializers.ModelSerializer):
    jobType = serializers.CharField(source="job_type")
    salaryRange = serializers.CharField(source="salary_range")
    requirements = serializers.ListField(child=serializers.CharField(), required=False)

    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "jobType",
            "category",
            "status",
            "description",
            "location",
            "salaryRange",
            "requirements",
            "responsibilities",
            "benefits",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def update(self, instance, validated_data):
        # Handle requirements separately
        requirements = validated_data.pop("requirements", None)
        if requirements is not None:
            instance.requirements = requirements

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class AdminJobListSerializer(serializers.ModelSerializer):
    jobType = serializers.CharField(source="job_type")
    salaryRange = serializers.CharField(source="salary_range")
    applications_count = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "jobType",
            "category",
            "status",
            "location",
            "salaryRange",
            "applications_count",
            "created_at",
        ]

    def get_applications_count(self, obj) -> int:
        return obj.applications.count()


class AdminJobApplicationSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source="job.title", read_only=True)
    job_category = serializers.CharField(source="job.category", read_only=True)
    applicant_name = serializers.SerializerMethodField()

    class Meta:
        model = JobApplication
        fields = [
            "id",
            "job_title",
            "job_category",
            "applicant_name",
            "email",
            "phone",
            "experience_years",
            "current_company",
            "expected_salary",
            "status",
            "applied_at",
        ]
        read_only_fields = ["id", "applied_at"]

    def get_applicant_name(self, obj) -> str:

        return f"{obj.first_name} {obj.last_name}"


class AdminUpdateApplicationStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=JobApplication.STATUS_CHOICES)


class WaitlistEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Waitlist
        fields = "__all__"


class AdminJobApplicationDetailSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source="job.title", read_only=True)
    job_category = serializers.CharField(source="job.category", read_only=True)
    job_type = serializers.CharField(source="job.job_type", read_only=True)
    job_location = serializers.CharField(source="job.location", read_only=True)
    job_salary_range = serializers.CharField(source="job.salary_range", read_only=True)

    applicant_name = serializers.SerializerMethodField()

    class Meta:
        model = JobApplication
        fields = [
            "id",
            "job_title",
            "job_category",
            "job_type",
            "job_location",
            "job_salary_range",
            "applicant_name",
            "email",
            "phone",
            "cover_letter",
            "resume_url",
            "experience_years",
            "current_company",
            "expected_salary",
            "status",
            "applied_at",
            "updated_at",
        ]
        read_only_fields = ["id", "applied_at", "updated_at"]

    def get_applicant_name(self, obj) -> str:
        return f"{obj.first_name} {obj.last_name}"


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


# Custom Authentication Serializers for Mobile App
class CustomRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "email",
            "password",
            "password_confirm",
        )
        extra_kwargs = {
            "email": {"required": True},
            "name": {"required": True},
        }

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        # Generate a username if not provided
        username = validated_data.get("email") or validated_data.get("name")
        if not User.objects.filter(username=username).exists():
            print("Creating user...")
            user = User.objects.create_user(
                username=username, password=password, **validated_data
            )
            return user
        else:
            raise serializers.ValidationError('User Already exist')


class CustomLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
            user = authenticate(email=email, password=password)
            if not user:
                raise serializers.ValidationError("Invalid credentials.")
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled.")
            attrs["user"] = user
            return attrs
        else:
            raise serializers.ValidationError("Must include email and password.")


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("No user found with this email address.")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    reset_token = serializers.UUIDField()
    new_password = serializers.CharField(validators=[validate_password])
    new_password_confirm = serializers.CharField()

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match."}
            )
        return attrs

    def save(self, **kwargs):
        reset_token = self.validated_data["reset_token"]

        # Atomic operation to ensure the token is used only once
        with transaction.atomic():
            otp_record = get_object_or_404(
                PasswordResetOTP,
                reset_token=reset_token,
                is_used=True,  # Should already be used in OTP verification
            )

            user = User.objects.get(email=otp_record.email)
            user.set_password(self.validated_data["new_password"])
            user.save()

            # Invalidate token
            otp_record.reset_token = None
            otp_record.save()

        return user


class PasswordResetResendSerializer(serializers.Serializer):
    email = serializers.EmailField()


class OTPSerializer(serializers.Serializer):
    otp = serializers.CharField()


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "gender",
            "location",
            "is_matchmaker",
        )
        read_only_fields = ("id", "email", "is_matchmaker")


# class UserProfileUpdateSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = User
#         fields = ("name", "gender", "age", "location", "bio", "is_matchmaker")
#         read_only_fields = ("is_matchmaker",)  # Prevent privilege escalation

#     def validate_bio(self, value):
#         """Sanitize bio text for XSS prevention"""
#         if value:
#             return self._sanitize_text_input(value)
#         return value

#     def validate_name(self, value):
#         """Sanitize name for XSS prevention"""
#         if value:
#             return self._sanitize_text_input(value)
#         return value

#     def _sanitize_text_input(self, text):
#         """Sanitize text input to prevent XSS attacks"""
#         import re
#         import html

#         if not text:
#             return text

#         # Escape HTML entities
#         text = html.escape(text, quote=True)

#         # Remove or escape potentially dangerous patterns
#         dangerous_patterns = [
#             r"<script[^>]*>.*?</script>",  # Script tags
#             r"javascript:",  # JavaScript URLs
#             r"vbscript:",  # VBScript URLs
#             r"data:",  # Data URLs
#             r"on\w+\s*=",  # Event handlers
#         ]

#         for pattern in dangerous_patterns:
#             text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)

#         return text

#     def update(self, instance, validated_data):
#         for attr, value in validated_data.items():
#             setattr(instance, attr, value)
#         instance.save()
#         return instance


class SocialLoginSerializer(serializers.Serializer):
    provider = serializers.CharField()
    access_token = serializers.CharField()

    def validate_provider(self, value):
        if value not in ["google", "apple"]:
            raise serializers.ValidationError("Provider must be google or apple.")
        return value


class DeviceRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceRegistration
        fields = ["device_type", "push_token"]

    def validate_device_type(self, value):
        if value not in ["ios", "android"]:
            raise serializers.ValidationError("Device type must be ios or android.")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        DeviceRegistration.objects.update_or_create(
            push_token=validated_data["push_token"],
            defaults={
                "user": user,
                "device_type": validated_data.get("device_type"),
                "is_active": True,
            },
        )
        return validated_data


# OAuth Serializers
class GoogleOAuthSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    id_token = serializers.CharField(required=False)

    def validate_access_token(self, value):
        if not value or len(value) < 10:
            raise serializers.ValidationError("Invalid access token format.")
        return value


class AppleOAuthSerializer(serializers.Serializer):
    identity_token = serializers.CharField()
    authorization_code = serializers.CharField(required=False)
    user = serializers.JSONField(required=False)  # Apple user info

    def validate_identity_token(self, value):
        if not value or len(value) < 10:
            raise serializers.ValidationError("Invalid identity token format.")
        return value


class OAuthLoginSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=["google", "apple"])
    google_data = GoogleOAuthSerializer(required=False)
    apple_data = AppleOAuthSerializer(required=False)

    def validate(self, attrs):
        provider = attrs.get("provider")

        if provider == "google":
            google_data = attrs.get("google_data")
            if not google_data:
                raise serializers.ValidationError(
                    "Google data is required for Google OAuth."
                )
            if not google_data.get("access_token"):
                raise serializers.ValidationError("Google access token is required.")
        elif provider == "apple":
            apple_data = attrs.get("apple_data")
            if not apple_data:
                raise serializers.ValidationError(
                    "Apple data is required for Apple OAuth."
                )
            if not apple_data.get("identity_token"):
                raise serializers.ValidationError("Apple identity token is required.")

        return attrs


class SocialAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialAccount
        fields = ["id", "provider", "provider_user_id", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class UserProfileWithSocialSerializer(serializers.ModelSerializer):
    social_accounts = SocialAccountSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "gender",
            "age",
            "location",
            "bio",
            "is_matchmaker",
            "social_accounts",
        ]
        read_only_fields = ["id", "email"]


class OAuthLinkSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=["google", "apple"])
    access_token = serializers.CharField(required=False)
    identity_token = serializers.CharField(required=False)

    def validate(self, attrs):
        provider = attrs.get("provider")

        if provider == "google" and not attrs.get("access_token"):
            raise serializers.ValidationError(
                "Access token is required for Google OAuth."
            )
        elif provider == "apple" and not attrs.get("identity_token"):
            raise serializers.ValidationError(
                "Identity token is required for Apple OAuth."
            )

        return attrs


# Location Serializers
class LocationUpdateSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=10, decimal_places=8, required=True)
    longitude = serializers.DecimalField(max_digits=11, decimal_places=8, required=True)
    accuracy = serializers.FloatField(required=False, allow_null=True)
    source = serializers.ChoiceField(
        choices=["gps", "network", "manual", "ip"], default="gps"
    )

    def validate_latitude(self, value):
        if not (-90 <= value <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if not (-180 <= value <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value


class AddressGeocodeSerializer(serializers.Serializer):
    address = serializers.CharField(max_length=500, required=True)

    def validate_address(self, value):
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Address must be at least 3 characters long."
            )
        return value.strip()


class LocationPrivacyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "location_privacy",
            "location_sharing_enabled",
            "location_update_frequency",
            "max_distance",
        ]


class LocationPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationPermission
        fields = [
            "location_enabled",
            "background_location_enabled",
            "precise_location_enabled",
            "location_services_consent",
            "location_data_sharing",
        ]


class LocationHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationHistory
        fields = [
            "latitude",
            "longitude",
            "accuracy",
            "address",
            "city",
            "state",
            "country",
            "timestamp",
            "source",
        ]
        read_only_fields = ["timestamp"]


class UserMatchSerializer(serializers.ModelSerializer):
    user1_name = serializers.SerializerMethodField()
    user1_age = serializers.SerializerMethodField()
    user1_city = serializers.SerializerMethodField()

    user2_name = serializers.SerializerMethodField()
    user2_age = serializers.SerializerMethodField()
    user2_city = serializers.SerializerMethodField()

    class Meta:
        model = UserMatch
        fields = [
            "id",
            "user1",
            "user2",
            "user1_name",
            "user1_age",
            "user1_city",
            "user2_name",
            "user2_age",
            "user2_city",
            "distance",
            "match_score",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_user1_name(self, obj) -> str:
        return getattr(obj.user1, "name", None)

    def get_user1_age(self, obj) -> int:
        return getattr(obj.user1, "age", None)

    def get_user1_city(self, obj) -> str:
        return getattr(obj.user1, "city", None)

    def get_user2_name(self, obj) -> str:
        return getattr(obj.user2, "name", None)

    def get_user2_age(self, obj) -> int:
        return getattr(obj.user2, "age", None)

    def get_user2_city(self, obj) -> str:
        return getattr(obj.user2, "city", None)


class UserProfileWithLocationSerializer(serializers.ModelSerializer):
    social_accounts = SocialAccountSerializer(many=True, read_only=True)
    location_permissions = LocationPermissionSerializer(read_only=True)
    has_location = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "gender",
            "age",
            "location",
            "latitude",
            "longitude",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "location_privacy",
            "location_sharing_enabled",
            "location_update_frequency",
            "max_distance",
            "age_range_min",
            "age_range_max",
            "preferred_gender",
            "bio",
            "is_matchmaker",
            "social_accounts",
            "location_permissions",
            "has_location",
            "last_location_update",
        ]
        read_only_fields = ["id", "email", "has_location", "last_location_update"]


class PrivacyDistributionSerializer(serializers.Serializer):
    public = serializers.IntegerField()
    friends = serializers.IntegerField()
    private = serializers.IntegerField()
    hidden = serializers.IntegerField()


class LocationStatisticsSerializer(serializers.Serializer):
    total_users_with_location = serializers.IntegerField()
    location_updates_24h = serializers.IntegerField()
    location_updates_7d = serializers.IntegerField()
    active_users_with_location = serializers.IntegerField()
    privacy_distribution = PrivacyDistributionSerializer()


class NearbyUserSerializer(serializers.ModelSerializer):
    distance = serializers.FloatField()
    coordinates = serializers.ListField(child=serializers.FloatField())

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "age",
            "gender",
            "city",
            "bio",
            "distance",
            "coordinates",
        ]


class MatchPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["max_distance", "age_range_min", "age_range_max", "preferred_gender"]

    def validate(self, attrs):
        age_min = attrs.get("age_range_min")
        age_max = attrs.get("age_range_max")

        if age_min and age_max and age_min > age_max:
            raise serializers.ValidationError(
                "Minimum age cannot be greater than maximum age."
            )

        return attrs


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


# Email and Phone Verification Serializers
# class RequestEmailOTPSerializer(serializers.Serializer):
#     email = serializers.EmailField()

#     def validate_email(self, value):
#         if User.objects.filter(email=value).exists():
#             raise serializers.ValidationError("User already exists.")
#         if not EmailVerification.can_resend_for_email(value):
#             raise serializers.ValidationError(
#                 "Too many OTP requests. Please try again in a minute."
#             )
#         return value

#     def create(self, validated_data):
#         email = validated_data["email"]

#         # Create OTP record
#         verification = EmailVerification.create_verification(user=None, email=email)

#         # Send OTP email
#         send_mail(
#             subject="Your Verification OTP",
#             message=f"Your OTP is {verification.otp_code}",
#             from_email=settings.DEFAULT_FROM_EMAIL,
#             recipient_list=[email],
#         )

#         return {"message": "OTP sent successfully"}


class RegisterRequestOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(
        validators=[
            UniqueValidator(
                queryset=User.objects.all(), message="Email already registered."
            )
        ]
    )

    def validate(self, attrs):
        email = attrs["email"]

        # OTP rate limit check
        if EmailVerification.objects.filter(email=email, is_used=False).exists():
            if not EmailVerification.can_resend_for_email(email):
                raise serializers.ValidationError("OTP already sent. Try again later.")
        return attrs

    def create(self, validated_data):
        email = validated_data["email"]

        verification = EmailVerification.create_verification(email=email)
        verification.save()

        send_mail(
            subject="Your Verification OTP",
            message=f"Your OTP is {verification.otp_code}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )

        return {"message": "OTP sent to your email"}


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        email = attrs["email"]
        otp_code = attrs["otp_code"]

        verification = EmailVerification.objects.filter(
            email=email, otp_code=otp_code, is_used=False
        ).first()

        if not verification:
            raise serializers.ValidationError("Invalid OTP.")

        if verification.is_expired():
            raise serializers.ValidationError("OTP expired.")

        attrs["verification"] = verification
        return attrs

    def create(self, validated_data):
        verification = validated_data["verification"]
        verification.is_verified = True
        verification.verified_at = timezone.now()
        verification.save()

        return {"registration_token": str(verification.registration_token)}


class ConfirmRegistrationSerializer(serializers.Serializer):
    registration_token = serializers.UUIDField()
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        token = attrs["registration_token"]
        password = attrs["password"]
        password_confirm = attrs["password_confirm"]

        if password != password_confirm:
            raise serializers.ValidationError("Passwords do not match.")

        verification = EmailVerification.objects.filter(
            registration_token=token, is_used=False, is_verified=True
        ).first()

        if not verification:
            raise serializers.ValidationError(
                "Invalid or unverified registration token."
            )

        attrs["verification"] = verification
        return attrs

    def create(self, validated_data):
        verification = validated_data["verification"]
        password = validated_data["password"]

        user = User.objects.create_user(
            username=verification.email,
            email=verification.email,
            password=password,
        )

        verification.user = user
        verification.is_used = True
        verification.save()

        refresh = RefreshToken.for_user(user)

        return {
            "user": user,
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
        }


class ResendEmailOTPSerializer(serializers.Serializer):
    registration_token = serializers.UUIDField()

    def validate_registration_token(self, value):
        # Check if token exists and is not used yet
        verification = EmailVerification.objects.filter(
            registration_token=value, is_used=False
        ).first()
        if not verification:
            raise serializers.ValidationError(
                "Invalid or already used registration token."
            )

        # Optional: prevent spamming (resend cooldown)
        if not EmailVerification.can_resend_for_email(verification.email):
            raise serializers.ValidationError(
                "Too many OTP requests. Please try again in a minute."
            )

        self.context["verification"] = verification
        return value

    def create(self, validated_data):
        verification = self.context["verification"]

        # Generate new OTP
        from random import randint

        verification.otp_code = f"{randint(1000, 9999)}"
        verification.expires_at = timezone.now() + timezone.timedelta(minutes=5)
        verification.save()

        # Send OTP email
        send_mail(
            subject="Your Verification OTP",
            message=f"Your new OTP is {verification.otp_code}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[verification.email],
        )

        return {
            "message": "OTP resent successfully",
            "registration_token": str(verification.registration_token),
        }


# class PhoneOTPRequestSerializer(serializers.Serializer):
#     phone_number = serializers.CharField(max_length=15)
#     country_code = serializers.CharField(max_length=5, default="+1")
#     user_id = serializers.IntegerField(required=False)

#     def validate_phone_number(self, value):
#         import re

#         # Remove all non-digit characters
#         cleaned = re.sub(r"\D", "", value)
#         if len(cleaned) < 10:
#             raise serializers.ValidationError("Phone number must be at least 10 digits")
#         return cleaned

#     def validate_country_code(self, value):
#         if not value.startswith("+"):
#             value = "+" + value
#         return value


# class PhoneOTPVerifySerializer(serializers.Serializer):
#     phone_number = serializers.CharField(max_length=15)
#     country_code = serializers.CharField(max_length=5, default="+1")
#     otp_code = serializers.CharField(max_length=4, min_length=4)

#     def validate_otp_code(self, value):
#         if not value.isdigit():
#             raise serializers.ValidationError("OTP code must contain only digits")
#         if len(value) != 4:
#             raise serializers.ValidationError("OTP code must be 4 digits")
#         return value


class UserRoleSelectionSerializer(serializers.ModelSerializer):
    is_matchmaker = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserRoleSelection
        fields = ["selected_role", "is_matchmaker"]


class UserRoleStatusSerializer(serializers.Serializer):
    selected_role = serializers.ChoiceField(choices=UserRoleSelection.ROLE_CHOICES)
    is_matchmaker = serializers.BooleanField()
    verification_status = serializers.ChoiceField(
        choices=DocumentVerification.STATUS_CHOICES, allow_null=True, required=False
    )


class EmailVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailVerification
        fields = ["id", "email", "is_verified", "created_at", "expires_at"]
        read_only_fields = ["id", "created_at", "expires_at"]


class PhoneVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhoneVerification
        fields = [
            "id",
            "phone_number",
            "country_code",
            "is_verified",
            "created_at",
            "expires_at",
        ]
        read_only_fields = ["id", "created_at", "expires_at"]


class ResendOTPSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["email", "phone"])
    identifier = serializers.CharField()  # email or phone number

    def validate_type(self, value):
        if value not in ["email", "phone"]:
            raise serializers.ValidationError("Type must be 'email' or 'phone'")
        return value


# =============================================================================
# ADVANCED USER PROFILE SERIALIZERS
# =============================================================================


class UserProfileDetailSerializer(serializers.ModelSerializer):
    """Detailed user profile serializer for viewing other users"""

    profile_views_count = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    compatibility_score = serializers.SerializerMethodField()
    profile_completion_percentage = serializers.IntegerField(
        source="get_profile_completion_percentage", read_only=True
    )
    selected_role = serializers.SerializerMethodField()
    age = serializers.ReadOnlyField()
    languages = serializers.ListField(child=serializers.CharField())
    hobbies = serializers.ListField(child=serializers.CharField())
    interests = serializers.ListField(child=serializers.CharField())
    traits = serializers.ListField(child=serializers.CharField())
    profile_gallery = serializers.ListField(child=serializers.URLField())
    # visibility_status = serializers.SerializerMethodField()
    # visibility_choice = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "age",
            "gender",
            "bio",
            "profile_picture",
            "profile_gallery",
            "education_level",
            "height",
            "zodiac_sign",
            "languages",
            "relationship_status",
            "smoking_preference",
            "drinking_preference",
            "pet_preference",
            "exercise_frequency",
            "no_of_kids",
            "have_kids",
            "personality_type",
            "love_language",
            "communication_style",
            "hobbies",
            "interests",
            "marriage_plans",
            "future_kids",
            "religion_importance",
            "religion",
            "dating_type",
            "open_to_long_distance",
            "city",
            "state",
            "country",
            "profile_views_count",
            "is_online",
            "distance",
            "compatibility_score",
            "profile_completion_percentage",
            "looking_for",
            "push_notifications_enabled",
            "email_notifications_enabled",
            "preferred_language",
            "profile_completion_percentage",
            "phone_number",
            "selected_role",
            "traits",
            "genotype",
            "location",
            "age",
            "date_of_birth",
            # "visibility_status",
            # "visibility_choice",
        ]
        read_only_fields = [
            "id",
            "profile_views_count",
            "is_online",
            "distance",
            "compatibility_score",
            "profile_completion_percentage",
            "location",
            "age",
            # "visibility_status",
            # "visibility_choice",
        ]

    @extend_schema_field(serializers.IntegerField())
    def get_profile_views_count(self, obj):
        return UserProfileView.objects.filter(viewed_user=obj).count()

    @extend_schema_field(serializers.BooleanField())
    def get_is_online(self, obj):
        if not obj.last_seen:
            return False

        return obj.last_seen >= now() - timedelta(minutes=3)

    @extend_schema_field(serializers.FloatField())
    def get_distance(self, obj):
        request = self.context.get("request")
        if request and request.user.has_location and obj.has_location:
            return request.user.get_distance_to(obj)
        return None

    # @extend_schema_field(serializers.CharField(allow_null=True))
    # def _get_visibility(self, obj):
    #     request = self.context.get("request")
    #     # A user viewing their own profile has no bondmaker context
    #     # if request.user == obj:
    #     #     return None

    #     return Visibility.objects.filter(
    #         owner=obj,
    #         bondmaker=request.user
    #     ).first()

    # def get_visibility_status(self, obj) -> str:
    #     visibility = self._get_visibility(obj)
    #     return visibility.status if visibility else None

    # def get_visibility_choice(self, obj) -> str:
    #     visibility = self._get_visibility(obj)
    #     return visibility.visibility if visibility else None

    @extend_schema_field(serializers.IntegerField())
    def get_compatibility_score(self, obj):
        request = self.context.get("request")
        if request and request.user != obj:
            from .location_utils import calculate_match_score

            return calculate_match_score(request.user, obj)
        return None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_selected_role(self, obj):
        role_selection = getattr(obj, "role_selection", None)
        return role_selection.selected_role if role_selection else None

    def validate_phone_number(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits.")

        if len(value) != 11:
            raise serializers.ValidationError("Phone number must be exactly 11 digits.")

        if not value.startswith("0"):
            raise serializers.ValidationError("Phone number must start with 0.")

        return value

    def validate_traits(self, value):
        if len(value) > 3:
            raise serializers.ValidationError("You can select only 3 traits.")
        return value

    def validate_interests(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Must be a list of interests.")
        if len(value) > 5:
            raise serializers.ValidationError("You can select up to 5 interests.")
        return value

    def validate_profile_gallery(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("Minimum of 3 pictures required")
        if len(value) > 7:
            raise serializers.ValidationError("Maximum of 7 pictures allowed")
        return value

    def validate_date_of_birth(self, value):
        today = date.today()
        age = (
            today.year
            - value.year
            - ((today.month, today.day) < (value.month, value.day))
        )

        if age < 18:
            raise serializers.ValidationError("You must be at least 18 years old.")

        return value


class StaticUserProfileSerializer(serializers.ModelSerializer):
    selected_role = serializers.SerializerMethodField()
    profile_completion_percentage = serializers.IntegerField(
        source="get_profile_completion_percentage",
        read_only=True,
    )
    age = serializers.ReadOnlyField()
    languages = serializers.ListField(child=serializers.CharField())
    hobbies = serializers.ListField(child=serializers.CharField())
    interests = serializers.ListField(child=serializers.CharField())
    traits = serializers.ListField(child=serializers.CharField())
    profile_gallery = serializers.ListField(child=serializers.URLField())

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "age",
            "gender",
            "bio",
            "profile_picture",
            "profile_gallery",
            "education_level",
            "height",
            "zodiac_sign",
            "languages",
            "relationship_status",
            "smoking_preference",
            "drinking_preference",
            "pet_preference",
            "exercise_frequency",
            "no_of_kids",
            "have_kids",
            "personality_type",
            "love_language",
            "communication_style",
            "hobbies",
            "interests",
            "marriage_plans",
            "future_kids",
            "religion_importance",
            "religion",
            "dating_type",
            "open_to_long_distance",
            "city",
            "state",
            "country",
            "looking_for",
            "preferred_language",
            "traits",
            "genotype",
            "location",
            "date_of_birth",
            "phone_number",
            "selected_role",
            "profile_completion_percentage",
        ]

    def get_selected_role(self, obj) -> str:
        role_selection = getattr(obj, "role_selection", None)
        return role_selection.selected_role if role_selection else None


# class UserSearchSerializer(serializers.ModelSerializer):
#     """Serializer for user search results"""

#     distance = serializers.SerializerMethodField()
#     match_score = serializers.SerializerMethodField()

#     class Meta:
#         model = User
#         fields = [
#             "id",
#             "name",
#             "age",
#             "gender",
#             "bio",
#             "profile_picture",
#             "city",
#             "state",
#             "country",
#             "education_level",
#             "height",
#             "zodiac_sign",
#             "relationship_status",
#             "dating_type",
#             "distance",
#             "match_score",
#         ]

#     def get_distance(self, obj) -> float | None:
#         request = self.context.get("request")
#         if request and request.user.has_location and obj.has_location:
#             return request.user.get_distance_to(obj)
#         return None

#     def get_match_score(self, obj) -> float | None:
#         request = self.context.get("request")
#         if request and request.user != obj:
#             from .location_utils import calculate_match_score

#             return calculate_match_score(request.user, obj)
#         return None


class UserInterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserInterest
        fields = ["id", "name", "category", "icon"]


class UserInteractionSerializer(serializers.ModelSerializer):
    target_user_name = serializers.CharField(source="target_user.name", read_only=True)
    target_user_photo = serializers.URLField(
        source="target_user.profile_picture", read_only=True
    )
    bondmaker_name = serializers.SerializerMethodField()  # compute dynamically

    class Meta:
        model = UserInteraction
        fields = [
            "id",
            "target_user",
            "target_user_name",
            "target_user_photo",
            "bondmaker_name",
            "interaction_type",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "target_user_name",
            "target_user_photo",
            "bondmaker_name",
        ]

    def get_bondmaker_name(self, obj) -> str:
        # Get the active visibility for this target user
        visibility = (
            Visibility.objects.filter(
                owner=obj.target_user, status="approved", expires_at__gt=timezone.now()
            )
            .select_related("bondmaker")
            .first()
        )
        if visibility and visibility.bondmaker:
            return visibility.bondmaker.name
        return None


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "message", "is_read", "created_at"]
        read_only_fields = ["id", "title", "message", "created_at"]


class SearchQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchQuery
        fields = ["id", "query", "filters", "results_count", "created_at"]
        read_only_fields = ["id", "created_at"]


# class RecommendationSerializer(serializers.ModelSerializer):
#     recommended_user = UserSearchSerializer(read_only=True)

#     class Meta:
#         model = RecommendationEngine
#         fields = ["id", "recommended_user", "score", "algorithm", "created_at"]
#         read_only_fields = ["id", "created_at"]


# =============================================================================
# SEARCH AND FILTER SERIALIZERS
# =============================================================================


class UserSearchFilterSerializer(serializers.Serializer):
    """Serializer for advanced user search filters"""

    query = serializers.CharField(required=False, allow_blank=True)
    gender = serializers.CharField(required=False)
    age_min = serializers.IntegerField(required=False, min_value=18, max_value=100)
    age_max = serializers.IntegerField(required=False, min_value=18, max_value=100)
    max_distance = serializers.IntegerField(required=False, min_value=1, max_value=500)
    education_level = serializers.CharField(required=False)
    relationship_status = serializers.CharField(required=False)
    smoking_preference = serializers.CharField(required=False)
    drinking_preference = serializers.CharField(required=False)
    pet_preference = serializers.CharField(required=False)
    exercise_frequency = serializers.CharField(required=False)
    have_kids = serializers.CharField(required=False)
    personality_type = serializers.CharField(required=False)
    love_language = serializers.CharField(required=False)
    dating_type = serializers.CharField(required=False)
    religion = serializers.CharField(required=False)
    interests = serializers.ListField(child=serializers.CharField(), required=False)
    hobbies = serializers.ListField(child=serializers.CharField(), required=False)
    is_matchmaker = serializers.BooleanField(required=False)
    has_photos = serializers.BooleanField(required=False)
    online_only = serializers.BooleanField(required=False)

    def validate(self, attrs):
        age_min = attrs.get("age_min")
        age_max = attrs.get("age_max")

        if age_min and age_max and age_min > age_max:
            raise serializers.ValidationError("age_min cannot be greater than age_max")

        return attrs


class CategoryFilterSerializer(serializers.Serializer):
    """Serializer for category-based filtering"""

    category = serializers.ChoiceField(
        choices=[
            ("all", "All"),
            ("casual_dating", "Casual Dating"),
            ("lgbtq", "LGBTQ+"),
            ("sugar", "Sugar Relationship"),
            ("serious", "Serious Relationship"),
            ("friends", "Friends First"),
            ("matchmakers", "Matchmakers Only"),
        ]
    )
    subcategory = serializers.CharField(required=False, allow_blank=True)


# =============================================================================
# CHAT AND MESSAGING SERIALIZERS (NEW)
# =============================================================================


# class ChatParticipantSerializer(serializers.ModelSerializer):
#     """Serializer for chat participants (simplified user info)"""

#     user_id = serializers.IntegerField(source="user.id", read_only=True)
#     name = serializers.CharField(source="user.name", read_only=True)
#     profile_picture = serializers.URLField(
#         source="user.profile_picture", read_only=True
#     )
#     is_online = serializers.SerializerMethodField()
#     is_muted = serializers.SerializerMethodField()

#     class Meta:
#         model = ChatParticipant
#         fields = [
#             "user_id",
#             "name",
#             "profile_picture",
#             "is_online",
#             "joined_at",
#             "last_seen_at",
#             "is_active",
#             "custom_nickname",
#             "notifications_enabled",
#             "is_muted",
#         ]
#         read_only_fields = [
#             "user_id",
#             "name",
#             "profile_picture",
#             "is_online",
#             "joined_at",
#             "last_seen_at",
#         ]

#     def get_is_online(self, obj) -> bool:
#         """Check if user is online (placeholder - implement with real-time status)"""
#         return False

#     @extend_schema_field({"type": "boolean"})
#     def get_is_muted(self, obj) -> bool:
#         """Check if chat is muted for this participant"""
#         return obj.is_muted


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.name", read_only=True)

    class Meta:
        model = Message
        fields = [
            "id",
            "sender_name",
            "message_type",
            "content",
            "timestamp",
        ]


class ChatDetailSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    participants = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = [
            "id",
            "chat_type",
            "participants",
            "created_at",
            "last_message_at",
            "messages",
        ]

    def get_participants(self, obj) -> dict:
        return [
            {
                "id": user.id,
                "name": user.name,
                "profile_picture": user.profile_picture,
            }
            for user in obj.participants.all()
        ]


class ChatListSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = [
            "id",
            "chat_type",
            "other_user",
            "last_message_at",
            "unread_count",
        ]

    def get_other_user(self, obj) -> dict:
        request = self.context["request"]
        other = obj.get_other_participant(request.user)

        if not other:
            return None

        return {
            "id": other.id,
            "name": other.name,
            "profile_picture": other.profile_picture,
        }

    def get_unread_count(self, obj) -> int:
        request = self.context["request"]
        return obj.get_unread_count(request.user)

    # def get_is_from_current_user(self, obj) -> bool:
    #     """Check if message is from the current user"""
    #     request = self.context.get("request")
    #     if request and request.user.is_authenticated:
    #         return obj.sender == request.user
    #     return False

    # def get_reply_to_message(self, obj) -> str:
    #     """Get the message being replied to"""
    #     if obj.reply_to:
    #         return {
    #             "id": obj.reply_to.id,
    #             "content": (
    #                 obj.reply_to.content[:100] + "..."
    #                 if len(obj.reply_to.content or "") > 100
    #                 else obj.reply_to.content
    #             ),
    #             "sender_name": (
    #                 obj.reply_to.sender.name if obj.reply_to.sender else "System"
    #             ),
    #             "message_type": obj.reply_to.message_type,
    #             "timestamp": obj.reply_to.timestamp,
    #         }
    #     return None

    # def get_formatted_timestamp(self, obj) -> str:
    #     """Get formatted timestamp for display"""
    #     from django.utils import timezone

    #     now = timezone.now()
    #     diff = now - obj.timestamp

    #     if diff.days == 0:
    #         return obj.timestamp.strftime("%H:%M")
    #     elif diff.days == 1:
    #         return "Yesterday"
    #     elif diff.days < 7:
    #         return obj.timestamp.strftime("%A")
    #     else:
    #         return obj.timestamp.strftime("%m/%d/%Y")


# class VoiceNoteSerializer(serializers.ModelSerializer):
#     """Serializer for voice notes"""

#     message_id = serializers.IntegerField(source="message.id", read_only=True)

#     class Meta:
#         model = VoiceNote
#         fields = [
#             "id",
#             "message_id",
#             "audio_url",
#             "duration",
#             "file_size",
#             "transcription",
#             "transcription_confidence",
#             "created_at",
#         ]
#         read_only_fields = ["id", "message_id", "created_at"]


# class CallSerializer(serializers.ModelSerializer):
#     """Serializer for voice/video calls"""

#     caller_name = serializers.CharField(source="caller.name", read_only=True)
#     caller_profile_picture = serializers.URLField(
#         source="caller.profile_picture", read_only=True
#     )
#     callee_name = serializers.CharField(source="callee.name", read_only=True)
#     callee_profile_picture = serializers.URLField(
#         source="callee.profile_picture", read_only=True
#     )
#     duration_display = serializers.CharField(
#         source="get_duration_display", read_only=True
#     )

#     class Meta:
#         model = Call
#         fields = [
#             "id",
#             "chat",
#             "caller",
#             "caller_name",
#             "caller_profile_picture",
#             "callee",
#             "callee_name",
#             "callee_profile_picture",
#             "call_type",
#             "status",
#             "started_at",
#             "answered_at",
#             "ended_at",
#             "duration",
#             "duration_display",
#             "call_id",
#             "room_id",
#             "quality_score",
#             "is_recorded",
#             "recording_url",
#         ]
#         read_only_fields = [
#             "id",
#             "chat",
#             "caller",
#             "caller_name",
#             "caller_profile_picture",
#             "callee",
#             "callee_name",
#             "callee_profile_picture",
#             "started_at",
#             "answered_at",
#             "ended_at",
#             "duration",
#             "duration_display",
#             "quality_score",
#         ]


# class CallInitiateSerializer(serializers.Serializer):
#     """Serializer for initiating calls"""

#     callee_id = serializers.IntegerField()
#     call_type = serializers.ChoiceField(
#         choices=[("voice", "Voice Call"), ("video", "Video Call")]
#     )

#     def validate_callee_id(self, value):
#         """Validate callee exists"""
#         if not User.objects.filter(id=value, is_active=True).exists():
#             raise serializers.ValidationError("User not found or inactive")
#         return value


# class ChatReportSerializer(serializers.ModelSerializer):
#     """Serializer for chat reports"""

#     reporter_name = serializers.CharField(source="reporter.name", read_only=True)
#     reported_user_name = serializers.CharField(
#         source="reported_user.name", read_only=True
#     )

#     class Meta:
#         model = ChatReport
#         fields = [
#             "id",
#             "reporter",
#             "reporter_name",
#             "reported_user",
#             "reported_user_name",
#             "chat",
#             "message",
#             "report_type",
#             "description",
#             "status",
#             "moderator_notes",
#             "action_taken",
#             "resolved_by",
#             "resolved_at",
#             "created_at",
#         ]
#         read_only_fields = [
#             "id",
#             "reporter",
#             "reporter_name",
#             "reported_user_name",
#             "status",
#             "moderator_notes",
#             "action_taken",
#             "resolved_by",
#             "resolved_at",
#             "created_at",
#         ]

#     def create(self, validated_data):
#         """Create report with current user as reporter"""
#         request = self.context.get("request")
#         if request and request.user.is_authenticated:
#             validated_data["reporter"] = request.user
#         return super().create(validated_data)

# class ChatSettingsSerializer(serializers.ModelSerializer):
#     """Serializer for chat settings"""

#     class Meta:
#         model = Chat
#         fields = ["chat_name", "chat_theme"]

#     def update(self, instance, validated_data):
#         """Update chat settings"""
#         for attr, value in validated_data.items():
#             setattr(instance, attr, value)
#         instance.save()
#         return instance

# # =============================================================================
# # SOCIAL FEED AND STORY SERIALIZERS (NEW)
# # =============================================================================

class PostCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)
    is_liked = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PostComment
        fields = [
            "id",
            "author",
            "author_name",
            "content",
            "parent_comment",
            "likes_count",
            "is_liked",
            "created_at",
        ]

    def get_is_liked(self, obj):
        user = self.context.get("request").user
        if not user.is_authenticated:
            return False
        return obj.interactions.filter(user=user).exists()


class PostCommentNestedSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)
    replies_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PostComment
        fields = [
            "id",
            "author",
            "author_name",
            "content",
            "parent_comment",
            "replies_count",
            "created_at",
        ]


class PostDetailSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)
    comments = PostCommentNestedSerializer(many=True, read_only=True)
    has_liked = serializers.SerializerMethodField()
    has_bonded = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = "__all__"

    def get_has_liked(self, obj):
        user = self.context["request"].user
        return obj.interactions.filter(user=user, interaction_type="like").exists()

    def get_has_bonded(self, obj):
        user = self.context["request"].user
        return obj.interactions.filter(user=user, interaction_type="bond").exists()


class PostCommentCreateSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)
    likes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PostComment
        fields = [
            "id",
            "author",
            "author_name",
            "content",
            "likes_count",
            "created_at",
        ]
        read_only_fields = ["author", "likes_count", "created_at"]


class PostSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)
    image_urls = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    hashtags = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    mentions = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    has_liked = serializers.SerializerMethodField()
    has_bonded = serializers.SerializerMethodField()
    is_featured = serializers.BooleanField(default=False)
    is_reported = serializers.BooleanField(default=False)

    class Meta:
        model = Post
        fields = [
            "id",
            "author",
            "author_name",
            "post_type",
            "content",
            "image_urls",
            "video_url",
            "video_thumbnail",
            "visibility",
            "location",
            "hashtags",
            "mentions",
            "likes_count",
            "comments_count",
            "shares_count",
            "bonds_count",
            "has_liked",
            "has_bonded",
            "created_at",
            "updated_at",
            "is_reported",
            "is_featured",
        ]
        read_only_fields = [
            "likes_count",
            "comments_count",
            "shares_count",
            "bonds_count",
            "author",
        ]

    def get_has_liked(self, obj):
        user = self.context["request"].user
        return obj.interactions.filter(user=user, interaction_type="like").exists()

    def get_has_bonded(self, obj):
        user = self.context["request"].user
        return obj.interactions.filter(user=user, interaction_type="bond").exists()


# class PostCreateSerializer(serializers.ModelSerializer):
#     """Serializer for creating new posts"""

#     class Meta:
#         model = Post
#         fields = [
#             "post_type",
#             "content",
#             "image_urls",
#             "video_url",
#             "video_thumbnail",
#             "visibility",
#             "location",
#             "hashtags",
#             "mentions",
#         ]

#     def validate_content(self, value):
#         """Validate and sanitize post content"""
#         if not value or len(value.strip()) == 0:
#             raise serializers.ValidationError("Post content cannot be empty")
#         if len(value) > 2000:
#             raise serializers.ValidationError(
#                 "Post content cannot exceed 2000 characters"
#             )
#         # Sanitize for XSS prevention
#         return self._sanitize_text_input(value)

#     def validate_location(self, value):
#         """Sanitize location text"""
#         if value:
#             return self._sanitize_text_input(value)
#         return value

#     def validate_image_urls(self, value):
#         """Validate image URLs"""
#         if value and len(value) > 10:
#             raise serializers.ValidationError("Cannot attach more than 10 images")
#         return value

#     def create(self, validated_data):
#         """Create post with current user as author"""
#         request = self.context.get("request")
#         if request and request.user.is_authenticated:
#             validated_data["author"] = request.user
#         return super().create(validated_data)


class StorySerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)
    has_liked = serializers.BooleanField(read_only=True)
    has_viewed = serializers.BooleanField(read_only=True)
    reactions_count = serializers.IntegerField(read_only=True)
    views_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Story
        fields = [
            "id",
            "author",
            "author_name",
            "story_type",
            "content",
            "image_url",
            "video_url",
            "video_duration",
            "background_color",
            "text_color",
            "font_size",
            "views_count",
            "reactions_count",
            "has_viewed",
            "has_liked",
            "created_at",
            "expires_at",
        ]


class StoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Story
        fields = [
            "story_type",
            "content",
            "image_url",
            "video_url",
            "video_duration",
            "background_color",
            "text_color",
            "font_size",
        ]

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["author"] = user
        validated_data["expires_at"] = timezone.now() + timedelta(hours=24)
        return super().create(validated_data)


class StoryListSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)
    author_avatar = serializers.CharField(
        source="author.profile_picture", read_only=True
    )

    views_count = serializers.IntegerField(read_only=True)
    reactions_count = serializers.IntegerField(read_only=True)
    has_viewed = serializers.BooleanField(read_only=True)
    is_liked = serializers.BooleanField(read_only=True)

    class Meta:
        model = Story
        fields = [
            "id",
            "author",
            "author_name",
            "author_avatar",
            "story_type",
            "views_count",
            "reactions_count",
            "has_viewed",
            "is_liked",
            "created_at",
        ]


class StoryDetailSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)
    author_avatar = serializers.CharField(
        source="author.profile_picture", read_only=True
    )
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = "__all__"

    def get_is_liked(self, obj):
        user = self.context["request"].user
        return StoryInteraction.objects.filter(
            story=obj, user=user, interaction_type="like"
        ).exists()


class StoryViewerSerializer(serializers.ModelSerializer):
    viewer_name = serializers.CharField(source="viewer.name", read_only=True)
    viewer_avatar = serializers.CharField(
        source="viewer.profile_picture", read_only=True
    )

    class Meta:
        model = StoryView
        fields = ["viewer", "viewer_name", "viewer_avatar", "viewed_at"]


class PostInteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostInteraction
        fields = ["interaction_type"]

    def validate_interaction_type(self, value):
        allowed = ["like", "share", "bond", "save"]
        if value not in allowed:
            raise serializers.ValidationError("Invalid interaction type")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        post = self.context["post"]
        interaction_type = validated_data["interaction_type"]

        interaction, created = PostInteraction.objects.get_or_create(
            user=user,
            post=post,
            interaction_type=interaction_type,
        )

        # LIKE (Toggle)
        if interaction_type == "like":
            if created:
                Post.objects.filter(id=post.id).update(likes_count=F("likes_count") + 1)
            else:
                interaction.delete()
                Post.objects.filter(id=post.id).update(likes_count=F("likes_count") - 1)

        # BOND (Toggle)
        elif interaction_type == "bond":
            if created:
                Post.objects.filter(id=post.id).update(bonds_count=F("bonds_count") + 1)
            else:
                interaction.delete()
                Post.objects.filter(id=post.id).update(bonds_count=F("bonds_count") - 1)

        # SHARE (Not Toggle)
        elif interaction_type == "share":
            if created:
                Post.objects.filter(id=post.id).update(
                    shares_count=F("shares_count") + 1
                )
            # if not created → do nothing (already shared)

        # SAVE (Toggle without counter)
        elif interaction_type == "save":
            if not created:
                interaction.delete()

        return interaction


class StoryInteractionSerializer(serializers.Serializer):

    story_id = serializers.IntegerField()
    interaction_type = serializers.ChoiceField(
        choices=StoryInteraction.INTERACTION_TYPES
    )

    def create(self, validated_data):
        user = self.context["request"].user
        story = Story.objects.get(id=validated_data["story_id"])

        obj, created = StoryInteraction.objects.get_or_create(
            user=user, story=story, interaction_type=validated_data["interaction_type"]
        )

        if not created:
            obj.delete()
            return {"status": "removed"}

        return {"status": "added"}


# class PostReportSerializer(serializers.ModelSerializer):
#     """Serializer for post/comment reports"""

#     reporter_name = serializers.CharField(source="reporter.name", read_only=True)
#     reported_user_name = serializers.CharField(
#         source="reported_user.name", read_only=True
#     )

#     class Meta:
#         model = PostReport
#         fields = [
#             "id",
#             "reporter",
#             "reporter_name",
#             "reported_user",
#             "reported_user_name",
#             "post",
#             "comment",
#             "report_type",
#             "description",
#             "status",
#             "moderator_notes",
#             "action_taken",
#             "resolved_by",
#             "resolved_at",
#             "created_at",
#         ]
#         read_only_fields = [
#             "id",
#             "reporter",
#             "reporter_name",
#             "reported_user_name",
#             "status",
#             "moderator_notes",
#             "action_taken",
#             "resolved_by",
#             "resolved_at",
#             "created_at",
#         ]

#     def create(self, validated_data):
#         """Create report with current user as reporter"""
#         request = self.context.get("request")
#         if request and request.user.is_authenticated:
#             validated_data["reporter"] = request.user
#         return super().create(validated_data)


# class PostShareSerializer(serializers.ModelSerializer):
#     """Serializer for post shares"""

#     class Meta:
#         model = PostShare
#         fields = ["platform"]

#     def create(self, validated_data):
#         """Create share with current user"""
#         request = self.context.get("request")
#         if request and request.user.is_authenticated:
#             validated_data["user"] = request.user
#         return super().create(validated_data)


# class FeedSearchSerializer(serializers.ModelSerializer):
#     """Serializer for feed search queries"""

#     class Meta:
#         model = FeedSearch
#         fields = ["query", "filters_applied"]

#     def create(self, validated_data):
#         """Create search with current user"""
#         request = self.context.get("request")
#         if request and request.user.is_authenticated:
#             validated_data["user"] = request.user
#         return super().create(validated_data)


# class FeedSuggestionSerializer(serializers.Serializer):
#     query = serializers.CharField()
#     count = serializers.IntegerField(required=False)


# class FeedSuggestionsResponseSerializer(serializers.Serializer):
#     message = serializers.CharField()
#     status = serializers.CharField()
#     suggestions = serializers.ListField(
#         child=serializers.CharField(), required=False
#     )
#     hashtags = serializers.ListField(
#         child=serializers.CharField(), required=False
#     )
#     popular_searches = serializers.ListField(
#         child=serializers.CharField(), required=False
#    )


# =============================================================================
# SUBSCRIPTION PLANS SERIALIZERS (NEW FROM FIGMA)
# =============================================================================


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for subscription plans"""

    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",
            "display_name",
            "description",
            "duration",
            "price_bondcoins",
            "price_usd",
            "unlimited_swipes",
            "undo_swipes",
            "unlimited_unwind",
            "global_access",
            "read_receipt",
            "live_hours_days",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for user subscriptions"""

    plan_name = serializers.CharField(source="plan.display_name", read_only=True)
    plan_details = SubscriptionPlanSerializer(source="plan", read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserSubscription
        fields = [
            "id",
            "plan",
            "plan_name",
            "plan_details",
            "status",
            "start_date",
            "end_date",
            "payment_method",
            "transaction_id",
            "auto_renew",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "start_date", "created_at", "updated_at"]


class UserSubscriptionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating user subscriptions"""

    class Meta:
        model = UserSubscription
        fields = ["plan", "payment_method", "auto_renew"]

    def create(self, validated_data):
        """Create subscription with current user and set end date"""
        from django.utils import timezone
        from datetime import timedelta

        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["user"] = request.user

        plan = validated_data["plan"]

        # Calculate end date based on plan duration
        duration_map = {
            "1_week": timedelta(weeks=1),
            "1_month": timedelta(days=30),
            "3_months": timedelta(days=90),
            "6_months": timedelta(days=180),
            "1_year": timedelta(days=365),
        }

        duration = duration_map.get(plan.duration, timedelta(days=30))
        validated_data["end_date"] = timezone.now() + duration

        return super().create(validated_data)


# =============================================================================
# BONDCOIN WALLET SERIALIZERS (NEW FROM FIGMA)
# =============================================================================


class BondcoinPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BondcoinPackage
        fields = [
            "id",
            "name",
            "bondcoin_amount",
            "price_usd",
            "is_popular",
            "is_active",
        ]


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ["available_balance", "locked_balance", "updated_at"]


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = [
            "id",
            "tx_type",
            "amount",
            "payment_method",
            "status",
            "reference_id",
            "created_at",
        ]


# =============================================================================
# VIRTUAL GIFTING SERIALIZERS (NEW FROM FIGMA)
# =============================================================================


class SendGiftSerializer(serializers.Serializer):
    receiver_id = serializers.IntegerField()
    gift_id = serializers.IntegerField()


class ConvertGiftSerializer(serializers.Serializer):
    gift_id = serializers.IntegerField()


class PurchaseSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    platform = serializers.ChoiceField(choices=["apple", "google"])
    receipt_data = serializers.CharField(required=False, allow_blank=True)
    purchase_token = serializers.CharField(required=False, allow_blank=True)


class GiftCategorySerializer(serializers.ModelSerializer):
    """Serializer for gift categories"""

    class Meta:
        model = GiftCategory
        fields = [
            "id",
            "name",
            "display_name",
            "description",
            "icon_url",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class VirtualGiftSerializer(serializers.ModelSerializer):
    """Serializer for virtual gifts"""

    category_name = serializers.CharField(
        source="category.display_name", read_only=True
    )

    class Meta:
        model = VirtualGift
        fields = [
            "id",
            "name",
            "category",
            "category_name",
            "description",
            "icon_url",
            "cost_bondcoins",
            "is_popular",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GiftTransactionSerializer(serializers.ModelSerializer):
    """Serializer for gift transactions"""

    sender_name = serializers.CharField(source="sender.name", read_only=True)
    recipient_name = serializers.CharField(source="recipient.name", read_only=True)
    gift_name = serializers.CharField(source="gift.name", read_only=True)
    gift_icon = serializers.URLField(source="gift.icon_url", read_only=True)

    class Meta:
        model = GiftTransaction
        fields = [
            "id",
            "sender",
            "sender_name",
            "recipient",
            "recipient_name",
            "gift",
            "gift_name",
            "gift_icon",
            "quantity",
            "total_cost",
            "context_type",
            "context_id",
            "status",
            "message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "sender",
            "sender_name",
            "recipient_name",
            "gift_name",
            "gift_icon",
            "total_cost",
            "created_at",
            "updated_at",
        ]


class GiftTransactionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating gift transactions"""

    class Meta:
        model = GiftTransaction
        fields = [
            "recipient",
            "gift",
            "quantity",
            "context_type",
            "context_id",
            "message",
        ]

    def create(self, validated_data):
        """Create gift transaction with current user as sender"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["sender"] = request.user

        # Calculate total cost
        gift = validated_data["gift"]
        quantity = validated_data.get("quantity", 1)
        validated_data["total_cost"] = gift.cost_bondcoins * quantity

        # Create Bondcoin transaction for the gift
        bondcoin_transaction = WalletTransaction.objects.create(
            user=validated_data["sender"],
            transaction_type="gift_sent",
            amount=-validated_data["total_cost"],
            gift=gift,
            description=f"Gift sent: {gift.name}",
            status="completed",
        )
        validated_data["bondcoin_transaction"] = bondcoin_transaction

        return super().create(validated_data)


# =============================================================================
# LIVE STREAMING ENHANCEMENT SERIALIZERS (NEW FROM FIGMA)
# =============================================================================


class LiveGiftSerializer(serializers.ModelSerializer):
    """Serializer for live session gifts"""

    sender_name = serializers.CharField(source="sender.name", read_only=True)
    gift_name = serializers.CharField(source="gift.name", read_only=True)
    gift_icon = serializers.URLField(source="gift.icon_url", read_only=True)

    class Meta:
        model = LiveGift
        fields = [
            "id",
            "session",
            "sender",
            "sender_name",
            "gift",
            "gift_name",
            "gift_icon",
            "quantity",
            "total_cost",
            "chat_message",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "sender",
            "sender_name",
            "gift_name",
            "gift_icon",
            "created_at",
        ]


class LiveGiftCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating live session gifts"""

    class Meta:
        model = LiveGift
        fields = ["session", "gift", "quantity"]

    def create(self, validated_data):
        """Create live gift with current user as sender"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["sender"] = request.user

        # Calculate total cost
        gift = validated_data["gift"]
        quantity = validated_data.get("quantity", 1)
        validated_data["total_cost"] = gift.cost_bondcoins * quantity

        # Create chat message
        validated_data["chat_message"] = f"{request.user.name} sent {gift.name}"

        # Create Bondcoin transaction
        bondcoin_transaction = WalletTransaction.objects.create(
            user=validated_data["sender"],
            tx_type="gift_sent",
            amount=-validated_data["total_cost"],
            gift=gift,
            status="completed",
        )
        validated_data["bondcoin_transaction"] = bondcoin_transaction

        return super().create(validated_data)


class LiveJoinRequestSerializer(serializers.ModelSerializer):
    """Serializer for live session join requests"""

    requester_name = serializers.CharField(source="requester.name", read_only=True)
    requester_profile_picture = serializers.URLField(
        source="requester.profile_picture", read_only=True
    )
    session_title = serializers.CharField(source="session.title", read_only=True)
    host_name = serializers.CharField(source="session.user.name", read_only=True)

    class Meta:
        model = LiveJoinRequest
        fields = [
            "id",
            "session",
            "session_title",
            "host_name",
            "requester",
            "requester_name",
            "requester_profile_picture",
            "requested_role",
            "status",
            "message",
            "responded_by",
            "response_message",
            "responded_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "requester",
            "requester_name",
            "requester_profile_picture",
            "session_title",
            "host_name",
            "responded_by",
            "responded_at",
            "created_at",
            "updated_at",
        ]


class LiveJoinRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating live session join requests"""

    class Meta:
        model = LiveJoinRequest
        fields = ["session", "requested_role", "message"]

    def create(self, validated_data):
        """Create join request with current user as requester"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["requester"] = request.user
        return super().create(validated_data)


class LiveJoinRequestManageSerializer(serializers.ModelSerializer):
    """Serializer for managing live session join requests (host response)"""

    class Meta:
        model = LiveJoinRequest
        fields = ["status", "response_message"]

    def update(self, instance, validated_data):
        """Update join request with response from host"""
        from django.utils import timezone

        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["responded_by"] = request.user
            validated_data["responded_at"] = timezone.now()

        return super().update(instance, validated_data)


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for payment methods"""

    class Meta:
        model = PaymentMethod
        fields = [
            "id",
            "name",
            "display_name",
            "description",
            "icon_url",
            "is_active",
            "processing_fee_percentage",
            "min_amount",
            "max_amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PaymentTransactionSerializer(serializers.ModelSerializer):
    """Serializer for payment transactions"""

    payment_method_display = serializers.CharField(
        source="payment_method.display_name", read_only=True
    )
    user_name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = PaymentTransaction
        fields = [
            "id",
            "user",
            "user_name",
            "transaction_type",
            "payment_method",
            "payment_method_display",
            "amount_usd",
            "processing_fee",
            "total_amount",
            "currency",
            "status",
            "provider",
            "provider_transaction_id",
            "subscription",
            "bondcoin_transaction",
            "description",
            "metadata",
            "created_at",
            "updated_at",
            "processed_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "user_name",
            "payment_method_display",
            "provider_transaction_id",
            "created_at",
            "updated_at",
            "processed_at",
        ]


class PaymentTransactionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating payment transactions"""

    class Meta:
        model = PaymentTransaction
        fields = [
            "transaction_type",
            "payment_method",
            "amount_usd",
            "currency",
            "subscription",
            "bondcoin_transaction",
            "description",
            "metadata",
        ]

    def validate(self, attrs):
        """Validate payment transaction"""
        payment_method = attrs.get("payment_method")
        amount_usd = attrs.get("amount_usd")

        if payment_method and amount_usd:
            # Check amount limits
            if amount_usd < payment_method.min_amount:
                raise serializers.ValidationError(
                    f"Amount must be at least ${payment_method.min_amount}"
                )

            if amount_usd > payment_method.max_amount:
                raise serializers.ValidationError(
                    f"Amount cannot exceed ${payment_method.max_amount}"
                )

            # Calculate processing fee and total
            processing_fee = amount_usd * (
                payment_method.processing_fee_percentage / 100
            )
            attrs["processing_fee"] = processing_fee
            attrs["total_amount"] = amount_usd + processing_fee

        return attrs


class PaymentWebhookSerializer(serializers.ModelSerializer):
    """Serializer for payment webhooks"""

    transaction_details = PaymentTransactionSerializer(
        source="transaction", read_only=True
    )

    class Meta:
        model = PaymentWebhook
        fields = [
            "id",
            "provider",
            "event_type",
            "event_id",
            "transaction",
            "transaction_details",
            "payload",
            "processed",
            "processing_error",
            "created_at",
            "processed_at",
        ]
        read_only_fields = ["id", "created_at", "processed_at"]


class PaymentWebhookCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating payment webhooks"""

    class Meta:
        model = PaymentWebhook
        fields = ["provider", "event_type", "event_id", "transaction", "payload"]


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


class PushNotificationSerializer(serializers.Serializer):
    token = serializers.CharField()
    title = serializers.CharField(default="Notification")
    body = serializers.CharField(default="Message")


class BondmakerListSerializer(serializers.ModelSerializer):
    verification_status = serializers.CharField(
        source="documentverification.status", read_only=True
    )

    class Meta:
        model = User
        fields = (
            "id",
            "name",
            "email",
            "phone_number",
            "location",
            "verification_status",
        )


class PublicBondmakerProfileSerializer(serializers.ModelSerializer):
    verification_status = serializers.SerializerMethodField()
    age = serializers.ReadOnlyField()
    accepted_match_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "profile_picture",
            "location",
            "gender",
            "age",
            "availability_status",
            "verification_status",
            "age",
            "accepted_match_count",
        ]

        read_only_fields = [
            "age",
        ]

    def get_verification_status(self, obj) -> str:
        verification = obj.document_verifications.first()
        if not verification:
            return "not_submitted"
        return verification.status


class UserSecurityQuestionDisplaySerializer(serializers.ModelSerializer):
    """Handles both display and update of user security questions"""

    question = serializers.SerializerMethodField(read_only=True)
    answer = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = UserSecurityQuestion
        fields = [
            "question_type",
            "question",
            "answer",
            "response_text",
            "response_choice",
            "is_public",
        ]

    def get_question(self, obj) -> str:
        return obj.get_question_type_display()

    def to_representation(self, instance) -> str | None:
        """Return answer in 'answer' key for display"""
        ret = super().to_representation(instance)
        # Decide which field has the actual answer
        if instance.response_text:
            ret["answer"] = instance.response_text
        elif instance.response_choice:
            ret["answer"] = instance.response_choice
        else:
            ret["answer"] = None
        return ret


class UserSecurityQuestionUpdateSerializer(serializers.Serializer):
    question_type = serializers.ChoiceField(choices=UserSecurityQuestion.QUESTION_TYPES)
    answer = serializers.CharField()


class BondmakerProfileUpdateSerializer(serializers.ModelSerializer):
    security_questions = UserSecurityQuestionDisplaySerializer(
        many=True, read_only=True
    )
    security_questions_update = UserSecurityQuestionUpdateSerializer(
        many=True, write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "username",
            "name",
            "gender",
            "date_of_birth",
            "relationship_status",
            "education_level",
            "profile_picture",
            "security_questions",
            "security_questions_update",
        ]

    def validate_username(self, value):
        user = self.context["request"].user

        # Only allow setting username if empty
        if user.username:
            return user.username

        clean_username = value.strip().lstrip("@")

        try:
            validate_username_format(clean_username)
        except Exception as e:
            raise serializers.ValidationError(str(e))

        is_valid, message, suggestions = UsernameValidation.validate_username(
            clean_username
        )

        if not is_valid:
            raise serializers.ValidationError(
                {"message": message, "suggestions": suggestions}
            )

        return clean_username

    @transaction.atomic
    def update(self, instance, validated_data):
        questions = validated_data.pop("security_questions", [])

        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Save security questions
        for q in questions:
            question_type = q["question_type"]
            answer = q["answer"]

            obj, _ = UserSecurityQuestion.objects.update_or_create(
                user=instance,
                question_type=question_type,
                defaults={
                    "response_text": (
                        answer
                        if QUESTION_UI_CONFIG[question_type]["input_type"] == "text"
                        else None
                    ),
                    "response_choice": (
                        answer
                        if QUESTION_UI_CONFIG[question_type]["input_type"] == "choice"
                        else None
                    ),
                },
            )

        return instance


class SubscribeSerializer(serializers.ModelSerializer):

    class Meta:
        model = BondmakerSubscription
        fields = ["id", "user", "bondmaker"]
        read_only_fields = ["user"]

    def create(self, validated_data):
        validated_data["follower"] = self.context["request"].user
        return super().create(validated_data)


class BondmakerSubscriptionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)
    bondmaker_name = serializers.CharField(source="bondmaker.name", read_only=True)

    class Meta:
        model = BondmakerSubscription
        fields = [
            "id",
            "user",
            "user_name",
            "bondmaker",
            "bondmaker_name",
            "start_date",
            "end_date",
            "active",
        ]


class SubscribeBondmakerSerializer(serializers.Serializer):
    bondmaker_id = serializers.IntegerField()


class BondmakerSuggestionSerializer(serializers.Serializer):
    visible_user_id = serializers.IntegerField()
    suggested_user_id = serializers.IntegerField()

    def validate(self, attrs):
        request = self.context["request"]
        bondmaker = request.user

        if not bondmaker.is_matchmaker:
            raise serializers.ValidationError("Only bondmakers can suggest users.")

        # Fetch users
        try:
            visible_user = User.objects.get(id=attrs["visible_user_id"])
        except User.DoesNotExist:
            raise serializers.ValidationError({"visible_user_id": "User not found"})

        try:
            suggested_user = User.objects.get(id=attrs["suggested_user_id"])
        except User.DoesNotExist:
            raise serializers.ValidationError({"suggested_user_id": "User not found"})

        # CRITICAL RULE: subscriber must be visible to this bondmaker
        is_visible = Visibility.objects.filter(
            owner=visible_user,
            bondmaker=bondmaker,
            is_active=True,
            expires_at__gt=timezone.now(),
        ).exists()

        if not is_visible:
            raise serializers.ValidationError(
                "You can only suggest users to people currently visible to you."
            )

        # Prevent suggesting the same user to themselves
        if visible_user == suggested_user:
            raise serializers.ValidationError(
                "You cannot suggest a user to themselves."
            )

        # Attach for view reuse
        attrs["subscriber"] = visible_user
        attrs["suggested_user"] = suggested_user

        return attrs


class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "age",
            "profile_picture",
        ]


class SuggestedMatchSerializer(serializers.ModelSerializer):
    suggested_user = SimpleUserSerializer(read_only=True)

    class Meta:
        model = SuggestedMatch
        fields = [
            "id",
            "suggested_user",
            "created_at"
        ]


class VisibilitySerializer(serializers.ModelSerializer):
    bondmaker_id = serializers.IntegerField(write_only=True)
    owner_id = serializers.IntegerField(source="owner.id", read_only=True)

    class Meta:
        model = Visibility
        fields = ["id", "owner_id", "bondmaker_id", "visibility", "status"]
        read_only_fields = ["owner_id", "status"]

    def validate(self, attrs):
        owner = self.context["request"].user
        bondmaker_id = attrs["bondmaker_id"]
        visibility_type = attrs["visibility"]

        try:
            bondmaker = User.objects.get(id=bondmaker_id, is_matchmaker=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid bondmaker.")

        # Prevent multiple active public visibility
        if visibility_type == "public":
            already_public = (
                Visibility.objects.filter(
                    owner=owner,
                    visibility="public",
                    status="approved",
                    expires_at__gt=timezone.now(),
                )
                .exclude(bondmaker=bondmaker)
                .exists()
            )

            if already_public:
                raise serializers.ValidationError(
                    "You are already publicly visible under another bondmaker."
                )

            existing = Visibility.objects.filter(
                owner=owner, bondmaker=bondmaker, status="pending"
            ).exists()

            if existing:
                raise serializers.ValidationError(
                    "You have already sent a visibility request to this bondmaker."
                )

        attrs["bondmaker"] = bondmaker
        return attrs

    def create(self, validated_data):
        owner = self.context["request"].user
        bondmaker = validated_data.pop("bondmaker")
        visibility_type = validated_data["visibility"]

        visibility, _ = Visibility.objects.update_or_create(
            owner=owner,
            bondmaker=bondmaker,
            defaults={
                "visibility": visibility_type,
                "status": "pending",
                "expires_at": None,
            },
        )

        # Notify Bondmaker
        notify_user(
            user=visibility.bondmaker,
            title="New Public Visibility Request",
            message=f"{visibility.owner.email} requested public visibility.",
            data={
                "type": "public_visibility_request",
                "visibility_id": visibility.id,
                "visibility_type": visibility_type,
            },
        )

        # Delegate to service layer
        if visibility_type == "private":
            VisibilityService.request_private_visibility(visibility)

        return visibility


class ApproveVisibilitySerializer(serializers.ModelSerializer):

    class Meta:
        model = Visibility
        fields = ["id", "owner_id", "status"]
        read_only_fields = ["id", "owner_id"]

    def validate_status(self, value):
        if value not in ["approved", "rejected"]:
            raise serializers.ValidationError("Invalid action.")
        return value

    def update(self, instance, validated_data):
        status = validated_data["status"]

        if status == "approved":
            VisibilityService.approve(instance)
        else:
            VisibilityService.reject(instance)

        return instance


class MatchRequestSerializer(serializers.Serializer):
    bondmaker_id = serializers.IntegerField()
    target_user_id = serializers.IntegerField()
    coins = serializers.IntegerField(min_value=1)

    def validate_bondmaker_id(self, value):
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Bondmaker not found")
        if not user.is_matchmaker:
            raise serializers.ValidationError("Selected user is not a bondmaker")
        return value

    def validate_taget_user(self, attrs):
        target_user = User.objects.get(id=attrs["target_user_id"])

        visibility = Visibility.objects.filter(
            owner=target_user,
            visibility__in=["public", "private"],
            expires_at__gt=timezone.now(),
        ).select_related("bondmaker").first()

        if not visibility:
            raise serializers.ValidationError(
                {"target_user_id": "Target user is not under any active bondmaker."}
            )

        attrs["bondmaker"] = visibility.bondmaker
        return attrs

    def validate(self, attrs):
        user = self.context["request"].user
        if user.id == attrs["target_user_id"]:
            raise serializers.ValidationError(
                "You cannot send a match request to yourself"
            )
        return attrs


class VisibilityStatusSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(source="owner.id", read_only=True)
    bondmaker_id = serializers.IntegerField(source="bondmaker.id", read_only=True)
    visibility_choice = serializers.CharField(source="visibility", read_only=True)
    current_status = serializers.CharField(source="status", read_only=True)

    class Meta:
        model = Visibility
        fields = ["id", "owner_id", "bondmaker_id", "visibility_choice", "current_status"]


class BondmakerMatchActionResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    platform_share_usd = serializers.FloatField(required=False)
    bondmaker_share_usd = serializers.FloatField(required=False)


class BondmakerMatchActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["accepted", "rejected"])


class UserSwipeCardSerializer(serializers.ModelSerializer):
    bondmaker = serializers.SerializerMethodField()
    # distance_km = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "age",
            "gender",
            "bio",
            "hobbies",
            "interests",
            "profile_picture",
            "bondmaker",
        ]

    def get_bondmaker(self, obj) -> List:
        visibility = obj.visibility_settings.filter(
            visibility="public",
            status="approved",
            expires_at__gt=timezone.now(),
        ).select_related("bondmaker").first()

        if visibility and visibility.bondmaker:
            bondmaker_user = visibility.bondmaker
            return {
                "id": bondmaker_user.id,
                "name": bondmaker_user.name,
                "avatar": bondmaker_user.profile_picture,
                "verified": bondmaker_user.is_matchmaker,
            }

        return None

    def get_distance_km(self, obj):
        # Calculate distance between request.user and obj
        request_user = self.context.get("request").user
        if request_user.has_location and obj.has_location:
            return round(
                calculate_distance(
                    request_user.location_coordinates,
                    obj.location_coordinates,
                ),
                2,
            )
        return None


class PendingMatchUserSerializer(serializers.ModelSerializer):
    requester_id = serializers.IntegerField(source="user1.id")
    requester_name = serializers.CharField(source="user1.name")
    requester_profile_picture = serializers.CharField(source="user1.profile_picture")
    target_id = serializers.IntegerField(source="user2.id")
    target_name = serializers.CharField(source="user2.name")
    target_profile_picture = serializers.CharField(source="user2.profile_picture")
    distance = serializers.SerializerMethodField()
    match_score = serializers.SerializerMethodField()
    status = serializers.CharField()
    match_request_id = serializers.IntegerField(source="match_request.id")

    class Meta:
        model = UserMatch
        fields = [
            "id",
            "match_request_id",
            "requester_id",
            "requester_name",
            "requester_profile_picture",
            "target_id",
            "target_name",
            "target_profile_picture",
            "distance",
            "match_score",
            "status",
            "created_at"
        ]

    def get_distance(self, obj) -> Optional[float]:
        """Calculate distance between user1 and user2 on the fly"""
        if obj.user1.has_location and obj.user2.has_location:
            return calculate_distance(
                obj.user1.location_coordinates, obj.user2.location_coordinates
            )
        return None

    def get_match_score(self, obj) -> float:
        """Calculate match score dynamically"""
        return calculate_match_score(obj.user1, obj.user2)


class BondmakerSpecialisationSerializer(serializers.ModelSerializer):
    categories = serializers.SlugRelatedField(
        slug_field="category",
        queryset=Specialisation.objects.all(),
        many=True,
        source="specialisations",
    )

    class Meta:
        model = User
        fields = ["categories"]

    def validate_categories(self, value):
        user = self.context["request"].user

        if not user.is_matchmaker:
            raise serializers.ValidationError(
                "Only bondmakers can set specialisations."
            )

        if len(value) > 5:
            raise serializers.ValidationError("Maximum of 5 specialisations allowed.")

        return value

    # def update(self, instance, validated_data):
    #     categories = validated_data.get("categories")

    #     specialisations = []
    #     for category in categories:
    #         spec, _ = Specialisation.objects.get_or_create(category=category)
    #         specialisations.append(spec)

    #     instance.specialisations.set(specialisations)

    #     return instance


# Bondmaker List Serializer (For Search)
class BondmakerSearchListSerializer(serializers.ModelSerializer):
    specialisations = serializers.StringRelatedField(many=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "specialisations"]


class SpecialisationCategorySerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()


class BondmakerDashboardSerializer(serializers.Serializer):
    bondmaker_id = serializers.IntegerField()
    bondmaker_name = serializers.CharField(read_only=True)
    bondmaker_profile_picture = serializers.URLField()
    level = serializers.IntegerField()
    total_matches = serializers.IntegerField()
    matches_to_next_level = serializers.IntegerField()
    progress_to_next_level = serializers.FloatField()
    # pending_match_requests = serializers.IntegerField()
    live_profiles = serializers.IntegerField()
    net_subscribers = serializers.IntegerField()
    profile_views = serializers.IntegerField()
    # wallet_balance = serializers.DictField(child=serializers.IntegerField())
    recent_activity = serializers.ListField()
    # daily_tasks = serializers.ListField()
    # streak_days = serializers.IntegerField()
    # badges = serializers.ListField()


class BondmakerAnalyticsSerializer(serializers.Serializer):
    period_days = serializers.IntegerField()

    matches = serializers.IntegerField()
    matches_growth_percentage = serializers.FloatField()

    live_profiles = serializers.IntegerField()
    live_profiles_growth_percentage = serializers.FloatField()

    net_subscribers = serializers.IntegerField()
    net_subscribers_growth_percentage = serializers.FloatField()

    likes = serializers.IntegerField()
    likes_growth_percentage = serializers.FloatField()
    comments = serializers.IntegerField()
    comments_growth_percentage = serializers.FloatField()

    earnings = serializers.FloatField()

    badge_earned = serializers.IntegerField()
    badge_progress_levels_remaining = serializers.IntegerField()

    chart_data = serializers.ListField()
    completed_tasks = serializers.IntegerField()
    completed_tasks_growth_percentage = serializers.FloatField()


class MatchUserMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "age",
            "profile_picture",
        ]


class MatchedUserSerializer(serializers.ModelSerializer):
    user1_id = serializers.IntegerField(source="user1.id", read_only=True)
    user2_id = serializers.IntegerField(source="user2.id", read_only=True)

    other_user = serializers.SerializerMethodField()
    other_user_profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = UserMatch
        fields = [
            "id",
            "user1_id",
            "user2_id",
            "other_user",
            "other_user_profile_picture",
            "match_score",
            "distance",
            "status",
            "updated_at",
        ]

    @extend_schema_field(MatchUserMiniSerializer)
    def get_other_user(self, obj) -> dict:
        request_user = self.context["request"].user
        other = obj.user2 if obj.user1 == request_user else obj.user1
        return MatchUserMiniSerializer(other).data

    @extend_schema_field(serializers.URLField)
    def get_other_user_profile_picture(self, obj) -> str:
        request_user = self.context["request"].user
        other = obj.user2 if obj.user1 == request_user else obj.user1
        return other.profile_picture


class IncomingPendingMatchSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user1.name", read_only=True)
    age = serializers.IntegerField(source="user1.age", read_only=True)
    profile_picture = serializers.URLField(
        source="user1.profile_picture", read_only=True
    )

    class Meta:
        model = UserMatch
        fields = [
            "id",
            "name",
            "age",
            "profile_picture",
            "match_score",
            "distance",
            "created_at",
        ]


# Bond Circle Create View
class AddCircleMembersSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )

    def validate(self, attrs):
        bondmaker = self.context["request"].user

        if not bondmaker.is_matchmaker:
            raise serializers.ValidationError("Only bondmakers can add members.")

        if not hasattr(bondmaker, "bond_circle"):
            raise serializers.ValidationError("You must create a bond circle first.")

        user_ids = set(attrs["user_ids"])

        matched_user_ids = set(
            UserMatch.objects.filter(
                match_request__bondmaker=bondmaker,
                status="matched"
            ).filter(
                Q(user1_id__in=user_ids) | Q(user2_id__in=user_ids)
            ).values_list("user1_id", "user2_id")
        )

        # Flatten the tuples into a single set
        flattened_ids = set()
        for u1, u2 in matched_user_ids:
            if u1 in user_ids:
                flattened_ids.add(u1)
            if u2 in user_ids:
                flattened_ids.add(u2)

        invalid_ids = user_ids - flattened_ids

        if invalid_ids:
            raise serializers.ValidationError(
                f"Some users are not matched under you: {list(invalid_ids)}"
            )

        attrs["validated_user_ids"] = user_ids
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        bondmaker = self.context["request"].user
        circle = bondmaker.bond_circle
        user_ids = validated_data["validated_user_ids"]

        created_members = []

        for user_id in user_ids:
            member, created = BondCircleMember.objects.get_or_create(
                circle=circle, user_id=user_id, defaults={"added_by": bondmaker}
            )
            if created:
                created_members.append(user_id)

        return {"added_members": created_members, "count": len(created_members)}


class BondCirclePostSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.BooleanField(read_only=True)

    class Meta:
        model = BondCirclePost
        fields = [
            "id",
            "content",
            "author_name",
            "created_at",
            "likes_count",
            "comments_count",
            "is_liked",
        ]


class BondCircleCommentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = BondCirclePostComment
        fields = ["id", "post", "user", "user_name", "content", "created_at"]
        read_only_fields = ["user"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class BondCircleSerializer(serializers.ModelSerializer):

    class Meta:
        model = BondCircle
        fields = ["id", "name", "description", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        user = self.context["request"].user

        if not user.is_matchmaker:
            raise serializers.ValidationError(
                "Only bondmakers can create a bond circle."
            )

        if hasattr(user, "bond_circle"):
            raise serializers.ValidationError("You already have a bond circle.")

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = self.context["request"].user

        return BondCircle.objects.create(bondmaker=user, **validated_data)


class TogglePostLikeSerializer(serializers.Serializer):
    post_id = serializers.IntegerField(write_only=True)
    liked = serializers.BooleanField(read_only=True)

    def validate_post_id(self, value):
        try:
            post = BondCirclePost.objects.select_related("circle").get(id=value)
        except BondCirclePost.DoesNotExist:
            raise serializers.ValidationError("Post does not exist.")

        user = self.context["request"].user
        circle = post.circle

        # Permission check
        is_member = BondCircleMember.objects.filter(circle=circle, user=user).exists()

        if not (user == circle.bondmaker or is_member):
            raise serializers.ValidationError(
                "You are not allowed to interact with this post."
            )

        self.context["post"] = post
        return value

    @transaction.atomic
    def create(self, validated_data):
        user = self.context["request"].user
        post = self.context["post"]

        like, created = BondCirclePostLike.objects.get_or_create(post=post, user=user)

        if not created:
            like.delete()
            return {"liked": False}

        return {"liked": True}
