"""Response serializers for API documentation and custom structured responses.

This module contains serializers purely used for generating correct
OpenAPI schemas (via drf-spectacular) and standardizing error/success
JSON shapes across the application.
"""

from rest_framework import serializers
from dating.serializers import (
    LanguageSettingsSerializer,
    NotificationSettingsSerializer,
    SocialAccountSerializer,
    UserProfileSerializer,
    UserProfileWithSocialSerializer,
    TokensSerializer,
)


class StatusMessageSerializer(serializers.Serializer):
    """Standard serializer for a response returning a status and message."""

    status = serializers.CharField()
    message = serializers.CharField()


class ErrorWithDetailsSerializer(serializers.Serializer):
    """Standard error response serializer containing details/errors object."""

    status = serializers.CharField()
    message = serializers.CharField()
    errors = serializers.DictField(required=False)


class SimpleStatusResponseSerializer(serializers.Serializer):
    """Basic response showing status and message."""

    status = serializers.CharField()
    message = serializers.CharField()


class CustomErrorResponseSerializer(serializers.Serializer):
    """Unified custom error response structure."""

    message = serializers.CharField()
    status = serializers.CharField()


class CoinTransactionSerializer(serializers.Serializer):
    """Serializer representing a single coin transaction."""

    id = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField()
    transaction_type = serializers.CharField()
    amount = serializers.IntegerField()
    created_at = serializers.DateTimeField()


class AdminLoginOTPResponseSerializer(serializers.Serializer):
    """Response returned when an OTP is successfully sent for admin login."""

    status = serializers.CharField()
    message = serializers.CharField()
    otp_code = serializers.CharField(required=False)


class AdminLoginResponseSerializer(serializers.Serializer):
    """Response returned for basic admin login data."""

    access = serializers.CharField()
    refresh = serializers.CharField()
    user = serializers.DictField()


class AdminLoginSuccessResponseSerializer(serializers.Serializer):
    """Response returned when login with admin OTP is successful."""

    status = serializers.CharField()
    message = serializers.CharField()
    admin_email = serializers.EmailField()
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    access_token_expires = serializers.DateTimeField()
    refresh_token_expires = serializers.DateTimeField()


class SupportedLanguagesResponseSerializer(serializers.Serializer):
    """Response containing list of supported languages and total count."""

    languages = serializers.DictField(child=serializers.CharField())
    total = serializers.IntegerField()


class TokenRefreshResponseSerializer(serializers.Serializer):
    """Response containing refreshed JWT tokens."""

    message = serializers.CharField()
    status = serializers.CharField()
    tokens = TokensSerializer()


class NotificationSettingsResponseSerializer(serializers.Serializer):
    """Response returned on successful retrieval/update of notification settings."""

    message = serializers.CharField()
    status = serializers.CharField()
    settings = NotificationSettingsSerializer()


class NotificationSettingsErrorSerializer(serializers.Serializer):
    """Error response returning validation errors for notification settings."""

    message = serializers.CharField()
    status = serializers.CharField()
    errors = serializers.DictField(required=False)


class LanguageSettingsResponseSerializer(serializers.Serializer):
    """Response returned on successful retrieval/update of language settings."""

    message = serializers.CharField()
    status = serializers.CharField()
    settings = LanguageSettingsSerializer()


class LanguageSettingsErrorSerializer(serializers.Serializer):
    """Error response returning validation errors for language settings."""

    message = serializers.CharField()
    status = serializers.CharField()
    errors = serializers.DictField(required=False)


class DeviceRegistrationRequestSerializer(serializers.Serializer):
    """Request payload for registering/updating a user's mobile device."""

    device_id = serializers.CharField()
    device_type = serializers.ChoiceField(choices=["android", "ios", "web"])
    push_token = serializers.CharField()


class DeviceRegistrationResponseSerializer(serializers.Serializer):
    """Response returned on successful device registration."""

    message = serializers.CharField()
    status = serializers.CharField()
    device_id = serializers.CharField()
    created = serializers.BooleanField()


class ValidationErrorResponseSerializer(serializers.Serializer):
    """Unified validation error serializer showcasing fields and reasons."""

    message = serializers.CharField()
    status = serializers.CharField()
    errors = serializers.DictField()


class OAuthLinkAccountRequestSerializer(serializers.Serializer):
    """Request payload for linking an OAuth social provider to a user account."""

    provider = serializers.ChoiceField(choices=["google", "apple"])
    access_token = serializers.CharField(required=False)
    identity_token = serializers.CharField(required=False)


class OAuthLinkAccountResponseSerializer(serializers.Serializer):
    """Response returned on successful social account linkage."""

    message = serializers.CharField()
    status = serializers.CharField()
    social_account = SocialAccountSerializer()


class OAuthUnlinkAccountResponseSerializer(serializers.Serializer):
    """Response returned on successful social account unlink."""

    message = serializers.CharField()
    status = serializers.CharField()


class SocialAccountsListResponseSerializer(serializers.Serializer):
    """Response listing all active social logins connected to the user."""

    message = serializers.CharField()
    status = serializers.CharField()
    social_accounts = SocialAccountSerializer(many=True)


class OAuthTokensSerializer(serializers.Serializer):
    """Token details including expiration times returned during OAuth login."""

    access = serializers.CharField()
    refresh = serializers.CharField()
    access_expires = serializers.DateTimeField()
    refresh_expires = serializers.DateTimeField()


class OAuthLoginResponseSerializer(serializers.Serializer):
    """Response returned on successful OAuth registration or login."""

    status = serializers.CharField()
    message = serializers.CharField()
    user = UserProfileWithSocialSerializer()
    tokens = OAuthTokensSerializer()


class StartLivenessResponseSerializer(serializers.Serializer):
    """Response details returned when initiating a liveness check session."""

    session_id = serializers.UUIDField()
    status = serializers.CharField()
    actions_required = serializers.ListField(child=serializers.CharField())
    expires_at = serializers.DateTimeField(required=False)
    max_attempts = serializers.IntegerField(required=False)
    current_attempt = serializers.IntegerField(required=False)
    message = serializers.CharField()


class SubmitLivenessRequestSerializer(serializers.Serializer):
    """Request body for submitting the recorded video for liveness checks."""

    session_id = serializers.UUIDField()
    video_data = serializers.CharField()
    format = serializers.CharField(required=False)


class SubmitLivenessResponseSerializer(serializers.Serializer):
    """Response details returned after analyzing submitted liveness video."""

    session_id = serializers.UUIDField()
    status = serializers.CharField()
    confidence = serializers.FloatField()
    actions_completed = serializers.ListField(child=serializers.CharField())
    can_retry = serializers.BooleanField()
    message = serializers.CharField()


class LivenessImageItemSerializer(serializers.Serializer):
    """Individual action and corresponding base64 image representation."""

    action = serializers.CharField()
    image_data = serializers.CharField()


class SubmitLivenessImagesRequestSerializer(serializers.Serializer):
    """Request payload containing structured frames for liveness checks."""

    session_id = serializers.UUIDField()
    images = LivenessImageItemSerializer(many=True)


class SubmitLivenessImagesResponseSerializer(serializers.Serializer):
    """Response details returned after analyzing the set of frames."""

    session_id = serializers.UUIDField()
    status = serializers.CharField()
    confidence = serializers.FloatField()
    can_retry = serializers.BooleanField()
    message = serializers.CharField()


class RetryLivenessRequestSerializer(serializers.Serializer):
    """Request payload to request a session retry."""

    session_id = serializers.UUIDField()


class RetryLivenessResponseSerializer(serializers.Serializer):
    """Response containing required actions for a retried liveness session."""

    session_id = serializers.UUIDField()
    actions_required = serializers.ListField(child=serializers.CharField())
    expires_at = serializers.DateTimeField()
    attempt_number = serializers.IntegerField()
    max_attempts = serializers.IntegerField()
    message = serializers.CharField()


class ResendOTPResponseSerializer(serializers.Serializer):
    """Response returned on successful resending of an OTP code."""

    message = serializers.CharField()
    status = serializers.CharField()


class UserRegisterResponseSerializer(serializers.Serializer):
    """Response returned on successful new user registration completion."""

    message = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    user = UserProfileSerializer()
    tokens = TokensSerializer()


class UserRegisterErrorSerializer(serializers.Serializer):
    """Error response when user registration fails."""

    message = serializers.CharField()
    status = serializers.CharField()


class UserLoginResponseSerializer(serializers.Serializer):
    """Response returned on successful user credentials authentication."""

    message = serializers.CharField()
    status = serializers.CharField()
    user = UserProfileSerializer()
    tokens = TokensSerializer()


class UserLoginValidationErrorSerializer(serializers.Serializer):
    """Error response when login credentials fail validation."""

    message = serializers.CharField()
    status = serializers.CharField()
    errors = serializers.DictField()


class UserLoginUnauthorizedSerializer(serializers.Serializer):
    """Error response when login credentials are unauthorized."""

    message = serializers.CharField()
    status = serializers.CharField()


class UserLoginErrorSerializer(serializers.Serializer):
    """General error response for user login failures."""

    message = serializers.CharField()
    status = serializers.CharField()


class AuthTokensSerializer(serializers.Serializer):
    """Standardized representation of access and refresh JWT tokens."""

    access = serializers.CharField()
    refresh = serializers.CharField()


class PasswordResetVerifyOTPResponseSerializer(serializers.Serializer):
    """Response schema on successful OTP verification during password reset."""

    status = serializers.CharField()
    message = serializers.CharField()
    reset_token = serializers.UUIDField()


class RegisterRequestOTPResponseSerializer(serializers.Serializer):
    """Response schema on successful registration OTP request."""

    message = serializers.CharField()
    registration_token = serializers.UUIDField()


class RegisterVerifyOTPResponseSerializer(serializers.Serializer):
    """Response schema on successful verification of a registration OTP."""

    status = serializers.CharField()
    message = serializers.CharField()
    registration_token = serializers.UUIDField()
