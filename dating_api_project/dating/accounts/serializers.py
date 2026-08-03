import re
from logging import getLogger
from datetime import timedelta, date
from typing import List

from django.db import transaction
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.validators import UniqueValidator
from rest_framework import serializers

from dating.models import (
    User,
    PasswordResetOTP,
    EmailVerification,
    AdminRole,
    SocialAccount,
    AdminPermission,
    DeviceRegistration
)
from dating.tasks import send_otp_email


logger = getLogger(__name__)


# =============================================================================
# AUTH AND REGISTRATION SERIALIZERS
# =============================================================================

class UserLoginRequestSerializer(serializers.Serializer):
    # firebase_token = serializers.CharField(required=False)
    email = serializers.EmailField()
    password = serializers.CharField()


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


class UserLogoutRequestSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(required=False)


class TokenRefreshRequestSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetResendSerializer(serializers.Serializer):
    email = serializers.EmailField()


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

            # Invalidate Refresh Token so as to prevent anyone with refresh being able to have access to account
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

            tokens = OutstandingToken.objects.filter(user=user)
            for token in tokens:
                try:
                    BlacklistedToken.objects.get_or_create(token=token)
                except Exception:
                    logger.exception(
                        "Failed to blacklist token %s",
                        token.jti
                    )

        return user


class OTPSerializer(serializers.Serializer):
    otp = serializers.CharField()
    email = serializers.EmailField()


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


        try:
            logger.info(f"About to send token: {verification.otp_code}")
            send_otp_email.delay(email, verification.otp_code)
        except Exception:
            logger.error("Code not sent", exc_info=True)
        return {
            "message": "OTP sent to your email",
            "registration_token": str(verification.registration_token),
        }


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

        return {
            "status": "success",
            "message": "OTP verified successfully.",
            "registration_token": str(verification.registration_token),
        }


class ConfirmRegistrationSerializer(serializers.Serializer):

    import re

    registration_token = serializers.UUIDField()
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        token = attrs["registration_token"]
        password = attrs["password"]
        password_confirm = attrs["password_confirm"]

        # Validate password
        ConfirmRegistrationSerializer.validate_password_strength(password)

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
    
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Validate that the password meets the strength requirements:
        - At least 8 characters long
        - Contains at least one uppercase letter
        - Contains at least one lowercase letter
        - Contains at least one digit
        - Contains at least one special character
        """
        
        if len(v) < 8:
            raise serializers.ValidationError(
                "Password must be at least 8 characters long"
            )
        
        if not re.search(r"[A-Z]", v):
            raise serializers.ValidationError(
                "Password must contain at least one uppercase letter"
            )
        
        if not re.search(r"[a-z]", v):
            raise serializers.ValidationError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise serializers.ValidationError("Password must contain at least one digit")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise serializers.ValidationError("Password must contain at least one special character")
        return v


    def create(self, validated_data):
        verification = validated_data["verification"]
        password = validated_data["password"]

        user = User.objects.create_user(
            username=verification.email,
            email=verification.email,
            password=password,
        )

        # Set user to false initially until after date of birth has been confirmed.
        user.is_active = False
        user.save(update_fields=["is_active"])

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

        # Invalidate other OTPs (exclude current one)
        EmailVerification.objects.filter(
            email=verification.email,
            is_used=False
        ).exclude(pk=verification.pk).update(is_used=True)

        verification.otp_code = EmailVerification.generate_otp()
        verification.expires_at = timezone.now() + timedelta(minutes=10)
        verification.save()
        print(verification.otp_code)

        try:
            logger.info(f"About to send token: {verification.otp_code}")
            # Send OTP email
            send_otp_email.delay(
                verification.email,
                verification.otp_code
            )
        except Exception:
            logger.error("Code not sent", exc_info=True)


        return {
            "message": "OTP resent successfully",
            "registration_token": str(verification.registration_token),
        }


class VerifyAgeSerializer(serializers.Serializer):
    
    registration_token = serializers.UUIDField(required=True)
    date_of_birth = serializers.DateField(required=True)

    def validate(self, attrs):

        # Validate token exist and is already verified
        token = attrs["registration_token"]
        dob = attrs['date_of_birth']

        # Get recently verified instance
        verification = EmailVerification.objects.filter(
            registration_token=token,
            is_used=True,
            is_verified=True
        ).order_by('-created_at').first()

        if not verification:
            raise serializers.ValidationError(
                "Invalid or unverified registration token."
            )

        # Validate Age
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 18:
            raise serializers.ValidationError(
                {
                    'date_of_birth': 'You must be at least 18 years old to register.'
                }
            )
        attrs["user"] = verification.user
        return attrs


class MessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField()


# =============================================================================
# ADMIN ACCOUNT MANAGEMENT VIEWS
# =============================================================================

class AdminLoginSerializer(serializers.Serializer):

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):

        email = data.get("email")
        password = data.get("password")

        user = authenticate(username=email, password=password)

        if not user:
            raise serializers.ValidationError("Invalid login credentials")

        if not user.is_staff:
            raise serializers.ValidationError("Not an admin account")

        data["user"] = user

        return data


class AdminLogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs["refresh"]
        return attrs

    def save(self):
        try:
            token = RefreshToken(self.token)
            token.blacklist()
        except Exception:
            raise serializers.ValidationError("Invalid refresh token")


class AdminPermissionSerializer(serializers.ModelSerializer):
    can_view_overview = serializers.BooleanField(default=True)
    can_view_applications = serializers.BooleanField(default=False)
    can_view_withdrawals = serializers.BooleanField(default=False)
    can_view_reports = serializers.BooleanField(default=False)
    can_approve_applications = serializers.BooleanField(default=False)
    can_manage_team = serializers.BooleanField(default=False)

    class Meta:
        model = AdminPermission
        fields = [
            "can_view_overview",
            "can_view_applications",
            "can_view_withdrawals",
            "can_view_reports",
            "can_approve_applications",
            "can_manage_team"
        ]


class CreateTeamMemberSerializer(serializers.ModelSerializer):
    role = serializers.SlugRelatedField(
        queryset=AdminRole.objects.all(), slug_field="name"
    )
    permissions = AdminPermissionSerializer(
        required=False,
        write_only=True
    )
    permission_data = AdminPermissionSerializer(
        source="admin_permissions",
        required=False,
        read_only=True
    )

    class Meta:
        model = User
        fields = [
            "name",
            "email",
            "role",
            "permissions",
            "status",
            "password",
            "permission_data",
        ]
        extra_kwargs = {"password": {"write_only": True}}

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        principal_admin = request.user

        permissions_data = validated_data.pop("permissions", None)
        role = validated_data.pop("role")
        password = validated_data.pop("password")

        # Create user
        user = User(
            **validated_data,
            role=role,
            is_staff=True,
            created_by=principal_admin
        )
        user.set_password(password)
        user.save()

        # Create permission object
        perm_obj, created = AdminPermission.objects.get_or_create(user=user)

        permission_fields = [
            f.name for f in AdminPermission._meta.fields if f.name.startswith("can_")
        ]

        # Start with role defaults
        for field in permission_fields:
            setattr(perm_obj, field, getattr(role, field, False))

        # Override only provided permissions
        if permissions_data:
            for field, value in permissions_data.items():
                setattr(perm_obj, field, value)

        perm_obj.save()

        return user


class UpdateAdminMemberSerializer(serializers.ModelSerializer):

    role = serializers.SlugRelatedField(
        queryset=AdminRole.objects.all(),
        slug_field="name"
    )

    permissions = AdminPermissionSerializer(write_only=True, required=False)

    permission_data = AdminPermissionSerializer(
        source="admin_permissions",
        required=False,
        read_only=True
    )

    class Meta:
        model = User
        fields = [
            "name",
            "email",
            "role",
            "permissions",
            "status",
            "permission_data"
        ]

    @transaction.atomic
    def update(self, instance, validated_data):

        permissions_data = validated_data.pop("permissions", None)
        role = validated_data.pop("role", None)

        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if role:
            instance.role = role

        instance.save()

        perm_obj, _ = AdminPermission.objects.get_or_create(user=instance)

        if permissions_data is not None:
            # Manual override from client
            for field, value in permissions_data.items():
                setattr(perm_obj, field, value)

        elif role:
            # Sync from role ONLY if no manual permissions sent
            permission_fields = [
                f.name for f in AdminPermission._meta.fields if f.name.startswith("can_")
            ]
            for field in permission_fields:
                setattr(perm_obj, field, getattr(role, field))

        perm_obj.save()

        return instance


class RemoveAdminMemberSerializer(serializers.Serializer):
    id = serializers.IntegerField()


class TeamMemberSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    joined_date = serializers.SerializerMethodField()
    last_active = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "role",
            "permissions",
            "joined_date",
            "last_active",
            "status",
        ]

    def get_role(self, obj) -> str:
        return obj.role.name if obj.role else None

    def get_permissions(self, obj) -> List:
        perm = getattr(obj, "admin_permissions", None)
        if not perm:
            return []

        mapping = {
            "can_view_overview": "Overview",
            "can_view_applications": "Applications",
            "can_view_withdrawals": "Withdrawals",
            "can_view_reports": "Reports",
            "can_manage_team": "Team",
        }

        return [label for field, label in mapping.items() if getattr(perm, field, False)]

    def get_joined_date(self, obj) -> str:
        return obj.date_joined.strftime("%d-%m-%y")

    def get_last_active(self, obj) -> str:
        return obj.last_active.strftime("%d-%m-%y") if obj.last_active else None


# =============================================================================
# OAUTH AND SOCIAL ACCOUNTS VIEWS
# =============================================================================

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


# =============================================================================
# PROFILE AND SETTINGS
# =============================================================================

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

