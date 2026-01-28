from rest_framework import serializers
from dating.serializers import (
    TokensSerializer,
    NotificationSettingsSerializer,
    LanguageSettingsSerializer,
    SocialAccountSerializer,
    UserProfileWithSocialSerializer,
    UserProfileSerializer,
)


class StatusMessageSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()


class ErrorWithDetailsSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    errors = serializers.DictField(required=False)


class SimpleStatusResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()


class CustomErrorResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()


class CoinTransactionSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField()
    transaction_type = serializers.CharField()
    amount = serializers.IntegerField()
    created_at = serializers.DateTimeField()


# Response when OTP is generated and sent
class AdminLoginOTPResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    otp_code = serializers.CharField(
        required=False
    )  # optional; only for debugging/testing


# Response when login with OTP is successful
class AdminLoginSuccessResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    admin_email = serializers.EmailField()
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    access_token_expires = serializers.DateTimeField()
    refresh_token_expires = serializers.DateTimeField()


class SupportedLanguagesResponseSerializer(serializers.Serializer):
    languages = serializers.DictField(child=serializers.CharField())
    total = serializers.IntegerField()


class TokenRefreshResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()
    tokens = TokensSerializer()


class PasswordResetResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()


class PasswordResetErrorResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()
    errors = serializers.DictField(required=False)


class PasswordResetConfirmRequestSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    new_password = serializers.CharField()


class PasswordResetConfirmResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()


class NotificationSettingsResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()
    settings = NotificationSettingsSerializer()


class NotificationSettingsErrorSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()
    errors = serializers.DictField(required=False)


class LanguageSettingsResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()
    settings = LanguageSettingsSerializer()


class LanguageSettingsErrorSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()
    errors = serializers.DictField(required=False)


class DeviceRegistrationRequestSerializer(serializers.Serializer):
    device_id = serializers.CharField()
    device_type = serializers.ChoiceField(choices=["android", "ios", "web"])
    push_token = serializers.CharField()


class DeviceRegistrationResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()
    device_id = serializers.CharField()
    created = serializers.BooleanField()


class ValidationErrorResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()
    errors = serializers.DictField()


class OAuthLinkAccountRequestSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=["google", "apple"])
    access_token = serializers.CharField(required=False)
    identity_token = serializers.CharField(required=False)


class OAuthLinkAccountResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()
    social_account = SocialAccountSerializer()


class OAuthUnlinkAccountResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()


class SocialAccountsListResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()
    social_accounts = SocialAccountSerializer(many=True)


class OAuthTokensSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    access_expires = serializers.DateTimeField()
    refresh_expires = serializers.DateTimeField()


class OAuthLoginResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    user = UserProfileWithSocialSerializer()
    tokens = OAuthTokensSerializer()


class StartLivenessResponseSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    status = serializers.CharField()
    actions_required = serializers.ListField(child=serializers.CharField())
    expires_at = serializers.DateTimeField(required=False)
    max_attempts = serializers.IntegerField(required=False)
    current_attempt = serializers.IntegerField(required=False)
    message = serializers.CharField()


class SubmitLivenessRequestSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    video_data = serializers.CharField()
    format = serializers.CharField(required=False)


class SubmitLivenessResponseSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    status = serializers.CharField()
    confidence = serializers.FloatField()
    actions_completed = serializers.ListField(child=serializers.CharField())
    can_retry = serializers.BooleanField()
    message = serializers.CharField()


class LivenessImageItemSerializer(serializers.Serializer):
    action = serializers.CharField()
    image_data = serializers.CharField()


class SubmitLivenessImagesRequestSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    images = LivenessImageItemSerializer(many=True)


class SubmitLivenessImagesResponseSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    status = serializers.CharField()
    confidence = serializers.FloatField()
    can_retry = serializers.BooleanField()
    message = serializers.CharField()


class RetryLivenessRequestSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()


class RetryLivenessResponseSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    actions_required = serializers.ListField(child=serializers.CharField())
    expires_at = serializers.DateTimeField()
    attempt_number = serializers.IntegerField()
    max_attempts = serializers.IntegerField()
    message = serializers.CharField()


class EmailOTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class EmailOTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=10)


class PhoneOTPRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    country_code = serializers.CharField(default="+1")
    user_id = serializers.IntegerField(required=True)


class PhoneOTPVerifySerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    country_code = serializers.CharField(default="+1")
    otp_code = serializers.CharField(max_length=10)


class OTPResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(required=False)
    expires_in = serializers.IntegerField(required=False)
    user = serializers.DictField(required=False)


class ResendOTPResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()


# User registration response
class UserRegisterResponseSerializer(serializers.Serializer):
    message = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    user = UserProfileSerializer()
    tokens = TokensSerializer()


class UserRegisterErrorSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()


# User login response
class UserLoginResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()
    user = UserProfileSerializer()
    tokens = TokensSerializer()


# User login validation error
class UserLoginValidationErrorSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()
    errors = serializers.DictField()


# User login unauthorized error
class UserLoginUnauthorizedSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()


# User login general error
class UserLoginErrorSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()


class AuthTokensSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
