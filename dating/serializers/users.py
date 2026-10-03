from rest_framework import serializers
from django.utils.timezone import now
from datetime import timedelta
from django.utils import timezone
from datetime import date
from ..models import Activity, User, DeviceRegistration, UserRoleSelection, UserInterest, UserProfileView, UserInteraction, SearchQuery, UserSocialHandle, UserSecurityQuestion, DocumentVerification, Visibility, Notification, Specialisation
from drf_spectacular.utils import extend_schema_field
from ..location_utils import calculate_match_score
from ..models.username import clean_and_validate_username
from ..media_refs import MediaRefsMixin


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
            # "bondcoin_balance",
        ]
        read_only_fields = [
            "id",
            # "bondcoin_balance",  # Financial data should be read-only
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
        fields = [
            "push_notifications_enabled",
            "email_notifications_enabled",
            "notify_on_new_match",
            "notify_on_message",
            "notify_on_like",
            "notify_on_bondmaker_update",
            "notify_on_promotional",
        ]

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
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
# SOCIAL MEDIA HANDLES SERIALIZERS (NEW FROM FIGMA)
# =============================================================================
class UserSocialHandleSerializer(serializers.ModelSerializer):
    """Serializer for user social media handles"""

    class Meta:
        model = UserSocialHandle
        fields = ["id", "platform", "url", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserSocialHandleCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating user social media handles"""

    class Meta:
        model = UserSocialHandle
        fields = ["platform", "url"]

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


class SecurityQuestionSerializer(serializers.ModelSerializer):
    question = serializers.CharField(source="get_question_type_display")

    class Meta:
        model = UserSecurityQuestion
        fields = [
            "id",
            "question_type",
            "question",
            "response_text",
            "response_choice",
        ]


class UsernameUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username"]

    def validate_username(self, value):
        user = self.context["request"].user
        return clean_and_validate_username(value, exclude_user_id=user.id)


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


class DeviceRegistrationSerializer(serializers.ModelSerializer):
    device_id = serializers.CharField()

    class Meta:
        model = DeviceRegistration
        fields = ["device_id", "device_type", "push_token", "token_type"]

    def validate_device_type(self, value):
        if value not in ["ios", "android"]:
            raise serializers.ValidationError("Device type must be ios or android.")
        return value

    def create(self, validated_data):
        user = self.context["request"].user

        device_id = validated_data["device_id"]

        # deactivate old tokens
        DeviceRegistration.objects.filter(
            user=user, device_id=device_id
        ).update(is_active=False)

        device, created = DeviceRegistration.objects.update_or_create(
            device_id=device_id,
            user=user,
            defaults={
                "token_type": validated_data.get("token_type", "expo"),
                "device_type": validated_data["device_type"],
                "push_token": validated_data["push_token"],
                "is_active": True,
            },
        )

        return device


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


# =============================================================================
# ADVANCED USER PROFILE SERIALIZERS
# =============================================================================
class UserProfileDetailSerializer(MediaRefsMixin, serializers.ModelSerializer):
    """Detailed user profile serializer for viewing other users"""

    media_ref_fields = {
        "profile_picture": ("profile_picture",),
        "profile_gallery": ("profile_gallery",),
        "bondmaker_profile_picture": ("bondmaker_profile_picture",),
        "bondmaker_cover_picture": ("bondmaker_cover_picture",),
    }

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
    profile_gallery = serializers.ListField(child=serializers.CharField(max_length=500))
    speciality = serializers.SlugRelatedField(
        slug_field="category",
        queryset=Specialisation.objects.all(),
        many=True,
        source="specialisations",
    )
    # visibility_status = serializers.SerializerMethodField()
    # visibility_choice = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "age",
            "email",
            "gender",
            "username",
            "bio",
            "bondmaker_bio",
            "thought_leadership",
            "profile_picture",
            "bondmaker_profile_picture",
            "bondmaker_cover_picture",
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
            "want_kids",
            "ethnicity",
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
            "selected_role",
            "traits",
            "genotype",
            "location",
            "age",
            "date_of_birth",
            "preferred_gender",
            "job_title",
            "company_name",
            "deal_breaker",
            "speciality",
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
            "username",
            "speciality"
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
            from ..location_utils import calculate_match_score

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
    speciality = serializers.SlugRelatedField(
        slug_field="category",
        queryset=Specialisation.objects.all(),
        many=True,
        source="specialisations",
    )

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
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
            "selected_role",
            "profile_completion_percentage",
            "company_name",
            "job_title",
            "deal_breaker",
            "speciality"
        ]

        read_only_fields = ["speciality"]

    def get_selected_role(self, obj) -> str:
        role_selection = getattr(obj, "role_selection", None)
        return role_selection.selected_role if role_selection else None


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


class PushNotificationSerializer(serializers.Serializer):
    token = serializers.CharField()
    title = serializers.CharField(default="Notification")
    body = serializers.CharField(default="Message")


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


class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "age",
            "profile_picture",
        ]


class MessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField()


# ======================================== ACTIVITY FEEDS
class ActivityFeedSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.name", read_only=True)
    message = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = [
            "id",
            "actor",
            "actor_name",
            "action",
            "metadata",
            "message",
            "created_at",
        ]
        read_only_fields = fields

    def get_message(self, obj):
        return obj.render_message()
