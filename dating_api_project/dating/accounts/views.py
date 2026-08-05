import uuid
from logging import getLogger
from datetime import timedelta

from django.utils.decorators import method_decorator
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone
from django.db import transaction
from django.db.models import Q


from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiRequest, OpenApiResponse, extend_schema_view
from django_ratelimit.decorators import ratelimit
from pybreaker import CircuitBreakerError as BreakerError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.generics import (
    GenericAPIView,
    CreateAPIView,
    ListAPIView,
    DestroyAPIView,
    UpdateAPIView,
    RetrieveUpdateAPIView,
    RetrieveAPIView
)

from dating.tasks import send_password_reset_email
from dating.circuit_breakers import email_breaker
from dating.permissions import IsPrincipalAdmin
from dating.utils import get_cached_my_profile, get_cached_static_profile
from dating.location_utils import calculate_match_score, get_location_statistics
from dating.models import (
    PasswordResetOTP,
    DeviceRegistration,
    SocialAccount,
    UserRoleSelection,
    DocumentVerification,
    UserProfileView,
    Activity,
)
from dating.oauth_utils import (
    GoogleOAuthVerifier,
    OAuthUserManager,
    OAuthTokenGenerator,
    AppleOAuthVerifier,
)

from .serializers import (
    UserLoginRequestSerializer,
    CustomLoginSerializer,
    UserLogoutRequestSerializer, 
    TokenRefreshRequestSerializer, 
    PasswordResetSerializer, 
    PasswordResetResendSerializer, 
    PasswordResetConfirmSerializer, 
    OTPSerializer, 
    RegisterRequestOTPSerializer, 
    VerifyOTPSerializer, 
    ConfirmRegistrationSerializer, 
    VerifyAgeSerializer, 
    ResendEmailOTPSerializer, 
    MessageResponseSerializer,

    AdminLoginSerializer,
    AdminLogoutSerializer,
    CreateTeamMemberSerializer,
    UpdateAdminMemberSerializer,
    RemoveAdminMemberSerializer,
    TeamMemberSerializer,

    GoogleOAuthSerializer,
    AppleOAuthSerializer,
    GoogleCallbackSerializer,
    OAuthLoginSerializer,
    DeviceRegistrationSerializer,
    SocialAccountSerializer,

    UserProfileSerializer,
    UserProfileWithSocialSerializer,
    UserProfileDetailSerializer,
    NotificationSettingsSerializer,
    LanguageSettingsSerializer,
    UserRoleSelectionSerializer,
    UserRoleStatusSerializer,
    StaticUserProfileSerializer,
)
from response_serializers import (
    UserLoginResponseSerializer, 
    UserLoginErrorSerializer, 
    UserLoginValidationErrorSerializer, 
    UserLoginUnauthorizedSerializer, 
    TokenRefreshResponseSerializer, 
    CustomErrorResponseSerializer, 
    StatusMessageSerializer, 
    PasswordResetVerifyOTPResponseSerializer, 
    ValidationErrorResponseSerializer, 
    RegisterRequestOTPResponseSerializer, 
    RegisterVerifyOTPResponseSerializer, 
    UserRegisterErrorSerializer, 
    UserRegisterResponseSerializer,

    AdminLoginResponseSerializer,

    OAuthLoginResponseSerializer,
    OAuthLinkAccountRequestSerializer,
    OAuthLinkAccountResponseSerializer,
    OAuthUnlinkAccountResponseSerializer,
    SocialAccountsListResponseSerializer,

    SimpleStatusResponseSerializer,
    NotificationSettingsResponseSerializer,
    NotificationSettingsErrorSerializer,
    LanguageSettingsResponseSerializer,
    LanguageSettingsErrorSerializer,
)

logger = getLogger(__name__)
User = get_user_model()


# =============================================================================
# AUTH AND REGISTRATION VIEWS
# =============================================================================

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
    """User Login Authentication"""

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

        # try:
        user = None

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

        # Issue JWT tokens
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message": "Login successful",
                "status": "success",
                "user": UserProfileSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_200_OK,
        )

        # except Exception as e:
        #     return Response(
        #         {"message": f"Login failed: {str(e)}", "status": "error"},
        #         status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        #     )


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
class UserLogoutView(GenericAPIView):
    """Logout user"""
    serializer_class = UserLogoutRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.validated_data.get("refresh_token")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                raise ValidationError("Invalid or expired token")

        return Response(
            {"message": "Logout successful", "status": "success"},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    request=TokenRefreshRequestSerializer,
    responses={
        200: TokenRefreshResponseSerializer,
        400: TokenRefreshResponseSerializer,
        401: TokenRefreshResponseSerializer,
    },
    tags=["Authentication"],
)
class TokenRefreshView(GenericAPIView):
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
    request=PasswordResetSerializer,
    responses={
        200: StatusMessageSerializer,
        400: CustomErrorResponseSerializer,
        500: CustomErrorResponseSerializer,
    },
)
class PasswordResetView(GenericAPIView):
    serializer_class = PasswordResetSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

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
        PasswordResetOTP.objects.filter(email=email, is_used=False).delete()

        # Generate new OTP
        otp = PasswordResetOTP.generate_otp()

        # Store it in DB
        PasswordResetOTP.objects.create(
            email=email,
            otp=otp,
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
    request=PasswordResetResendSerializer,
    responses={
        200: StatusMessageSerializer,
        400: CustomErrorResponseSerializer,
        500: CustomErrorResponseSerializer,
    },
)
class PasswordResendOTPView(GenericAPIView):
    serializer_class = PasswordResetSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")

        response_msg = {
            "message": "If the email exists, OTP has been sent",
            "status": "success",
        }

        user = User.objects.filter(email=email).first()
        if not user:
            return Response(response_msg, status=200)

        # Rate limit check
        if not PasswordResetOTP.can_resend_for_email(email):
            return Response(
                {"message": "Too many requests. Try again in a minute."},
                status=400,
            )

        # Mark previous OTPs as used (do NOT delete — for audit trail)
        PasswordResetOTP.objects.filter(
            email=email, is_used=False
        ).update(is_used=True)

        # Generate new OTP
        otp = PasswordResetOTP.generate_otp()

        PasswordResetOTP.objects.create(
            email=email,
            otp=otp,
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


@extend_schema(
    tags=["Authentication"],
    responses={
        200: StatusMessageSerializer,
        400: CustomErrorResponseSerializer,
        500: CustomErrorResponseSerializer,
    },
)
class PasswordResetConfirmView(GenericAPIView):
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
    request=OTPSerializer,
    responses={
        200: PasswordResetVerifyOTPResponseSerializer,
        400: CustomErrorResponseSerializer,
        500: CustomErrorResponseSerializer,
    },
)
@method_decorator(
    ratelimit(key="ip", rate="5/m", method="POST", block=False), name="dispatch"
)
class PasswordResetVerifyOTPView(GenericAPIView):
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

        otp_record = PasswordResetOTP.objects.filter(
            otp=otp,
            email=email,
            is_used=False,
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
        201: RegisterRequestOTPResponseSerializer,
        400: ValidationErrorResponseSerializer,
        500: CustomErrorResponseSerializer,
    },
)
class RegisterRequestOTPView(CreateAPIView):
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
class VerifyOTPView(CreateAPIView):
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
class ConfirmRegistrationView(CreateAPIView):
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
class ResendEmailOTPView(CreateAPIView):
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


# =============================================================================
# ADMIN ACCOUNT MANAGEMENT VIEWS
# =============================================================================

@extend_schema(
    tags=["Admin"],
    responses=AdminLoginResponseSerializer
)
class AdminLoginView(APIView):
    permission_classes = [AllowAny]
    @extend_schema(
        request=AdminLoginSerializer,
        responses=AdminLoginResponseSerializer
    )
    def post(self, request):

        serializer = AdminLoginSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        user.last_used = timezone.now()
        user.save()

        refresh = RefreshToken.for_user(user)

        return Response({

            "access": str(refresh.access_token),

            "refresh": str(refresh),

            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role.name if user.role else None,
            }

        }, status=status.HTTP_200_OK)


class AdminLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Admin"],
        request=AdminLogoutSerializer,
        responses=MessageResponseSerializer
    )
    def post(self, request):

        serializer = AdminLogoutSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(
            {"message": "Logged out successfully"},
            status=status.HTTP_200_OK
        )


@extend_schema(
    tags=["Admin"],
    responses={
        201: OpenApiResponse(description="Admin Created"),
        403: OpenApiResponse(description="User is not Principal Admin")
    }
    )
class CreateAdminMemberView(CreateAPIView):
    serializer_class = CreateTeamMemberSerializer
    permission_classes = [IsPrincipalAdmin]


@extend_schema(
    tags=["Admin"],
    responses={
        200: UpdateAdminMemberSerializer,
        403: OpenApiResponse(description="User is not a Principal Admin")
    }
    )
class UpdateAdminMemberView(UpdateAPIView):
    queryset = User.objects.filter(is_staff=True)
    serializer_class = UpdateAdminMemberSerializer
    permission_classes = [IsPrincipalAdmin]


@extend_schema(
    tags=["Admin"],
    responses={
        204: OpenApiResponse(description="Member successfully removed"),
        403: OpenApiResponse(description="User is not a Principal Admin")
    }
    )
class RemoveAdminMemberView(DestroyAPIView):
    serializer_class = RemoveAdminMemberSerializer
    queryset = User.objects.filter(is_staff=True)
    permission_classes = [IsPrincipalAdmin]


@extend_schema(
    tags=["Admin"],
    )
class AdminTeamView(ListAPIView):
    serializer_class = TeamMemberSerializer
    permission_classes = [IsPrincipalAdmin]

    def get_queryset(self):
        """
        Returns team members created by the principal admin.
        Supports:
            - Search by name, ID, wallet
            - Filter by role
            - Filter by status
        """
        qs = User.objects.filter(is_staff=True).select_related("role")

        # ----- Search -----
        search_query = self.request.query_params.get("search", None)
        if search_query:
            filters = (
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(id__icontains=search_query)
            )
            if search_query.isdigit():
                filters |= Q(id=int(search_query))
            qs = qs.filter(filters)

        # ----- Filter by role -----
        role_filter = self.request.query_params.get("role", None)
        if role_filter and role_filter.lower() != "all":
            qs = qs.filter(role__name__iexact=role_filter)

        # ----- Filter by status -----
        status_filter = self.request.query_params.get("status", None)
        if status_filter and status_filter.lower() != "all":
            qs = qs.filter(status__iexact=status_filter)

        return qs.order_by("-date_joined")  # newest first


# =============================================================================
# OAUTH AND SOCIAL ACCOUNTS VIEWS
# =============================================================================

@extend_schema(tags=["Authentication"])
@method_decorator(
    ratelimit(key="ip", rate="5/m", method="POST", block=False), name="dispatch"
)
class GoogleOAuthView(GenericAPIView):
    """Google OAuth login for mobile app"""

    permission_classes = [AllowAny]
    serializer_class = GoogleOAuthSerializer

    @extend_schema(
        request=GoogleOAuthSerializer,
        responses=OAuthLoginResponseSerializer,
        description="Login or register user using Google OAuth access token.",
    )
    def post(self, request):
        if getattr(request, "limited", False):
            return Response(
                {"error": "Too many requests. Please try again in a minute."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        id_token = serializer.validated_data["id_token"]

        try:
            
            # Wrap token creation and user creation in a transaction
            with transaction.atomic():
                oauth_data, error = GoogleOAuthVerifier.verify_id_token(id_token)

                if error:
                    return Response(
                        {
                            "message": f"Google OAuth verification failed: {error}",
                            "status": "error",
                        },
                        status=400,
                    )

                user, error = OAuthUserManager.get_or_create_user_from_oauth(
                    oauth_data, "google"
                )

                if error:
                    return Response(
                        {"message": f"User creation failed: {error}", "status": "error"},
                        status=400,
                    )

                tokens, error = OAuthTokenGenerator.generate_tokens(user)

                if error:
                    return Response(
                        {"message": f"Token generation failed: {error}", "status": "error"},
                        status=500,
                    )

            return Response(
                {
                    "message": "Google login successful",
                    "status": "success",
                    "user": UserProfileWithSocialSerializer(user).data,
                    "tokens": tokens,
                },
                status=200,
            )

        except Exception as e:
            return Response(
                {"message": f"Google login failed: {str(e)}", "status": "error"},
                status=500,
            )

@extend_schema(
    tags=["Authentication"],
    # tags=["OAuth"],
    )
@method_decorator(
    ratelimit(key="ip", rate="5/m", method="POST", block=False), name="dispatch"
)
class AppleOAuthView(GenericAPIView):
    """Apple Sign-In for mobile app"""

    permission_classes = [AllowAny]
    serializer_class = AppleOAuthSerializer

    @extend_schema(
        request=AppleOAuthSerializer,
        responses=OAuthLoginResponseSerializer,
        description="Login or register user using Apple identity token.",
    )
    def post(self, request):

        if getattr(request, "limited", False):
            return Response(
                {"error": "Too many requests. Please try again in a minute."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        identity_token = serializer.validated_data["identity_token"]

        try:
            

            # Wrap verification, user creation, and token generation in a transaction
            with transaction.atomic():
                oauth_data, error = AppleOAuthVerifier.verify_identity_token(identity_token)

                if error:
                    return Response(
                        {
                            "message": f"Apple OAuth verification failed: {error}",
                            "status": "error",
                        },
                        status=400,
                    )

                user, error = OAuthUserManager.get_or_create_user_from_oauth(
                    oauth_data, "apple"
                )

                if error:
                    return Response(
                        {"message": f"User creation failed: {error}", "status": "error"},
                        status=400,
                    )

                tokens, error = OAuthTokenGenerator.generate_tokens(user)

                if error:
                    return Response(
                        {"message": f"Token generation failed: {error}", "status": "error"},
                        status=500,
                    )

            return Response(
                {
                    "message": "Apple login successful",
                    "status": "success",
                    "user": UserProfileWithSocialSerializer(user).data,
                    "tokens": tokens,
                },
                status=200,
            )

        except Exception as e:
            return Response(
                {"message": f"Apple login failed: {str(e)}", "status": "error"},
                status=500,
            )

@extend_schema(
    tags=["Authentication"],
    )
class GoogleOAuthCallbackView(GenericAPIView):
    serializer_class = GoogleCallbackSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        # Extract only the 'code' from the URL
        code = request.GET.get("code")
        if not code:
            return Response({"error": "No code provided"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data={"code": code})
        serializer.is_valid(raise_exception=True)

        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": serializer.validated_data["code"],
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI"),
            "grant_type": "authorization_code",
        }

        try:
            response = requests.post(token_url, data=data, timeout=10)
            response.raise_for_status()
            token_data = response.json()
        except requests.RequestException as e:
            return Response(
                {"error": "Failed to exchange code for token", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(token_data, status=status.HTTP_200_OK)


@extend_schema(tags=["Authentication"])
class SocialLoginView(GenericAPIView):
    """Unified social login endpoint (Google/Apple)"""

    permission_classes = [AllowAny]
    serializer_class = OAuthLoginSerializer

    @extend_schema(
        request=OAuthLoginSerializer,
        responses=OAuthLoginResponseSerializer,
        description="Login or register user using Google or Apple OAuth.",
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider = serializer.validated_data["provider"]

        try:
            if provider == "google":
                access_token = serializer.validated_data["google_data"]["access_token"]

            
                oauth_data, error = GoogleOAuthVerifier.verify_access_token(
                    access_token
                )

            else:
                identity_token = serializer.validated_data["apple_data"][
                    "identity_token"
                ]

                oauth_data, error = AppleOAuthVerifier.verify_identity_token(
                    identity_token
                )

            if error:
                return Response(
                    {
                        "message": f"{provider.title()} OAuth verification failed: {error}",
                        "status": "error",
                    },
                    status=400,
                )

            user, error = OAuthUserManager.get_or_create_user_from_oauth(
                oauth_data, provider
            )

            if error:
                return Response(
                    {"message": f"User creation failed: {error}", "status": "error"},
                    status=400,
                )

            tokens, error = OAuthTokenGenerator.generate_tokens(user)

            if error:
                return Response(
                    {"message": f"Token generation failed: {error}", "status": "error"},
                    status=500,
                )

            return Response(
                {
                    "message": f"{provider.title()} login successful",
                    "status": "success",
                    "user": UserProfileWithSocialSerializer(user).data,
                    "tokens": tokens,
                },
                status=200,
            )

        except Exception as e:
            return Response(
                {"message": f"Social login failed: {str(e)}", "status": "error"},
                status=500,
            )

@extend_schema(
    tags=["Authentication"],
    responses={
        401: OpenApiResponse(description="User Not Authenticated")
    }
)

class DeviceRegistrationView(CreateAPIView):
    serializer_class = DeviceRegistrationSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)

        active_tokens = DeviceRegistration.objects.filter(
            user=request.user, is_active=True
        ).count()

        return Response({
            "message": "Device registered successfully",
            "status": "success",
            "data": response.data,
            "active_tokens": active_tokens,
        })


class OAuthLinkAccountView(GenericAPIView):
    """Link social account to existing user"""

    permission_classes = [IsAuthenticated]
    serializer_class = OAuthLinkAccountRequestSerializer

    @extend_schema(
        tags = ['Authentication'],
        responses={
            200: OAuthLinkAccountResponseSerializer,
            400: ValidationErrorResponseSerializer,
            500: CustomErrorResponseSerializer,
        },
        description="Link a Google or Apple account to the currently authenticated user.",
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider = serializer.validated_data["provider"]

        try:
          
            if provider == "google":
                oauth_data, error = GoogleOAuthVerifier.verify_access_token(
                    serializer.validated_data["access_token"]
                )
            else:
                oauth_data, error = AppleOAuthVerifier.verify_identity_token(
                    serializer.validated_data["identity_token"]
                )

            if error:
                return Response(
                    {
                        "message": f"OAuth verification failed: {error}",
                        "status": "error",
                    },
                    status=400,
                )

            social_account, error = OAuthUserManager.link_social_account(
                request.user, oauth_data, provider
            )

            if error:
                return Response(
                    {"message": f"Account linking failed: {error}", "status": "error"},
                    status=400,
                )

            return Response(
                {
                    "message": f"{provider.title()} account linked successfully",
                    "status": "success",
                    "social_account": SocialAccountSerializer(social_account).data,
                },
                status=200,
            )

        except Exception as e:
            return Response(
                {"message": f"Account linking failed: {str(e)}", "status": "error"},
                status=500,
            )


class OAuthUnlinkAccountView(GenericAPIView):
    """Unlink social account from user"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
            tags = ['Authentication'],
        responses={
            200: OAuthUnlinkAccountResponseSerializer,
            404: CustomErrorResponseSerializer,
            500: CustomErrorResponseSerializer,
        },
        description="Unlink a social provider from the current user.",
    )
    def delete(self, request, provider):
        try:
            social_account = SocialAccount.objects.get(
                user=request.user, provider=provider, is_active=True
            )

            social_account.is_active = False
            social_account.save()

            return Response(
                {
                    "message": f"{provider.title()} account unlinked successfully",
                    "status": "success",
                },
                status=200,
            )

        except SocialAccount.DoesNotExist:
            return Response(
                {"message": f"No active {provider} account found", "status": "error"},
                status=404,
            )
        except Exception as e:
            return Response(
                {"message": f"Account unlinking failed: {str(e)}", "status": "error"},
                status=500,
            )

@extend_schema(
    tags=["Authentication"],
    )
class SocialAccountsListView(ListAPIView):
    """List user's linked social accounts"""

    permission_classes = [IsAuthenticated]
    serializer_class = SocialAccountSerializer

    def get_queryset(self):
        return SocialAccount.objects.filter(user=self.request.user, is_active=True)

    @extend_schema(
        responses={200: SocialAccountsListResponseSerializer},
        description="List all active social accounts linked to the current user.",
    )
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)

        return Response(
            {
                "message": "Social accounts retrieved successfully",
                "status": "success",
                "social_accounts": response.data,
            }
        )


# =============================================================================
# PROFILE AND SETTINGS
# =============================================================================


@extend_schema(
    tags=["Profile"],
    )
class UserProfileViews(RetrieveUpdateAPIView):
    serializer_class = UserProfileDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    # ---------------- RETRIEVE ----------------
    def retrieve(self, request, *args, **kwargs):
        try:
            user = self.get_object()

            # 1 Cached profile
            profile_data = get_cached_my_profile(user, request=request)

            # 2 Firestore merge (live)
            # firebase_uid = getattr(user, "firebase_uid", user.email)
            # firestore_profile = get_user_profile_from_firestore(firebase_uid)

            # if firestore_profile:
            #     profile_data = {**profile_data, **firestore_profile}

            return Response(
                {
                    "message": "Profile retrieved successfully",
                    "status": "success",
                    "user": profile_data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {
                    "message": f"Failed to retrieve profile: {str(e)}",
                    "status": "error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ---------------- UPDATE ----------------
    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop("partial", False)
            instance = self.get_object()

            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            updated_user = serializer.save()

            # Check if user is under 18 and flag them

            if updated_user.date_of_birth and updated_user.age < 18:
                updated_user.is_flagged_for_deletion = True
                updated_user.scheduled_deletion_at = timezone.now() + timedelta(hours=24)
                updated_user.save(update_fields=["is_flagged_for_deletion", "scheduled_deletion_at"])

            # CLEAR BOTH CACHES AFTER SAVE
            cache.delete(f"my_profile:{instance.id}")
            cache.delete(f"user_static_profile:{instance.id}")

            # 2 Update Firestore if needed
            # from .firebase_utils import update_user_profile_in_firestore

            # firestore_data = {}
            # firestore_fields = ["bio", "interests", "photos"]

            # for field in firestore_fields:
            #     if field in request.data:
            #         firestore_data[field] = request.data[field]

            # if firestore_data:
            #     firebase_uid = getattr(instance, "firebase_uid", instance.email)
            #     update_user_profile_in_firestore(firebase_uid, firestore_data)

            return Response(
                {
                    "message": "Profile updated successfully",
                    "status": "success",
                    "user": UserProfileDetailSerializer(updated_user).data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {
                    "message": f"Failed to update profile: {str(e)}",
                    "status": "error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



@extend_schema(
    tags = ['Authentication'],
    request=None,
    responses={
        200: SimpleStatusResponseSerializer,
        500: CustomErrorResponseSerializer,
    },
    description="Deactivate the authenticated user's account",
)
class AccountDeactivationView(GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            user.is_active = False
            user.save(update_fields=["is_active"])

            return Response(
                {
                    "message": "Account deactivated successfully",
                    "status": "success",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {
                    "message": f"Failed to deactivate account: {str(e)}",
                    "status": "error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



@extend_schema(tags=["Notification"])
@extend_schema_view(
    get=extend_schema(
        responses={
            200: NotificationSettingsResponseSerializer,
            500: CustomErrorResponseSerializer
        },
        description="Get current notification settings",
    ),

    put=extend_schema(
        request=NotificationSettingsSerializer,
        responses={
            200: NotificationSettingsResponseSerializer,
            400: NotificationSettingsErrorSerializer,
            500: CustomErrorResponseSerializer,
        },
        description="Update notification settings",
    )
)
class NotificationSettingsView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = NotificationSettingsSerializer

    def get(self, request):
        try:
            user = request.user
            serializer = self.get_serializer(user)

            return Response(
                {
                    "message": "Notification settings retrieved successfully",
                    "status": "success",
                    "settings": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {
                    "message": f"Failed to retrieve notification settings: {str(e)}",
                    "status": "error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def put(self, request):
        try:
            user = request.user
            serializer = self.get_serializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(
                {
                    "message": "Notification settings updated successfully",
                    "status": "success",
                    "settings": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except serializers.ValidationError as e:
            return Response(
                {
                    "message": "Failed to update notification settings",
                    "status": "error",
                    "errors": e.detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {
                    "message": f"Failed to update notification settings: {str(e)}",
                    "status": "error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



@extend_schema(tags=["Language"])
@extend_schema_view(
    get=extend_schema(
        responses={
            200: LanguageSettingsResponseSerializer,
            500: CustomErrorResponseSerializer,
        },
        description="Get current language settings",
    ),
    put=extend_schema(
        request=LanguageSettingsSerializer,
        responses={
            200: LanguageSettingsResponseSerializer,
            400: LanguageSettingsErrorSerializer,
            500: CustomErrorResponseSerializer,
        },
        description="Update language settings",
    ),
)

class LanguageSettingsView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LanguageSettingsSerializer


@extend_schema(
    tags=["Profile"],
    )
class UserRoleSelectionView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserRoleSelectionSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        selected_role = serializer.validated_data["selected_role"]

        role_selection, _ = UserRoleSelection.objects.update_or_create(
            user=request.user,
            defaults={"selected_role": selected_role},
        )

        # TODO: IF USER CHOOSE BONDMAKER, HE OUGHT TO UNDERGO SERIES OF VERIFICATION STEPS
        # If user chose bondmaker, create or reuse pending verification
        # if selected_role == "bondmaker":
        #     DocumentVerification.objects.get_or_create(
        #         user=request.user,
        #         status="pending",
        #         defaults={"document_type": "passport"},
        #     )

        return Response(
            {
                "message": "Role selection saved",
                "status": "success",
                "selected_role": selected_role,
                "is_matchmaker": request.user.is_matchmaker,  # still False
            }
        )


@extend_schema(
    tags=["Profile"],
    )
class UserRoleStatusView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserRoleStatusSerializer

    def get(self, request):
        user = request.user

        # Role selection
        role_selection = UserRoleSelection.objects.filter(user=user).first()
        selected_role = (
            role_selection.selected_role if role_selection else "looking_for_love"
        )

        # Latest verification (if any)
        verification = (
            DocumentVerification.objects.filter(user=user)
            .order_by("-uploaded_at")
            .first()
        )
        verification_status = verification.status if verification else None

        data = {
            "selected_role": selected_role,
            "is_matchmaker": user.is_matchmaker,
            "verification_status": verification_status,
        }

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)


@extend_schema(
    tags=["Profile"],
    )
class UserProfileDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StaticUserProfileSerializer

    def retrieve(self, request, *args, **kwargs):
        user_id = kwargs.get("user_id")
        viewed_user = User.objects.get(id=user_id)

        # 1 Get cached static profile
        data = get_cached_static_profile(user_id)

        # 2 Inject dynamic fields
        data["profile_views_count"] = UserProfileView.objects.filter(
            viewed_user=viewed_user
        ).count()

        data[
            "is_online"
        ] = viewed_user.last_seen and viewed_user.last_seen >= timezone.now() - timedelta(
            minutes=3
        )

        if request.user.has_location and viewed_user.has_location:
            data["distance"] = request.user.get_distance_to(viewed_user)
        else:
            data["distance"] = None

        if request.user != viewed_user:
            data["compatibility_score"] = calculate_match_score(
                request.user, viewed_user
            )
        else:
            data["compatibility_score"] = None

        # 3 Track profile view
        UserProfileView.objects.get_or_create(
            viewer=request.user,
            viewed_user=viewed_user,
            defaults={"source": "direct"},
        )
        # After tracking profile view, add to activity log
        Activity.objects.create(
            actor=request.user,
            action="profile_viewed",
            recipient=viewed_user,
            metadata={
                "viewed_user_id": viewed_user.id,
                "viewed_username": viewed_user.name,
                "viewer_user_id": request.user.id,
                "viewer_username": request.user.name,
            },
        )

        return Response(data)

