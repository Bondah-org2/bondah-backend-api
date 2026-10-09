from dating.serializers import TwoStepVerifyOTPSerializer
from dating.tasks import send_password_reset_email
import logging
from dating.tasks import send_otp_email
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from django.utils import timezone
import uuid
from rest_framework import serializers
from django.core.exceptions import ValidationError
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from ..models import DeviceRegistration, PasswordResetOTP, PasswordResetPurpose
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.conf import settings
from ..serializers import CustomLoginSerializer, PasswordResetSerializer, PasswordResetConfirmSerializer, ChangeLoginInfoSerializer, UserProfileSerializer, VerifyAgeSerializer, UserLogoutRequestSerializer, UserLoginRequestSerializer, TokenRefreshRequestSerializer, RegisterRequestOTPSerializer, VerifyOTPSerializer, ResendEmailOTPSerializer, PasswordResetResendSerializer, OTPSerializer, ConfirmRegistrationSerializer, MessageResponseSerializer, SecurityPinSetupSerializer
from django.db import transaction
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema, inline_serializer
from dating.openapi.response_serializers import CustomErrorResponseSerializer, StatusMessageSerializer, TokenRefreshResponseSerializer, ValidationErrorResponseSerializer, RegisterRequestOTPResponseSerializer, RegisterVerifyOTPResponseSerializer, UserRegisterResponseSerializer, UserRegisterErrorSerializer, UserLoginResponseSerializer, UserLoginValidationErrorSerializer, UserLoginUnauthorizedSerializer, UserLoginErrorSerializer
from rest_framework.generics import GenericAPIView
from pybreaker import CircuitBreakerError as BreakerError
from ..integrations.circuit_breakers import email_breaker

User = get_user_model()
logger = logging.getLogger(__name__)


# =============================================================================
# MOBILE APP AUTHENTICATION VIEWS
# =============================================================================
@extend_schema(
    tags=["Authentication"],
    responses={
        201: RegisterRequestOTPResponseSerializer,
        400: ValidationErrorResponseSerializer,
        500: CustomErrorResponseSerializer,
    },
)
class RegisterRequestOTPView(generics.CreateAPIView):
    serializer_class = RegisterRequestOTPSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()  # calls your serializer's create()
        return Response(result, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Authentication"],
    responses={
        200: RegisterVerifyOTPResponseSerializer,
        400: ValidationErrorResponseSerializer,
        500: CustomErrorResponseSerializer,
    },
)
@method_decorator(
    ratelimit(key="ip", rate="5/m", method="POST", block=False), name="dispatch"
)
class VerifyOTPView(generics.CreateAPIView):
    serializer_class = VerifyOTPSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        if getattr(request, "limited", False):
            return Response(
                {"error": "Too many requests. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data, status=status.HTTP_200_OK)


@extend_schema(
    tags=["Authentication"],
    responses={
        201: UserRegisterResponseSerializer,
        400: ValidationErrorResponseSerializer,
        500: UserRegisterErrorSerializer,
    },
)
class ConfirmRegistrationView(generics.CreateAPIView):
    serializer_class = ConfirmRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()

        user = data["user"]
        tokens = data["tokens"]

        # # Ensure Firestore document exists
        # firebase_uid = getattr(user, "firebase_uid", user.email)
        # ensure_firestore_user_document(firebase_uid, user)

        response_data = {
            "user": {"id": user.id, "email": user.email, "status": user.status, "is_active": user.is_active},
            "tokens": tokens,
        }
        return Response(response_data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Authentication"],
    responses={
        200: RegisterRequestOTPResponseSerializer,
        400: ValidationErrorResponseSerializer,
        500: CustomErrorResponseSerializer,
    },
)
class ResendEmailOTPView(generics.CreateAPIView):
    serializer_class = ResendEmailOTPSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()  # dict returned
        return Response(data, status=200)


@extend_schema(
    tags=["Onboarding Verification"],
    request=VerifyAgeSerializer,
    responses={
        200: MessageResponseSerializer,
        400: ValidationErrorResponseSerializer,
        500: CustomErrorResponseSerializer,
    },
    description="Verify user age during onboarding. Requires a valid, verified registration token. User must be at least 18 years old.",
)
class VerifyAgeView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = VerifyAgeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        user.date_of_birth = serializer.validated_data["date_of_birth"]
        user.is_active = True
        user.save()

        return Response(
            {
                "message": "Updated successfully",
                "user": {"id": user.id, "email": user.email, "status": user.status, "is_active": user.is_active},
            },
            status=status.HTTP_200_OK
        )


# -------------------------
# User Login
# -------------------------
@extend_schema(
    tags=["Authentication"],
    responses={
        200: UserLoginResponseSerializer,
        400: UserLoginValidationErrorSerializer,
        401: UserLoginUnauthorizedSerializer,
        500: UserLoginErrorSerializer,
    },
)
@method_decorator(
    ratelimit(key="ip", rate="5/m", method="POST", block=False), name="dispatch"
)
class UserLoginView(GenericAPIView):
    serializer_class = UserLoginRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        # Check if the request exceeded the rate limit
        if getattr(request, "limited", False):
            return Response(
                {"error": "Too many requests. Please try again in a minute."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # firebase_token = serializer.validated_data.get("firebase_token")
        email = serializer.validated_data.get("email")
        password = serializer.validated_data.get("password")

        try:
            user = None
            deletion_cancelled = False

            # Case 1: Firebase login
            # if firebase_token:
            #     decoded_token = verify_firebase_token(firebase_token)
            #     if decoded_token:
            #         user = get_or_create_user_from_firebase(decoded_token)
            #     else:
            #         # Ignore Firebase failure and fallback to email/password
            #         pass

            # Case 2: Email/password login (fallback or if no Firebase token)
            if not user:
                if not email or not password:
                    return Response(
                        {"message": "Email and password required", "status": "error"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                login_serializer = CustomLoginSerializer(
                    data={"email": email, "password": password}
                )
                login_serializer.is_valid(raise_exception=True)
                user = login_serializer.validated_data["user"]
                deletion_cancelled = login_serializer.validated_data.get("deletion_cancelled", False)

            # Issue JWT tokens
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "message": "Login successful",
                    "status": "success",
                    "deletion_cancelled": deletion_cancelled,
                    "user": UserProfileSerializer(user).data,
                    "tokens": {
                        "access": str(refresh.access_token),
                        "refresh": str(refresh),
                    },
                },
                status=status.HTTP_200_OK,
            )

        except serializers.ValidationError:
            # Wrong email or password is a 400, not a server error
            raise
        except Exception as e:
            return Response(
                {"message": f"Login failed: {str(e)}", "status": "error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# -------------------------
# User Logout
# -------------------------
@extend_schema(
    tags = ['Authentication'],
    request=UserLogoutRequestSerializer,
    responses={
        200: inline_serializer(
            name="LogoutResponse",
            fields={
                "message": serializers.CharField(),
                "status": serializers.CharField(),
            },
        ),
        400: inline_serializer(
            name="ErrorResponse",
            fields={
                "message": serializers.CharField(),
                "status": serializers.CharField(),
            },
        ),
    },
)
@extend_schema(
    tags=["Authentication"],
    )
class UserLogoutView(GenericAPIView):
    serializer_class = UserLogoutRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.validated_data.get("refresh_token")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                user_id = token.get("user_id")
                token.blacklist()
            except Exception:
                return Response(
                    {"message": "Invalid or expired token", "status": "error"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Stop push notifications to this phone; the valid refresh token
            # proves which account is signing out of it
            device_id = request.META.get("HTTP_X_DEVICE_ID")
            if device_id and user_id:
                DeviceRegistration.objects.filter(
                    user_id=user_id, device_id=device_id
                ).update(is_active=False)

        return Response(
            {"message": "Logout successful", "status": "success"},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Authentication"],
    )
@extend_schema(
    request=TokenRefreshRequestSerializer,
    responses={
        200: TokenRefreshResponseSerializer,
        400: TokenRefreshResponseSerializer,
        401: TokenRefreshResponseSerializer,
    },
)
class TokenRefreshView(generics.GenericAPIView):
    serializer_class = TokenRefreshRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.validated_data["refresh_token"]
        from rest_framework_simplejwt.tokens import RefreshToken

        token = RefreshToken(refresh_token)

        return Response(
            {
                "message": "Token refreshed successfully",
                "status": "success",
                "tokens": {"access": str(token.access_token), "refresh": str(token)},
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags = ['Authentication'],
    request=ChangeLoginInfoSerializer,
    responses={
        200: inline_serializer(
            name="ChangeLoginInfoResponse",
            fields={
                "message": serializers.CharField(),
                "status": serializers.CharField(),
                "requires_verification": serializers.BooleanField(),
            },
        ),
        400: inline_serializer(
            name="ChangeLoginInfoErrorResponse",
            fields={
                "message": serializers.CharField(),
                "status": serializers.CharField(),
            },
        ),
    },
)
class ChangeLoginInfoView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangeLoginInfoSerializer

    def post(self, request):
        serializer = self.get_serializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        if user.pending_email:
            PasswordResetOTP.objects.filter(
                email=user.pending_email,
                is_used=False,
                purpose=PasswordResetPurpose.LOGIN_INFO_CHANGE,
            ).delete()

            otp = PasswordResetOTP.generate_otp()
            PasswordResetOTP.objects.create(
                email=user.pending_email,
                otp=otp,
                purpose=PasswordResetPurpose.LOGIN_INFO_CHANGE,
            )

            send_otp_email.delay(
                user.pending_email,
                otp,
                user_name=user.name,
                subject="Confirm your new email address",
            )

            return Response(
                {
                    "message": "Login info updated. A verification code has been sent to your new email.",
                    "status": "success",
                    "requires_verification": True,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "message": "Login info updated successfully.",
                "status": "success",
                "requires_verification": False,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Authentication"],
    request=SecurityPinSetupSerializer,
    responses={
        200: inline_serializer(
            name="SecurityPinSetupResponse",
            fields={
                "message": serializers.CharField(),
                "status": serializers.CharField(),
            },
        ),
        400: inline_serializer(
            name="SecurityPinSetupErrorResponse",
            fields={
                "message": serializers.CharField(),
                "status": serializers.CharField(),
            },
        ),
    },
)
class SecurityPinSetupView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SecurityPinSetupSerializer

    def post(self, request):
        serializer = self.get_serializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "PIN set successfully.", "status": "success"},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=['Authentication'],
    request=TwoStepVerifyOTPSerializer,
    responses={
        200: inline_serializer(
            name="TwoStepVerifyOTPResponse",
            fields={
                "message": serializers.CharField(),
                "status": serializers.CharField(),
                "email": serializers.EmailField(),
            },
        ),
        400: inline_serializer(
            name="TwoStepVerifyOTPErrorResponse",
            fields={
                "message": serializers.CharField(),
                "status": serializers.CharField(),
            },
        ),
    },
)
@method_decorator(
    ratelimit(key="user", rate="5/m", method="POST", block=False), name="dispatch"
)
class TwoStepVerifyOTPView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TwoStepVerifyOTPSerializer

    def post(self, request, *args, **kwargs):
        if getattr(request, "limited", False):
            return Response(
                {"message": "Too many requests. Try again in a minute.", "status": "error"},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        
        user = request.user
        if not user.pending_email:
            return Response(
                {"message": "No pending email change to verify.", "status": "error"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp = serializer.validated_data["otp"]

        otp_record = PasswordResetOTP.objects.filter(
            otp=otp,
            is_used=False,
            email=user.pending_email,
            purpose=PasswordResetPurpose.LOGIN_INFO_CHANGE
        ).first()

        if not otp_record or otp_record.is_expired():
            return Response(
                {"message": "Invalid or expired OTP", "status": "error"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            otp_record.is_used = True
            otp_record.save()

            user.email = user.pending_email
            user.pending_email = None
            user.save()
        
        return Response(
            {
                "message": "Email updated successfully",
                "status": "success",
                "email": user.email,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Authentication"],
    request=None,
    responses={
        200: inline_serializer(
            name="TwoStepResendResponse",
            fields={
                "message": serializers.CharField(),
                "status": serializers.CharField(),
            },
        ),
        400: inline_serializer(
            name="TwoStepResendErrorResponse",
            fields={
                "message": serializers.CharField(),
                "status": serializers.CharField(),
            },
        ),
    },
)
class TwoStepResendOTPView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        if not user.pending_email:
            return Response(
                {"message": "No pending email change to verify.", "status": "error"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        if not PasswordResetOTP.can_resend_for_email(
            user.pending_email,
            PasswordResetPurpose.LOGIN_INFO_CHANGE
        ):
            return Response(
                {"message": "Too many requests. Try again in a minute.", "status": "error"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        PasswordResetOTP.objects.filter(
            email=user.pending_email,
            is_used=False,
            purpose=PasswordResetPurpose.LOGIN_INFO_CHANGE
        ).update(is_used=True)

        otp = PasswordResetOTP.generate_otp()

        PasswordResetOTP.objects.create(
            email=user.pending_email,
            otp=otp,
            purpose=PasswordResetPurpose.LOGIN_INFO_CHANGE
        )

        send_otp_email.delay(
            user.pending_email,
            otp,
            user_name=user.name,
            subject="Confirm your new email address",
        )

        return Response(
            {
                "message": "A new verification code has been sent to your new email.",
                "status": "success",
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags = ['Authentication'],
    request=PasswordResetSerializer,
    responses={
        200: StatusMessageSerializer,
        400: CustomErrorResponseSerializer,
        500: CustomErrorResponseSerializer,
    },
)
class PasswordResetView(generics.GenericAPIView):
    serializer_class = PasswordResetSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        purpose = serializer.validated_data["purpose"]

        # Always respond success (avoid email enumeration)
        response_msg = {
            "message": "If the email exists, OTP has been sent",
            "status": "success",
        }

        user = User.objects.filter(email=email).first()
        if not user:
            return Response(response_msg, status=200)
        
        # Extract device info from request
        ip_address = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() \
            or request.META.get("REMOTE_ADDR", "Unknown")
        user_agent = request.META.get("HTTP_USER_AGENT", "Unknown device")
        reset_time = timezone.now().strftime("%B %d, %Y at %I:%M %p UTC")

        # Delete old OTPs for this email
        PasswordResetOTP.objects.filter(email=email, is_used=False, purpose=purpose).delete()

        # Generate new OTP
        otp = PasswordResetOTP.generate_otp()

        # Store it in DB
        PasswordResetOTP.objects.create(
            email=email,
            otp=otp,
            purpose=purpose,
        )

        try:
            # Send OTP via email
            send_password_reset_email.delay(
                user.email,
                otp,
                user_name=user.name,
                ip_address=ip_address,
                user_agent=user_agent,
                reset_time=reset_time,
            )   
        except Exception as e:
            logger.error(f"Email error: {e}", exc_info=True)
            raise

        return Response(response_msg, status=200)


@extend_schema(
    tags = ['Authentication'],
   request=PasswordResetConfirmSerializer,
     responses={
       200: PasswordResetConfirmSerializer,
        400: PasswordResetConfirmSerializer,
        500: PasswordResetConfirmSerializer,
    },
 )

@method_decorator(
    ratelimit(key="ip", rate="5/m", method="POST", block=False), name="dispatch"
)
class PasswordResetVerifyOTPView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = OTPSerializer

    def post(self, request, *args, **kwargs):
        if getattr(request, "limited", False):
            return Response(
                {"error": "Too many requests. Try again in a minute."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp = serializer.validated_data["otp"]
        email = serializer.validated_data["email"]
        purpose = serializer.validated_data["purpose"]

        otp_record = PasswordResetOTP.objects.filter(
            otp=otp,
            email=email,
            is_used=False,
            purpose=purpose,
        ).first()

        if not otp_record or otp_record.is_expired():
            return Response(
                {"message": "Invalid or expired OTP", "status": "error"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Atomic update to prevent race conditions
        with transaction.atomic():
            otp_record.is_used = True
            otp_record.reset_token = uuid.uuid4()
            otp_record.save()

        return Response(
            {
                "message": "OTP verified successfully",
                "status": "success",
                "reset_token": otp_record.reset_token,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Authentication"],
    responses={
        200: StatusMessageSerializer,
        400: CustomErrorResponseSerializer,
        500: CustomErrorResponseSerializer,
    },
)
class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Password reset successfully", "status": "success"},
            status=status.HTTP_200_OK
        )


@extend_schema(
    tags = ['Authentication'],
    request=PasswordResetResendSerializer,
    responses={
        200: StatusMessageSerializer,
        400: CustomErrorResponseSerializer,
        500: CustomErrorResponseSerializer,
    },
)
class PasswordResendOTPView(generics.GenericAPIView):
    serializer_class = PasswordResetSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        purpose = request.data.get("purpose")

        response_msg = {
            "message": "If the email exists, OTP has been sent",
            "status": "success",
        }

        user = User.objects.filter(email=email).first()
        if not user:
            return Response(response_msg, status=200)

        # Rate limit check
        if not PasswordResetOTP.can_resend_for_email(email, purpose):
            return Response(
                {"message": "Too many requests. Try again in a minute."},
                status=400,
            )

        # Mark previous OTPs as used (do NOT delete — for audit trail)
        PasswordResetOTP.objects.filter(
            email=email, is_used=False, purpose=purpose
        ).update(is_used=True)

        # Generate new OTP
        otp = PasswordResetOTP.generate_otp()

        PasswordResetOTP.objects.create(
            email=email,
            otp=otp,
            purpose=purpose,
        )

        # Send mail
        try:
            email_breaker.call(
                send_mail,
                subject="Your Password Reset OTP",
                message=f"Your OTP is {otp}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
            )
        except BreakerError:
            logger.warning("Email circuit breaker open — password reset email not sent to %s", email)
        except Exception:
            logger.error("Failed to send password reset email to %s", email, exc_info=True)

        return Response(response_msg, status=200)
