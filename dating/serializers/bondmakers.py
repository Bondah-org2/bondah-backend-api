from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from ..constants import QUESTION_UI_CONFIG
from ..media_refs import MediaRefsMixin
from ..models import User, UserSecurityQuestion, BondmakerSubscription, SuggestedMatch, Visibility, Specialisation
from ..models.username import UsernameValidation, validate_username_format
from .users import SimpleUserSerializer, UserSecurityQuestionDisplaySerializer, UserSecurityQuestionUpdateSerializer


class BondmakerListSerializer(serializers.ModelSerializer):
    verification_status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "name",
            "username",
            "profile_picture"
            "email",
            "phone_number",
            "location",
            "verification_status",
        )

    def get_verification_status(self, obj) -> str:
        latest = obj.document_verifications.order_by("-uploaded_at").first()
        return latest.status if latest else None


class PublicBondmakerProfileSerializer(serializers.ModelSerializer):
    # verification_status = serializers.SerializerMethodField()
    age = serializers.ReadOnlyField()
    # accepted_match_count = serializers.IntegerField(read_only=True)
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
            "username",
            "bondmaker_profile_picture",
            "bondmaker_cover_picture",
            "age",
            "is_matchmaker",
            "bondmaker_bio",
            # "accepted_match_count",
            "speciality",
        ]

        read_only_fields = [
            "age",
        ]

    def get_verification_status(self, obj) -> str:
        verification = obj.document_verifications.first()
        if not verification:
            return "not_submitted"
        return verification.status


class BondmakerProfileUpdateSerializer(MediaRefsMixin, serializers.ModelSerializer):
    media_ref_fields = {
        "profile_picture": ("profile_picture",),
        "bondmaker_profile_picture": ("bondmaker_profile_picture",),
        "bondmaker_cover_picture": ("bondmaker_cover_picture",),
    }

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
            "bondmaker_bio",
            "thought_leadership",
            "email",
            "gender",
            "date_of_birth",
            "relationship_status",
            "education_level",
            "profile_picture",
            "security_questions",
            "security_questions_update",
            "bondmaker_profile_picture",
            "bondmaker_cover_picture",
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
    level_label = serializers.SerializerMethodField()
    total_matches = serializers.IntegerField()
    matches_to_next_level = serializers.IntegerField()
    progress_to_next_level = serializers.FloatField()

    def get_level_label(self, obj) -> str:
        level = obj.get("level", 1) if isinstance(obj, dict) else getattr(obj, "level", 1)
        labels = {
            1: "Newcomer",
            2: "Connector",
            3: "Matchmaker",
            4: "Expert",
            5: "Elite",
        }
        return labels.get(level, f"Level {level}")
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


# ======================================== lEADERBOARD
