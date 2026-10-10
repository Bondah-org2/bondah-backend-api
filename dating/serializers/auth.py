from ..models.users import PasswordResetPurpose
import hmac
import logging
from dating.tasks import send_otp_email
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from datetime import timedelta
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import F
from datetime import date
from rest_framework.validators import UniqueValidator
from ..models import User, EmailVerification, PhoneVerification, PasswordResetOTP, SecurityPin
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


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
    # firebase_token = serializers.CharField(required=False)
    email = serializers.EmailField()
    password = serializers.CharField()


class UserLogoutRequestSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(required=False)


class TokensSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class TokenRefreshRequestSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


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
                # Signing in during the 30-day grace period cancels a deletion
                from ..services import account_service

                user = account_service.find_for_sign_in(email, password)
                if user:
                    attrs["deletion_cancelled"] = account_service.cancel_deletion(user)
            if not user:
                raise serializers.ValidationError("Invalid credentials.")
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled.")
            if user.status == "banned":
                from ..authentication import AccountBanned

                raise AccountBanned({
                    "detail": user.status_reason or AccountBanned.default_detail,
                    "code": "account_banned",
                })
            attrs["user"] = user
            return attrs
        else:
            raise serializers.ValidationError("Must include email and password.")


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    purpose = serializers.CharField(default=PasswordResetPurpose.PASSWORD_RESET)


class PasswordResetConfirmSerializer(serializers.Serializer):
    reset_token = serializers.UUIDField()
    new_password = serializers.CharField(validators=[validate_password])
    new_password_confirm = serializers.CharField()
    purpose = serializers.CharField(default=PasswordResetPurpose.PASSWORD_RESET)


    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match."}
            )
        return attrs

    def save(self, **kwargs):
        reset_token = self.validated_data["reset_token"]
        purpose = self.validated_data["purpose"]

        # Atomic operation to ensure the token is used only once
        with transaction.atomic():
            otp_record = get_object_or_404(
                PasswordResetOTP,
                reset_token=reset_token,
                purpose=purpose,
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
                BlacklistedToken.objects.get_or_create(token=token)

        return user


class ChangeLoginInfoSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_email = serializers.EmailField(required=False)
    new_password = serializers.CharField(required=False)

    def validate(self, attrs):
        current_password = attrs.get("current_password")
        new_email = attrs.get("new_email")
        new_password = attrs.get("new_password")

        request = self.context["request"]
        
        if not request.user.check_password(current_password):
            raise serializers.ValidationError({"current_password": "Incorrect password."})
        
        if new_email and User.objects.filter(email=new_email).exclude(id=request.user.id).exists():
            raise serializers.ValidationError({"new_email": "Email already in use."})

        if new_password:
            try:
                validate_password(new_password, user=request.user)
            except ValidationError as exc:
                raise serializers.ValidationError({"new_password": list(exc.messages)})

        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        new_email = self.validated_data.get("new_email")
        new_password = self.validated_data.get("new_password")

        if new_email:
            user.pending_email = new_email

        if new_password:
            user.set_password(new_password)

        user.save()
        return user
        
        if new_password:
            self.request.user.set_password(new_password)
        
        self.request.user.save()
        
        return self.request.user


class SecurityPinSetupSerializer(serializers.Serializer):
    pin = serializers.CharField(min_length=4, max_length=4)
    confirm_pin = serializers.CharField(min_length=4, max_length=4)

    def validate(self, attrs):
        pin = attrs.get("pin")
        confirm_pin = attrs.get("confirm_pin")

        if not pin.isdigit():
            raise serializers.ValidationError({"pin": "PIN must be exactly 4 digits."})

        if pin != confirm_pin:
            raise serializers.ValidationError({"confirm_pin": "PINs do not match."})

        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        pin = self.validated_data["pin"]

        security_pin, _ = SecurityPin.objects.get_or_create(user=user)
        security_pin.set_pin(pin)
        security_pin.save()

        return security_pin


class TwoStepVerifyOTPSerializer(serializers.Serializer):
    otp = serializers.CharField()


class PasswordResetResendSerializer(serializers.Serializer):
    email = serializers.EmailField()


class OTPSerializer(serializers.Serializer):
    otp = serializers.CharField()
    email = serializers.EmailField()
    purpose = serializers.CharField(default=PasswordResetPurpose.PASSWORD_RESET)


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

        # The live code for this email; wrong guesses count against it
        verification = (
            EmailVerification.objects.filter(email=email, is_used=False)
            .order_by("-created_at")
            .first()
        )

        if not verification:
            raise serializers.ValidationError("Invalid OTP.")

        if verification.failed_attempts >= EmailVerification.MAX_ATTEMPTS:
            raise serializers.ValidationError("Too many wrong codes. Request a new code.")

        if verification.is_expired():
            raise serializers.ValidationError("OTP expired.")

        if not hmac.compare_digest(str(verification.otp_code), str(otp_code)):
            EmailVerification.objects.filter(pk=verification.pk).update(
                failed_attempts=F("failed_attempts") + 1
            )
            raise serializers.ValidationError("Invalid OTP.")

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
        import re

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
        verification.failed_attempts = 0
        verification.save()

        try:
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
        if verification.user is None:
            raise serializers.ValidationError("Invalid or unverified registration token.")
        if verification.user.date_of_birth and verification.user.date_of_birth != dob:
            # The age check runs once; a retry with the same date is fine
            raise serializers.ValidationError("Your date of birth is already set.")
        attrs["user"] = verification.user
        return attrs


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
