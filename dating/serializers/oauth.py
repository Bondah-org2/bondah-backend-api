from rest_framework import serializers
from ..models import User, SocialAccount


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


class SocialLoginSerializer(serializers.Serializer):
    provider = serializers.CharField()
    access_token = serializers.CharField()

    def validate_provider(self, value):
        if value not in ["google", "apple"]:
            raise serializers.ValidationError("Provider must be google or apple.")
        return value


# OAuth Serializers
class GoogleOAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField(required=False)
    access_token = serializers.CharField(required=False)
    
    def validate(self, attrs):
        if not attrs.get("id_token") and not attrs.get("access_token"):
            raise serializers.ValidationError(
                "Either id_token or access_token is required."
            )
        return attrs


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


class GoogleCallbackSerializer(serializers.Serializer):
    code = serializers.CharField(
        required=True,
        help_text="Authorization code returned by Google OAuth"
    )
