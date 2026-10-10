from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from ..constants import QUESTION_UI_CONFIG
from ..media_refs import MediaRefsMixin
from ..models import User, UserSecurityQuestion, UserSocialHandle, BondmakerSubscription, SuggestedMatch, Visibility, Specialisation
from ..models.username import UsernameValidation, validate_username_format
from .users import IdentityFieldsMixin, SimpleUserSerializer, UserSecurityQuestionDisplaySerializer, UserSecurityQuestionUpdateSerializer


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


# The "About your work" step sends these two; they are stored as answers
WORK_ANSWER_FIELDS = {"business_type": "business_service", "provides_guidance": "relationship_guidance"}
# Older app builds sent "community_service"; the stored choice is "community"
CHOICE_ALIASES = {"community_service": "community"}
MAX_SKILLS = 15
MAX_SOCIAL_HANDLES = 10


class SocialHandleInputSerializer(serializers.Serializer):
    platform = serializers.ChoiceField(choices=UserSocialHandle.PLATFORM_CHOICES)
    url = serializers.URLField(max_length=500)


class BondmakerProfileUpdateSerializer(IdentityFieldsMixin, MediaRefsMixin, serializers.ModelSerializer):
    """The bondmaker setup steps and the bondmaker profile edit screen.

    Every step sends only its own fields. Answers, skills and social links are
    validated here and saved in one transaction with the profile fields.
    """

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
    skills = serializers.ListField(
        child=serializers.CharField(max_length=40), source="bondmaker_skills", required=False
    )
    business_type = serializers.CharField(write_only=True, required=False)
    provides_guidance = serializers.CharField(write_only=True, required=False)
    social_handles = SocialHandleInputSerializer(many=True, write_only=True, required=False)

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
            "skills",
            "business_type",
            "provides_guidance",
            "social_handles",
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

    def validate_skills(self, value):
        cleaned = []
        for skill in value:
            skill = skill.strip()
            if skill and skill.lower() not in {c.lower() for c in cleaned}:
                cleaned.append(skill)
        if len(cleaned) > MAX_SKILLS:
            raise serializers.ValidationError(f"Add up to {MAX_SKILLS} skills.")
        return cleaned

    def validate_social_handles(self, value):
        if len(value) > MAX_SOCIAL_HANDLES:
            raise serializers.ValidationError(f"Add up to {MAX_SOCIAL_HANDLES} links.")
        platforms = [h["platform"] for h in value]
        if len(platforms) != len(set(platforms)):
            raise serializers.ValidationError("Add one link per platform.")
        return value

    @staticmethod
    def _clean_answer(question_type, answer):
        config = QUESTION_UI_CONFIG.get(question_type, {"input_type": "text"})
        answer = (answer or "").strip()
        if config["input_type"] == "choice":
            answer = CHOICE_ALIASES.get(answer, answer)
            allowed = {c["value"] for c in config["choices"]}
            if answer not in allowed:
                raise serializers.ValidationError(
                    {question_type: f"Choose one of: {', '.join(sorted(allowed))}."}
                )
            return None, answer
        if not answer:
            raise serializers.ValidationError({question_type: "This answer can't be empty."})
        if len(answer) > 2000:
            raise serializers.ValidationError({question_type: "Keep this answer under 2000 characters."})
        return answer, None

    def validate(self, attrs):
        attrs = super().validate(attrs)
        answers = {}
        for q in attrs.pop("security_questions_update", []):
            answers[q["question_type"]] = self._clean_answer(q["question_type"], q["answer"])
        for field, question_type in WORK_ANSWER_FIELDS.items():
            if field in attrs:
                answers[question_type] = self._clean_answer(question_type, attrs.pop(field))
        attrs["_answers"] = answers
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        answers = validated_data.pop("_answers", {})
        handles = validated_data.pop("social_handles", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        for question_type, (text, choice) in answers.items():
            UserSecurityQuestion.objects.update_or_create(
                user=instance,
                question_type=question_type,
                defaults={"response_text": text, "response_choice": choice},
            )

        if handles is not None:
            # The step sends the full list, so it replaces what was there
            UserSocialHandle.objects.filter(user=instance).delete()
            UserSocialHandle.objects.bulk_create(
                [UserSocialHandle(user=instance, platform=h["platform"], url=h["url"]) for h in handles]
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
