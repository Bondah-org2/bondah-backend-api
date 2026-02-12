from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum
from rest_framework import status
from rest_framework import generics
from decimal import Decimal
import time
import random
import string
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.hashers import make_password, check_password
import json
from django.core.files.storage import default_storage
from django.conf import settings
import os
from django.shortcuts import get_object_or_404
import uuid
from django.core.files.base import ContentFile
from rest_framework import serializers
from .pagination import (
    BondmakerPagination,
    BondmakerPublicPagination,
    PendingRequestListPagination,
)
from django.core.exceptions import ValidationError
from .location_utils import update_user_location, geocode_address
from django.db.models import F
from django.db.models.functions import ACos, Cos, Sin, Radians
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

# from .location_utils import find_nearby_users, get_location_statistics
from .models import (
    NewsletterSubscriber,
    PuzzleVerification,
    CoinTransaction,
    Waitlist,
    EmailLog,
    Job,
    JobApplication,
    AdminUser,
    AdminOTP,
    TranslationLog,
    SocialAccount,
    DeviceRegistration,
    LocationHistory,
    UserMatch,
    LocationPermission,
    EmailVerification,
    PhoneVerification,
    UserRoleSelection,
    PaymentWebhook,
    PaymentTransaction,
    PaymentTransaction,
    PaymentMethod,
    UserSubscription,
    BondcoinPackage,
    WalletTransaction,
    LiveSession,
    LiveGift,
    SubscriptionPlan,
    DocumentVerification,
    UserSecurityQuestion,
    UserSocialHandle,
    Post,
    FeedSearch,
    Message,
    Chat,
    Call,
    UserInterest,
    RecommendationEngine,
    UserInteraction,
    SearchQuery,
    UserVerificationStatus,
    PostComment,
    LiveParticipant,
    BondmakerSubscription,
    SuggestedMatch,
    Visibility,
    RevenueRecord,
    MatchRequest,
    MatchRevenueSplit,
    VirtualGift,
    PasswordResetOTP,
    Story,
    StoryReaction,
    StoryView,
    PostComment,
    CommentInteraction,
    Post,
    PostInteraction,
    Notification,
    Report,
)
from deep_translator import GoogleTranslator
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.conf import settings
import logging
from .serializers import (
    UserSerializer,
    LanguageSettingsSerializer,
    NewsletterSubscriberSerializer,
    PuzzleVerificationSerializer,
    CoinTransactionSerializer,
    WaitlistSerializer,
    NewsletterWelcomeEmailSerializer,
    WaitlistConfirmationEmailSerializer,
    GenericEmailSerializer,
    # JobListSerializer,
    # JobDetailSerializer,
    # JobApplicationSerializer,
    AdminLoginSerializer,
    AdminOTPVerificationSerializer,
    AdminJobCreateSerializer,
    AdminJobUpdateSerializer,
    AdminJobListSerializer,
    AdminJobApplicationSerializer,
    TranslationRequestSerializer,
    TranslationResponseSerializer,
    SupportedLanguagesSerializer,
    # Mobile App Authentication Serializers
    CustomRegisterSerializer,
    CustomLoginSerializer,
    PasswordResetSerializer,
    PasswordResetConfirmSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    UserProfileDetailSerializer,
    SocialLoginSerializer,
    DeviceRegistrationSerializer,
    NotificationSettingsSerializer,
    # OAuth Serializers
    GoogleOAuthSerializer,
    AppleOAuthSerializer,
    OAuthLoginSerializer,
    SocialAccountSerializer,
    UserProfileWithSocialSerializer,
    OAuthLinkSerializer,
    # Location Serializers
    LocationUpdateSerializer,
    AddressGeocodeSerializer,
    LocationPrivacyUpdateSerializer,
    LocationPermissionSerializer,
    LocationHistorySerializer,
    UserMatchSerializer,
    UserProfileWithLocationSerializer,
    NearbyUserSerializer,
    MatchPreferencesSerializer,
    UsernameValidationSerializer,
    PaymentWebhookCreateSerializer,
    PaymentTransactionSerializer,
    PaymentTransactionCreateSerializer,
    GiftTransactionCreateSerializer,
    WalletTransactionSerializer,
    WalletSerializer,
    UserSubscriptionSerializer,
    UserSubscriptionCreateSerializer,
    SubscriptionPlanSerializer,
    UsernameUpdateSerializer,
    DocumentVerificationCreateSerializer,
    DocumentVerificationSerializer,
    LiveParticipantSerializer,
    UserSecurityQuestionSerializer,
    UserSecurityQuestionSerializer,
    UserSecurityQuestionCreateSerializer,
    UserSocialHandleSerializer,
    UserSocialHandleCreateSerializer,
    ChatDetailSerializer,
    ChatSerializer,
    ChatCreateSerializer,
    CallInitiateSerializer,
    CallSerializer,
    PostSerializer,
    StorySerializer,
    UserInterestSerializer,
    RecommendationSerializer,
    UserInteractionSerializer,
    PostInteractionSerializer,
    CommentInteractionSerializer,
    StoryReactionSerializer,
    AdminJobApplicationDetailSerializer,
    FeedSuggestionsResponseSerializer,
    TranslationRequestSerializer,
    TranslationResponseSerializer,
    GenericEmailSerializer,
    NewsletterWelcomeEmailSerializer,
    WaitlistConfirmationEmailSerializer,
    TranslationStatsResponseSerializer,
    AdminUpdateApplicationStatusSerializer,
    WaitlistEntrySerializer,
    AdminLogoutSerializer,
    AdminTokenRefreshSerializer,
    UserLogoutRequestSerializer,
    UserLoginRequestSerializer,
    TokenRefreshRequestSerializer,
    UserRoleSelectionSerializer,
    ResendOTPSerializer,
    UserSearchSerializer,
    UserSearchFilterSerializer,
    MessageSerializer,
    ChatSettingsSerializer,
    MessageCreateSerializer,
    PostCreateSerializer,
    PostCommentSerializer,
    LiveGiftSerializer,
    PaymentWebhookSerializer,
    FirebaseMatchSerializer,
    PushNotificationSerializer,
    UserRoleStatusSerializer,
    BondmakerListSerializer,
    PublicBondmakerProfileSerializer,
    BondmakerSubscriptionSerializer,
    BondmakerSuggestionSerializer,
    SubscribeBondmakerSerializer,
    VisibilitySerializer,
    LocationStatisticsSerializer,
    MatchRequestSerializer,
    PurchaseSerializer,
    SendGiftSerializer,
    ConvertGiftSerializer,
    BondcoinPackageSerializer,
    BondmakerMatchActionSerializer,
    BondmakerMatchActionResponseSerializer,
    VirtualGiftSerializer,
    RegisterRequestOTPSerializer,
    VerifyOTPAndRegisterSerializer,
    ResendEmailOTPSerializer,
    StoryCreateSerializer,
    PostShareSerializer,
    LiveSessionSerializer,
    PasswordResetResendSerializer,
    UserSwipeCardSerializer,
    PendingMatchUserSerializer,
    OTPSerializer,
)
from .firebase_utils import (
    verify_firebase_token,
    get_or_create_user_from_firebase,
    get_user_profile_from_firestore,
    update_user_profile_in_firestore,
    create_match_in_firestore,
    send_push_notification,
    get_matches_for_user,
)
from rest_framework import permissions
from django.db.models import Count, Avg
from .location_utils import (
    calculate_match_score,
    get_location_statistics,
    is_user_visible_to,
    calculate_distance,
)
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse

from .schema import (
    authentication_required_schema,
    paginated_list_schema,
    BondahSchemaMixin,
)
from .services.match_service import charge_match_request, reject_match_request
from .services.payment_service import process_apple_purchase, process_google_purchase
from .services.gift_service import send_gift, convert_gift_to_coins
from .services.wallet_service import credit_wallet
from .services.match_service import charge_match_request, accept_match_request
from django.db import transaction
from deep_translator import GoogleTranslator
from django.db import models
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.db.models import Q
from .jwt_utils import generate_tokens, refresh_access_token, revoke_refresh_token
from .permissions import AdminJWTPermission
from response_serializers import (
    ErrorWithDetailsSerializer,
    SimpleStatusResponseSerializer,
    CustomErrorResponseSerializer,
    StatusMessageSerializer,
    CoinTransactionSerializer,
    AdminLoginOTPResponseSerializer,
    AdminLoginSuccessResponseSerializer,
    SupportedLanguagesResponseSerializer,
    TokenRefreshResponseSerializer,
    NotificationSettingsErrorSerializer,
    LanguageSettingsResponseSerializer,
    LanguageSettingsErrorSerializer,
    ValidationErrorResponseSerializer,
    DeviceRegistrationRequestSerializer,
    DeviceRegistrationResponseSerializer,
    OAuthLinkAccountResponseSerializer,
    OAuthLinkAccountRequestSerializer,
    OAuthUnlinkAccountResponseSerializer,
    SocialAccountsListResponseSerializer,
    OAuthLoginResponseSerializer,
    UserRegisterResponseSerializer,
    UserLoginErrorSerializer,
    UserLoginResponseSerializer,
    UserLoginUnauthorizedSerializer,
    UserLoginValidationErrorSerializer,
    UserProfileWithSocialSerializer,
    UserRegisterErrorSerializer,
    NotificationSettingsResponseSerializer,
)
from schema_serializers import (
    GetPuzzleRequestSerializer,
    GetPuzzleResponseSerializer,
    SubmitPuzzleAnswerRequestSerializer,
    SubmitPuzzleAnswerResponseSerializer,
    SpendCoinsRequestSerializer,
    EarnCoinsRequestSerializer,
)
from .coin_utils import has_solved_puzzle
from rest_framework.generics import GenericAPIView

User = get_user_model()
logger = logging.getLogger(__name__)


# class UserCreateView(generics.CreateAPIView):
#     queryset = User.objects.all()
#     serializer_class = CustomRegisterSerializer

#     def create(self, request, *args, **kwargs):
#         try:
#             return super().create(request, *args, **kwargs)
#         except Exception as e:
#             return Response(
#                 {"message": f"User creation failed: {str(e)}", "status": "error"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )


class NewsletterSignupView(generics.CreateAPIView):
    queryset = NewsletterSubscriber.objects.all()
    serializer_class = NewsletterSubscriberSerializer

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                # Check if email already exists
                email = serializer.validated_data.get("email")
                name = serializer.validated_data.get("name", "")

                if NewsletterSubscriber.objects.filter(email=email).exists():
                    return Response(
                        {
                            "message": "Email already subscribed to newsletter",
                            "status": "error",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Save the newsletter subscription
                subscriber = serializer.save()

                # Send automatic welcome email
                subject = f"Welcome to Bondah Dating{f', {name}' if name else ''}! 🎉"
                message = f"""
Hi {name if name else 'there'},

Thank you for subscribing to our newsletter!

We're excited to keep you updated on:
• Latest dating tips and advice
• Success stories from our community
• New features and updates
• Exclusive matchmaking opportunities
• Early access to premium features

Stay tuned for amazing content coming your way!

Best regards,
The Bondah Team

P.S. Follow us on social media for daily dating insights!
                """.strip()

                # Log email attempt
                email_log = EmailLog.objects.create(
                    email_type="newsletter_welcome",
                    recipient_email=email,
                    subject=subject,
                    message=message,
                )

                try:
                    # Send email using Django's email functionality
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=False,
                    )

                    email_log.is_sent = True
                    email_log.save()

                except Exception as e:
                    email_log.is_sent = False
                    email_log.error_message = str(e)
                    email_log.save()
                    # Don't fail the signup if email fails

                # Return success response
                return Response(
                    {
                        "message": "Subscription successful! Welcome email sent.",
                        "status": "success",
                    },
                    status=status.HTTP_201_CREATED,
                )

            return Response(
                {
                    "message": "Invalid data provided",
                    "status": "error",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return Response(
                {"message": f"Server error: {str(e)}", "status": "error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class JoinWaitlistView(generics.CreateAPIView):
    """Join the waitlist"""

    serializer_class = WaitlistSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        data = request.data
        logger.info("📋 Received data: %s", data)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        if Waitlist.objects.filter(email=email).exists():
            logger.info("Email already exists: %s", email)
            return Response(
                {
                    "message": "Email already registered on waitlist",
                    "status": "success",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        # Determine timestamp field dynamically
        timestamp_field = (
            "date_joined" if hasattr(Waitlist, "date_joined") else "joined_at"
        )
        waitlist_data = {
            "email": email,
            "first_name": serializer.validated_data.get("first_name", ""),
            "last_name": serializer.validated_data.get("last_name", ""),
            timestamp_field: timezone.now(),
        }

        saved_entry = Waitlist.objects.create(**waitlist_data)
        logger.info("Saved waitlist entry: %s", saved_entry)

        return Response(
            {
                "message": "Successfully joined the waitlist!",
                "status": "success",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class GetPuzzleView(APIView):
    @extend_schema(
        request=GetPuzzleRequestSerializer,
        responses={
            201: GetPuzzleResponseSerializer,
            400: ErrorWithDetailsSerializer,
            404: ErrorWithDetailsSerializer,
            500: ErrorWithDetailsSerializer,
        },
    )
    def post(self, request):
        serializer = GetPuzzleRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data["user_id"]

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"status": "error", "message": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        question, answer = PuzzleVerification.generate_puzzle()

        puzzle = PuzzleVerification.objects.create(
            user=user, question=question, answer=answer
        )

        return Response(
            {"puzzle_id": puzzle.id, "question": puzzle.question},
            status=status.HTTP_201_CREATED,
        )


class SubmitPuzzleAnswerView(APIView):
    @extend_schema(
        request=SubmitPuzzleAnswerRequestSerializer,
        responses={
            200: SubmitPuzzleAnswerResponseSerializer,
            400: ErrorWithDetailsSerializer,
            404: ErrorWithDetailsSerializer,
            500: ErrorWithDetailsSerializer,
        },
    )
    def post(self, request):
        serializer = SubmitPuzzleAnswerRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        puzzle_id = serializer.validated_data["puzzle_id"]
        user_answer = serializer.validated_data["user_answer"]

        try:
            puzzle = PuzzleVerification.objects.get(id=puzzle_id)
        except PuzzleVerification.DoesNotExist:
            return Response(
                {"status": "error", "message": "Puzzle not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        is_correct = puzzle.answer.strip().lower() == user_answer.strip().lower()

        puzzle.user_answer = user_answer
        puzzle.is_correct = is_correct
        puzzle.save(update_fields=["user_answer", "is_correct"])

        return Response(
            {
                "correct": is_correct,
                "message": "Correct!" if is_correct else "Incorrect, try again.",
            },
            status=status.HTTP_200_OK,
        )


# ------------------------------
# EarnCoinsView
# ------------------------------
class EarnCoinsView(generics.GenericAPIView):
    serializer_class = EarnCoinsRequestSerializer

    @extend_schema(
        request=EarnCoinsRequestSerializer,
        responses={201: CoinTransactionSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data["user_id"]
        amount = serializer.validated_data["amount"]

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=404)

        if not has_solved_puzzle(user):
            return Response(
                {"error": "You must solve a puzzle before earning coins."},
                status=403,
            )

        transaction = CoinTransaction.objects.create(
            user=user, transaction_type="earn", amount=amount
        )

        return Response(CoinTransactionSerializer(transaction).data, status=201)


# ------------------------------
# SpendCoinsView
# ------------------------------
class SpendCoinsView(generics.GenericAPIView):
    serializer_class = SpendCoinsRequestSerializer

    @extend_schema(
        request=SpendCoinsRequestSerializer,
        responses={201: CoinTransactionSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data["user_id"]
        amount = serializer.validated_data["amount"]

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=404)

        if not has_solved_puzzle(user):
            return Response(
                {"error": "You must solve a puzzle before spending coins."},
                status=403,
            )

        # calculate balance
        total_earned = (
            CoinTransaction.objects.filter(
                user=user, transaction_type="earn"
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )
        total_spent = (
            CoinTransaction.objects.filter(
                user=user, transaction_type="spend"
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        balance = total_earned - total_spent
        if amount > balance:
            return Response({"error": "Insufficient coin balance."}, status=400)

        transaction = CoinTransaction.objects.create(
            user=user, transaction_type="spend", amount=amount
        )

        return Response(CoinTransactionSerializer(transaction).data, status=201)


# class JobListView(generics.ListAPIView):
#     serializer_class = JobListSerializer
#     queryset = Job.objects.all()

#     def get_queryset(self):
#         queryset = super().get_queryset().filter(status="open")

#         job_type = self.request.query_params.get("jobType")
#         category = self.request.query_params.get("category")
#         status_param = self.request.query_params.get("status")

#         if job_type:
#             queryset = queryset.filter(job_type=job_type)
#         if category:
#             queryset = queryset.filter(category=category)
#         if status_param:
#             queryset = queryset.filter(status=status_param)

#         return queryset

#     def list(self, request, *args, **kwargs):
#         try:
#             return super().list(request, *args, **kwargs)
#         except Exception as e:
#             return Response(
#                 {"status": "error", "message": f"Failed to retrieve jobs: {str(e)}"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )


# class JobDetailView(generics.RetrieveAPIView):
#     queryset = Job.objects.all()
#     serializer_class = JobDetailSerializer
#     lookup_field = "id"

#     def retrieve(self, request, *args, **kwargs):
#         try:
#             return super().retrieve(request, *args, **kwargs)
#         except Exception as e:
#             return Response(
#                 {"message": f"Failed to retrieve job: {str(e)}", "status": "error"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )


# class JobApplicationView(generics.CreateAPIView):
#     serializer_class = JobApplicationSerializer

#     def create(self, request, *args, **kwargs):
#         try:
#             # Handle both DRF request and regular Django request
#             if hasattr(request, "data"):
#                 data = request.data
#             else:
#                 # For regular Django request, parse JSON from body
#                 import json

#                 data = json.loads(request.body.decode("utf-8")) if request.body else {}

#             serializer = self.get_serializer(data=data)
#             if serializer.is_valid():
#                 # Get the job
#                 job_id = serializer.validated_data.get("job", {}).get("id")
#                 job = Job.objects.get(id=job_id)

#                 # Get applicant details
#                 applicant_email = serializer.validated_data.get("email", "")
#                 first_name = serializer.validated_data.get("first_name", "")
#                 last_name = serializer.validated_data.get("last_name", "")
#                 applicant_name = f"{first_name} {last_name}".strip()

#                 # Create the application
#                 application = serializer.save(job=job)

#                 # Send automatic confirmation email
#                 subject = f"Application Received - {job.title} at Bondah Dating"
#                 message = f"""
# Hi {applicant_name},

# Thank you for your interest in joining the Bondah Dating team!

# We've received your application for the {job.title} position and are excited to review your qualifications.

# What happens next:
# • Our team will review your application within 3-5 business days
# • If selected, we'll contact you for the next steps
# • You'll receive updates on your application status

# Application Details:
# • Position: {job.title}
# • Application ID: {application.id}
# • Applied: {application.applied_at.strftime('%B %d, %Y')}

# We appreciate your interest in helping us build the future of dating!

# Best regards,
# The Bondah Team

# P.S. Follow us on social media to stay updated on our journey!
#                 """.strip()

#                 # Log email attempt
#                 email_log = EmailLog.objects.create(
#                     email_type="job_application_confirmation",
#                     recipient_email=applicant_email,
#                     subject=subject,
#                     message=message,
#                 )

#                 try:
#                     # Send email using Django's email functionality
#                     send_mail(
#                         subject=subject,
#                         message=message,
#                         from_email=settings.DEFAULT_FROM_EMAIL,
#                         recipient_list=[applicant_email],
#                         fail_silently=False,
#                     )

#                     email_log.is_sent = True
#                     email_log.save()

#                 except Exception as e:
#                     email_log.is_sent = False
#                     email_log.error_message = str(e)
#                     email_log.save()
#                     # Don't fail the application if email fails

#                 # Return success response
#                 return Response(
#                     {
#                         "message": "Job application submitted successfully! Confirmation email sent.",
#                         "status": "success",
#                         "applicationId": application.id,
#                     },
#                     status=status.HTTP_201_CREATED,
#                 )

#             return Response(
#                 {
#                     "message": "Invalid application data",
#                     "status": "error",
#                     "errors": serializer.errors,
#                 },
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         except Job.DoesNotExist:
#             return Response(
#                 {"message": "Job not found", "status": "error"},
#                 status=status.HTTP_404_NOT_FOUND,
#             )
#         except Exception as e:
#             return Response(
#                 {"message": f"Application failed: {str(e)}", "status": "error"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )


class AdminLoginView(GenericAPIView):
    serializer_class = AdminLoginSerializer

    @extend_schema(
        request=AdminLoginSerializer,
        responses={
            200: AdminLoginOTPResponseSerializer,
            400: SimpleStatusResponseSerializer,
            401: SimpleStatusResponseSerializer,
            500: SimpleStatusResponseSerializer,
        },
        description="Admin login endpoint. Generates OTP and sends to email.",
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        try:
            admin_user = AdminUser.objects.get(email=email, is_active=True)
        except AdminUser.DoesNotExist:
            return Response(
                {"status": "error", "message": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not check_password(password, admin_user.password):
            return Response(
                {"status": "error", "message": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Generate OTP
        otp_code = "".join(random.choices(string.digits, k=6))
        expires_at = timezone.now() + timedelta(minutes=10)

        AdminOTP.objects.create(
            admin_user=admin_user, otp_code=otp_code, expires_at=expires_at
        )

        # Send OTP email
        subject = " Admin Login OTP - Bondah Dating"
        message = f"Your OTP for admin login is: {otp_code}\nIt expires in 10 minutes."
        send_mail(
            subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=True
        )

        return Response(
            {
                "status": "success",
                "message": "OTP sent to your email",
            },
            status=status.HTTP_200_OK,
        )


class AdminOTPVerificationView(GenericAPIView):
    serializer_class = AdminOTPVerificationSerializer

    @extend_schema(
        request=AdminOTPVerificationSerializer,
        responses={
            200: AdminLoginSuccessResponseSerializer,
            400: SimpleStatusResponseSerializer,
            500: SimpleStatusResponseSerializer,
        },
        description="Verify OTP and generate JWT tokens for admin.",
    )
    def post(self, request, *args, **kwargs):
        # Use GenericAPIView's serializer handling
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        otp_code = serializer.validated_data["otp_code"]

        try:
            admin_user = AdminUser.objects.get(email=email, is_active=True)
            otp = AdminOTP.objects.filter(
                admin_user=admin_user, otp_code=otp_code, is_used=False
            ).latest("created_at")
        except (AdminUser.DoesNotExist, AdminOTP.DoesNotExist):
            return Response(
                {"status": "error", "message": "Invalid OTP"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp.expires_at < timezone.now():
            return Response(
                {"status": "error", "message": "OTP has expired"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mark OTP as used
        otp.is_used = True
        otp.save(update_fields=["is_used"])

        # Update last login
        admin_user.last_login = timezone.now()
        admin_user.save(update_fields=["last_login"])

        # Generate JWT tokens
        tokens = generate_tokens(admin_user)

        return Response(
            {
                "status": "success",
                "message": "Login successful",
                "admin_email": admin_user.email,
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "access_token_expires": tokens["access_token_expires"],
                "refresh_token_expires": tokens["refresh_token_expires"],
            },
            status=status.HTTP_200_OK,
        )


class AdminJobListView(generics.ListAPIView):
    queryset = Job.objects.all()
    serializer_class = AdminJobListSerializer

    @extend_schema(
        responses={200: AdminJobListSerializer(many=True)},
        description="List all jobs with summary information.",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AdminJobCreateView(generics.CreateAPIView):
    queryset = Job.objects.all()
    serializer_class = AdminJobCreateSerializer

    @extend_schema(
        request=AdminJobCreateSerializer,
        responses={201: AdminJobCreateSerializer, 400: SimpleStatusResponseSerializer},
        description="Create a new job posting.",
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class AdminJobUpdateView(generics.UpdateAPIView):
    queryset = Job.objects.all()
    serializer_class = AdminJobUpdateSerializer

    @extend_schema(
        request=AdminJobUpdateSerializer,
        responses={200: AdminJobUpdateSerializer, 400: SimpleStatusResponseSerializer},
        description="Update an existing job posting.",
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)


class AdminJobApplicationsView(GenericAPIView):
    serializer_class = AdminJobApplicationSerializer

    @extend_schema(
        responses={200: AdminJobApplicationSerializer(many=True)},
        description="Retrieve job applications with optional filters",
    )
    def get(self, request, *args, **kwargs):
        job_id = request.query_params.get("job_id")
        status_filter = request.query_params.get("status")

        applications = JobApplication.objects.all().order_by("-applied_at")
        if job_id:
            applications = applications.filter(job_id=job_id)
        if status_filter:
            applications = applications.filter(status=status_filter)

        serializer = self.get_serializer(applications, many=True)
        return Response(
            {
                "message": "Applications retrieved successfully",
                "status": "success",
                "applications": serializer.data,
            }
        )


class AdminUpdateApplicationStatusView(GenericAPIView):
    serializer_class = AdminUpdateApplicationStatusSerializer

    @extend_schema(
        request=AdminUpdateApplicationStatusSerializer,
        responses={200: AdminJobApplicationSerializer},
        description="Update the status of a specific job application",
    )
    def put(self, request, application_id, *args, **kwargs):
        try:
            application = JobApplication.objects.get(id=application_id)

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            application.status = serializer.validated_data["status"]
            application.save()

            return Response(
                {
                    "message": "Application status updated successfully",
                    "status": "success",
                    "application": AdminJobApplicationSerializer(application).data,
                },
                status=status.HTTP_200_OK,
            )

        except JobApplication.DoesNotExist:
            return Response(
                {"message": "Application not found", "status": "error"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "message": f"Failed to update application status: {str(e)}",
                    "status": "error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminJobApplicationDetailView(GenericAPIView):
    serializer_class = AdminJobApplicationDetailSerializer

    @extend_schema(
        responses={200: AdminJobApplicationDetailSerializer},
        description="Retrieve detailed information of a specific job application",
    )
    def get(self, request, application_id, *args, **kwargs):
        """Get detailed view of a specific job application"""
        try:
            application = JobApplication.objects.get(id=application_id)
            serializer = self.get_serializer(application)
            return Response(
                {
                    "message": "Application details retrieved successfully",
                    "status": "success",
                    "application": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except JobApplication.DoesNotExist:
            return Response(
                {"message": "Application not found", "status": "error"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "message": f"Failed to retrieve application details: {str(e)}",
                    "status": "error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    request=AdminTokenRefreshSerializer,
    responses={200: OpenApiTypes.OBJECT},
    description="Refresh access token using refresh token",
)
class AdminTokenRefreshView(GenericAPIView):
    serializer_class = AdminTokenRefreshSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.validated_data["refresh_token"]

        try:
            new_tokens = refresh_access_token(refresh_token)
            return Response(
                {
                    "message": "Token refreshed successfully",
                    "status": "success",
                    "access_token": new_tokens["access_token"],
                    "access_token_expires": new_tokens["access_token_expires"],
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"message": f"Failed to refresh token: {str(e)}", "status": "error"},
                status=status.HTTP_401_UNAUTHORIZED,
            )


@extend_schema(
    request=AdminLogoutSerializer,
    responses={200: OpenApiTypes.OBJECT},
    description="Logout admin user and revoke refresh token",
)
class AdminLogoutView(GenericAPIView):
    serializer_class = AdminLogoutSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.validated_data.get("refresh_token")
        if refresh_token:
            revoke_refresh_token(refresh_token)

        return Response(
            {"message": "Logged out successfully", "status": "success"},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    responses={200: OpenApiTypes.OBJECT},
    description="Verify if access token is valid",
)
class AdminVerifyTokenView(GenericAPIView):
    permission_classes = [AdminJWTPermission]

    def get(self, request, *args, **kwargs):
        try:
            admin_user = request.admin_user
            return Response(
                {
                    "message": "Token is valid",
                    "status": "success",
                    "admin_email": admin_user.email,
                    "admin_id": admin_user.id,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"message": f"Token verification failed: {str(e)}", "status": "error"},
                status=status.HTTP_401_UNAUTHORIZED,
            )


@extend_schema(
    responses={200: OpenApiTypes.OBJECT},
    description="Debug endpoint to check authentication status",
)
class AdminDebugAuthView(GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        auth_header = request.headers.get("Authorization")
        debug_info = {
            "has_authorization_header": bool(auth_header),
            "authorization_header": auth_header,
            "all_headers": dict(request.headers),
        }

        if auth_header:
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                debug_info["token_length"] = len(token) if token else 0
                debug_info["token_format"] = "Valid Bearer format"
                try:
                    from .jwt_utils import verify_token

                    payload = verify_token(token, "access")
                    debug_info["token_valid"] = True
                    debug_info["token_payload"] = payload
                except Exception as e:
                    debug_info["token_valid"] = False
                    debug_info["token_error"] = str(e)
            else:
                debug_info["token_format"] = (
                    "Invalid format - should start with 'Bearer '"
                )
        else:
            debug_info["token_format"] = "No Authorization header"

        return Response(
            {
                "message": "Debug authentication info",
                "status": "success",
                "debug_info": debug_info,
            },
            status=status.HTTP_200_OK,
        )


# =============================================================================
# MOBILE APP AUTHENTICATION VIEWS
# =============================================================================


class RegisterRequestOTPView(generics.CreateAPIView):
    serializer_class = RegisterRequestOTPSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # serializer.save() returns a dict
        data = serializer.save()

        # Always return a dict as JSON
        return Response(data, status=status.HTTP_200_OK)


@method_decorator(
    ratelimit(key="ip", rate="5/m", method="POST", block=False), name="dispatch"
)
class VerifyOTPAndRegisterView(generics.CreateAPIView):
    serializer_class = VerifyOTPAndRegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):

        # Check if the request exceeded the rate limit
        if getattr(request, "limited", False):
            return Response(
                {"error": "Too many requests. Please try again in a minute."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # serializer.save() returns a dict containing user + tokens
        data = serializer.save()

        user = data["user"]
        tokens = data["tokens"]

        # Return a clean dict
        response_data = {
            "user": {
                "id": user.id,
                "email": user.email,
            },
            "tokens": tokens,
        }

        return Response(response_data, status=status.HTTP_201_CREATED)


class ResendEmailOTPView(generics.CreateAPIView):
    serializer_class = ResendEmailOTPSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()  # dict returned
        return Response(data, status=200)


# -------------------------
# User Login
# -------------------------


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

        firebase_token = serializer.validated_data.get("firebase_token")
        email = serializer.validated_data.get("email")
        password = serializer.validated_data.get("password")

        try:
            user = None

            # Case 1: Firebase login
            if firebase_token:
                decoded_token = verify_firebase_token(firebase_token)
                if decoded_token:
                    user = get_or_create_user_from_firebase(decoded_token)
                else:
                    # Ignore Firebase failure and fallback to email/password
                    pass

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

        except Exception as e:
            return Response(
                {"message": f"Login failed: {str(e)}", "status": "error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# -------------------------
# User Logout
# -------------------------


@extend_schema(
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
    serializer_class = UserLogoutRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.validated_data.get("refresh_token")
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()

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
    request=PasswordResetSerializer,
    responses={
        200: PasswordResetSerializer,
        400: PasswordResetSerializer,
        500: PasswordResetSerializer,
    },
)
class PasswordResetView(generics.GenericAPIView):
    serializer_class = PasswordResetSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")

        # Always respond success (avoid email enumeration)
        response_msg = {
            "message": "If the email exists, OTP has been sent",
            "status": "success",
        }

        user = User.objects.filter(email=email).first()
        if not user:
            return Response(response_msg, status=200)

        # Delete old OTPs for this email
        PasswordResetOTP.objects.filter(email=email, is_used=False).delete()

        # Generate new OTP
        otp = PasswordResetOTP.generate_otp()

        # Store it in DB
        PasswordResetOTP.objects.create(
            email=email,
            otp=otp,
        )

        # Send OTP via email
        try:
            send_mail(
                subject="Your Password Reset OTP",
                message=f"Your OTP is {otp}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as e:
            print("Email error:", e)

        return Response(response_msg, status=200)


# @extend_schema(
#     request=PasswordResetConfirmSerializer,
#     responses={
#         200: PasswordResetConfirmSerializer,
#         400: PasswordResetConfirmSerializer,
#         500: PasswordResetConfirmSerializer,
#     },
# )
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

        otp_record = PasswordResetOTP.objects.filter(
            otp=otp,
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
    request=PasswordResetResendSerializer,
    responses={200: PasswordResetResendSerializer},
)
class PasswordResendOTPView(generics.GenericAPIView):
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
        send_mail(
            subject="Your Password Reset OTP",
            message=f"Your OTP is {otp}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )

        return Response(response_msg, status=200)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """User profile view for mobile app"""

    serializer_class = UserProfileDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            profile_data = serializer.data

            # Try to get additional data from Firestore
            from .firebase_utils import get_user_profile_from_firestore

            # Assuming user has firebase_uid, or use email as key
            firebase_uid = getattr(
                instance, "firebase_uid", instance.email
            )  # Adjust if you add firebase_uid field
            firestore_profile = get_user_profile_from_firestore(firebase_uid)
            if firestore_profile:
                profile_data.update(firestore_profile)  # Merge Firestore data

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

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop("partial", False)
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            updated_user = serializer.save()

            # Update Firestore if additional data provided
            firestore_data = {}
            firestore_fields = [
                "bio",
                "interests",
                "photos",
            ]  # Example fields stored in Firestore
            for field in firestore_fields:
                if field in request.data:
                    firestore_data[field] = request.data[field]

            if firestore_data:
                firebase_uid = getattr(instance, "firebase_uid", instance.email)
                update_user_profile_in_firestore(firebase_uid, firestore_data)

            return Response(
                {
                    "message": "Profile updated successfully",
                    "status": "success",
                    "user": self.get_serializer(updated_user).data,
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
    request=None,
    responses={
        200: SimpleStatusResponseSerializer,
        500: CustomErrorResponseSerializer,
    },
    description="Deactivate the authenticated user's account",
)
class AccountDeactivationView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            user.is_active = False
            user.save(update_fields=["is_active"])

            return Response(
                {"message": "Account deactivated successfully", "status": "success"},
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


@extend_schema_view(
    get=extend_schema(
        responses={
            200: NotificationSettingsResponseSerializer,
            500: CustomErrorResponseSerializer,
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
    ),
)
class NotificationSettingsView(generics.GenericAPIView):
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
class LanguageSettingsView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LanguageSettingsSerializer


@method_decorator(
    ratelimit(key="ip", rate="5/m", method="POST", block=False), name="dispatch"
)
class GoogleOAuthView(generics.GenericAPIView):
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

        access_token = serializer.validated_data["access_token"]

        try:
            from .oauth_utils import (
                GoogleOAuthVerifier,
                OAuthUserManager,
                OAuthTokenGenerator,
            )

            oauth_data, error = GoogleOAuthVerifier.verify_access_token(access_token)

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


class AppleOAuthView(generics.GenericAPIView):
    """Apple Sign-In for mobile app"""

    permission_classes = [AllowAny]
    serializer_class = AppleOAuthSerializer

    @extend_schema(
        request=AppleOAuthSerializer,
        responses=OAuthLoginResponseSerializer,
        description="Login or register user using Apple identity token.",
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        identity_token = serializer.validated_data["identity_token"]

        try:
            from .oauth_utils import (
                AppleOAuthVerifier,
                OAuthUserManager,
                OAuthTokenGenerator,
            )

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


class SocialLoginView(generics.GenericAPIView):
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

                from .oauth_utils import (
                    GoogleOAuthVerifier,
                    OAuthUserManager,
                    OAuthTokenGenerator,
                )

                oauth_data, error = GoogleOAuthVerifier.verify_access_token(
                    access_token
                )

            else:
                identity_token = serializer.validated_data["apple_data"][
                    "identity_token"
                ]

                from .oauth_utils import (
                    AppleOAuthVerifier,
                    OAuthUserManager,
                    OAuthTokenGenerator,
                )

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


class DeviceRegistrationView(generics.CreateAPIView):
    """
    Register a device for push notifications.
    Automatically deactivates old tokens for the same user/device combination.
    """

    serializer_class = DeviceRegistrationSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        device_id = serializer.validated_data["device_id"]
        device_type = serializer.validated_data["device_type"]
        push_token = serializer.validated_data["push_token"]
        user = request.user

        # Deactivate previous tokens for this device ID and user
        DeviceRegistration.objects.filter(user=user, device_id=device_id).update(
            is_active=False
        )

        # Create or update the device
        device, created = DeviceRegistration.objects.update_or_create(
            device_id=device_id,
            user=user,
            defaults={
                "device_type": device_type,
                "push_token": push_token,
                "is_active": True,
            },
        )

        return Response(
            {
                "message": "Device registered successfully",
                "status": "success",
                "device_id": device.device_id,
                "created": created,
                "active_tokens": DeviceRegistration.objects.filter(
                    user=user, is_active=True
                ).count(),
            },
            status=status.HTTP_200_OK,
        )


class OAuthLinkAccountView(generics.GenericAPIView):
    """Link social account to existing user"""

    permission_classes = [IsAuthenticated]
    serializer_class = OAuthLinkAccountRequestSerializer

    @extend_schema(
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
            from .oauth_utils import (
                GoogleOAuthVerifier,
                AppleOAuthVerifier,
                OAuthUserManager,
            )

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


class OAuthUnlinkAccountView(generics.GenericAPIView):
    """Unlink social account from user"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
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


class SocialAccountsListView(generics.ListAPIView):
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


# Location Management Views
class LocationUpdateView(generics.UpdateAPIView):
    """
    Update the authenticated user's current GPS location.
    """

    serializer_class = LocationUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # The user object is the "object" to update
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            latitude = serializer.validated_data["latitude"]
            longitude = serializer.validated_data["longitude"]
            accuracy = serializer.validated_data.get("accuracy")
            source = serializer.validated_data.get("source", "gps")

            success = update_user_location(
                request.user, latitude, longitude, accuracy, source
            )

            if not success:
                return Response(
                    {"message": "Failed to update location", "status": "error"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(
                {
                    "message": "Location updated successfully",
                    "status": "success",
                    "location": {
                        "latitude": float(latitude),
                        "longitude": float(longitude),
                        "city": request.user.city,
                        "state": request.user.state,
                        "country": request.user.country,
                    },
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"message": f"Location update failed: {str(e)}", "status": "error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AddressGeocodeView(generics.GenericAPIView):
    """
    Convert a user-provided address into GPS coordinates.
    """

    serializer_class = AddressGeocodeSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            address = serializer.validated_data["address"]
            result = geocode_address(address)

            if not result:
                return Response(
                    {"message": "Could not geocode address", "status": "error"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                {
                    "message": "Address geocoded successfully",
                    "status": "success",
                    "coordinates": {
                        "latitude": result["latitude"],
                        "longitude": result["longitude"],
                        "formatted_address": result["formatted_address"],
                        "accuracy": result.get("accuracy", "UNKNOWN"),
                    },
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"message": f"Geocoding failed: {str(e)}", "status": "error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LocationPrivacyUpdateView(generics.UpdateAPIView):
    """
    Update the authenticated user's location privacy settings.
    """

    serializer_class = LocationPrivacyUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            self.get_object(), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        try:
            serializer.save()
            return Response(
                {
                    "message": "Location privacy settings updated successfully",
                    "status": "success",
                    "settings": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {
                    "message": f"Failed to update privacy settings: {str(e)}",
                    "status": "error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LocationPermissionsView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update the authenticated user's location permissions.
    """

    serializer_class = LocationPermissionSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        # Get or create permissions for the user
        obj, created = LocationPermission.objects.get_or_create(user=self.request.user)
        return obj

    def retrieve(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(self.get_object())
            return Response(
                {
                    "message": "Location permissions retrieved successfully",
                    "status": "success",
                    "permissions": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {
                    "message": f"Failed to retrieve permissions: {str(e)}",
                    "status": "error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(
                self.get_object(), data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {
                    "message": "Location permissions updated successfully",
                    "status": "success",
                    "permissions": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {
                    "message": f"Failed to update permissions: {str(e)}",
                    "status": "error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LocationHistoryView(generics.ListAPIView):
    """Get user's location history"""

    serializer_class = LocationHistorySerializer

    def get_queryset(self):
        return LocationHistory.objects.filter(user=self.request.user)[:30]

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {
                    "message": "Location history retrieved successfully",
                    "status": "success",
                    "history": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {
                    "message": f"Failed to retrieve location history: {str(e)}",
                    "status": "error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# --------------------------
# 1. Nearby Users
# --------------------------
class NearbyUsersView(generics.GenericAPIView):
    """
    Find nearby users for matching.
    """

    serializer_class = NearbyUserSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        max_distance = request.GET.get("max_distance")
        if max_distance:
            try:
                max_distance = int(max_distance)
            except ValueError:
                return Response(
                    {"message": "max_distance must be an integer", "status": "error"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            nearby_users = find_nearby_users(request.user, max_distance)

            results = []
            for user_data in nearby_users:
                user = user_data["user"]
                serializer = self.get_serializer(user)
                data = serializer.data
                data["distance"] = user_data["distance"]
                data["coordinates"] = user_data["coordinates"]
                results.append(data)

            return Response(
                {
                    "message": "Nearby users retrieved successfully",
                    "status": "success",
                    "nearby_users": results,
                    "count": len(results),
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {
                    "message": f"Failed to find nearby users: {str(e)}",
                    "status": "error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# --------------------------
# 2. Match Preferences
# --------------------------
class MatchPreferencesView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update user's matching preferences.
    """

    serializer_class = MatchPreferencesSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return Response(
            {
                "message": "Match preferences retrieved successfully",
                "status": "success",
                "preferences": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            self.get_object(), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "message": "Match preferences updated successfully",
                "status": "success",
                "preferences": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


# --------------------------
# 3. User Profile with Location
# --------------------------
class UserLocationProfileView(generics.RetrieveAPIView):
    """
    Retrieve user profile along with location info.
    """

    serializer_class = UserProfileWithLocationSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return Response(
            {
                "message": "User profile retrieved successfully",
                "status": "success",
                "user": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


# --------------------------
# 4. Location Statistics (Admin Only)
# --------------------------
class LocationStatisticsView(GenericAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = LocationStatisticsSerializer

    @extend_schema(
        responses={
            200: LocationStatisticsSerializer,
            403: OpenApiResponse(description="Admin access required"),
            500: OpenApiResponse(description="Server error"),
        },
        description="Retrieve location-related statistics (admin only)",
    )
    def get(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response(
                {"message": "Admin access required", "status": "error"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            stats = get_location_statistics()  # your function
            serializer = self.get_serializer(stats)
            return Response(
                {
                    "message": "Location statistics retrieved successfully",
                    "status": "success",
                    "statistics": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {
                    "message": f"Failed to retrieve statistics: {str(e)}",
                    "status": "error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# =============================================================================
# EMAIL AND PHONE VERIFICATION VIEWS
# =============================================================================


# class EmailOTPRequestView(GenericAPIView):
#     permission_classes = [AllowAny]
#     serializer_class = EmailOTPRequestSerializer

#     @extend_schema(
#         request=EmailOTPRequestSerializer, responses={200: OTPResponseSerializer}
#     )
#     def post(self, request):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         email = serializer.validated_data["email"]

#         User = get_user_model()
#         user, created = User.objects.get_or_create(
#             email=email, defaults={"username": email, "is_active": False}
#         )

#         if not EmailVerification.can_resend_for_email(email):
#             return Response(
#                 {"message": "Too many OTP requests. Wait 1 minute", "status": "error"},
#                 status=status.HTTP_429_TOO_MANY_REQUESTS,
#             )

#         verification = EmailVerification.create_verification(user, email)
#         subject = "Verify Your Email - Bondah Dating"
#         message = f"Your OTP is: {verification.otp_code} (expires in 10 minutes)"
#         send_mail(
#             subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False
#         )

#         return Response(
#             {
#                 "message": "OTP sent to your email",
#                 "status": "success",
#                 "email": email,
#                 "expires_in": 600,
#             },
#             status=status.HTTP_200_OK,
#         )


# class EmailOTPVerifyView(GenericAPIView):
#     permission_classes = [AllowAny]
#     serializer_class = EmailOTPVerifySerializer

#     @extend_schema(
#         request=EmailOTPVerifySerializer, responses={200: OTPResponseSerializer}
#     )
#     def post(self, request):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         email = serializer.validated_data["email"]
#         otp_code = serializer.validated_data["otp_code"]

#         try:
#             verification = EmailVerification.objects.filter(
#                 email=email, otp_code=otp_code, is_used=False
#             ).latest("created_at")

#             if verification.is_expired():
#                 return Response(
#                     {"message": "OTP expired", "status": "error"},
#                     status=status.HTTP_400_BAD_REQUEST,
#                 )

#             verification.is_verified = True
#             verification.is_used = True
#             verification.verified_at = timezone.now()
#             verification.save()

#             user = verification.user
#             user.is_active = True
#             user.save()

#             user_status, _ = UserVerificationStatus.objects.get_or_create(user=user)
#             user_status.email_verified = True
#             user_status.email_verified_at = timezone.now()
#             user_status.update_verification_level()

#             return Response(
#                 {
#                     "message": "Email verified successfully",
#                     "status": "success",
#                     "user": {
#                         "id": user.id,
#                         "email": user.email,
#                         "is_active": user.is_active,
#                     },
#                 },
#                 status=status.HTTP_200_OK,
#             )

#         except EmailVerification.DoesNotExist:
#             return Response(
#                 {"message": "Invalid OTP", "status": "error"},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )


# class PhoneOTPRequestView(GenericAPIView):
#     permission_classes = [AllowAny]
#     serializer_class = PhoneOTPRequestSerializer

#     @extend_schema(
#         request=PhoneOTPRequestSerializer, responses={200: OTPResponseSerializer}
#     )
#     def post(self, request):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         phone_number = serializer.validated_data["phone_number"]
#         country_code = serializer.validated_data.get("country_code", "+1")
#         user_id = serializer.validated_data["user_id"]

#         User = get_user_model()
#         try:
#             user = User.objects.get(id=user_id)
#         except User.DoesNotExist:
#             return Response(
#                 {"message": "User not found", "status": "error"}, status=404
#             )

#         if not PhoneVerification.can_resend_for_phone(phone_number, country_code):
#             return Response(
#                 {"message": "Too many OTP requests. Wait 1 minute", "status": "error"},
#                 status=status.HTTP_429_TOO_MANY_REQUESTS,
#             )

#         verification = PhoneVerification.create_verification(
#             user, phone_number, country_code
#         )
#         print(f"SMS OTP for {country_code}{phone_number}: {verification.otp_code}")

#         return Response(
#             {
#                 "message": "OTP sent to your phone",
#                 "status": "success",
#                 "phone_number": f"{country_code}{phone_number}",
#                 "expires_in": 600,
#             },
#             status=status.HTTP_200_OK,
#         )


# class PhoneOTPVerifyView(GenericAPIView):
#     permission_classes = [AllowAny]
#     serializer_class = PhoneOTPVerifySerializer

#     @extend_schema(
#         request=PhoneOTPVerifySerializer, responses={200: OTPResponseSerializer}
#     )
#     def post(self, request):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         phone_number = serializer.validated_data["phone_number"]
#         country_code = serializer.validated_data.get("country_code", "+1")
#         otp_code = serializer.validated_data["otp_code"]

#         try:
#             verification = PhoneVerification.objects.filter(
#                 phone_number=phone_number,
#                 country_code=country_code,
#                 otp_code=otp_code,
#                 is_used=False,
#             ).latest("created_at")

#             if verification.is_expired():
#                 return Response(
#                     {"message": "OTP expired", "status": "error"}, status=400
#                 )

#             verification.is_verified = True
#             verification.is_used = True
#             verification.verified_at = timezone.now()
#             verification.save()

#             user_status, _ = UserVerificationStatus.objects.get_or_create(
#                 user=verification.user
#             )
#             user_status.phone_verified = True
#             user_status.phone_verified_at = timezone.now()
#             user_status.update_verification_level()

#             return Response(
#                 {
#                     "message": "Phone verified successfully",
#                     "status": "success",
#                     "user": {
#                         "id": verification.user.id,
#                         "email": verification.user.email,
#                         "phone_verified": True,
#                     },
#                 },
#                 status=status.HTTP_200_OK,
#             )

#         except PhoneVerification.DoesNotExist:
#             return Response({"message": "Invalid OTP", "status": "error"}, status=400)


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


# =============================================================================
# ADVANCED USER SEARCH AND DISCOVERY VIEWS
# =============================================================================


class UserSearchView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSearchSerializer  # Output serializer
    # pagination_class = CustomPagination

    @extend_schema(
        request=UserSearchFilterSerializer,
        responses={200: UserSearchSerializer(many=True)},
    )
    def get_queryset(self):

        filter_serializer = UserSearchFilterSerializer(data=self.request.GET)
        filter_serializer.is_valid(raise_exception=True)
        filters = filter_serializer.validated_data

        queryset = User.objects.filter(is_active=True).exclude(id=self.request.user.id)

        # Apply dynamic filters
        filter_map = {
            "gender": "gender",
            "age_min": "age__gte",
            "age_max": "age__lte",
            "education_level": "education_level",
            "relationship_status": "relationship_status",
            "smoking_preference": "smoking_preference",
            "drinking_preference": "drinking_preference",
            "pet_preference": "pet_preference",
            "exercise_frequency": "exercise_frequency",
            "kids_preference": "kids_preference",
            "personality_type": "personality_type",
            "love_language": "love_language",
            "dating_type": "dating_type",
        }

        for key, field in filter_map.items():
            if filters.get(key):
                queryset = queryset.filter(**{field: filters[key]})

        if filters.get("religion"):
            queryset = queryset.filter(religion__icontains=filters["religion"])
        if filters.get("is_matchmaker") is not None:
            queryset = queryset.filter(is_matchmaker=filters["is_matchmaker"])
        if filters.get("has_photos"):
            queryset = queryset.exclude(profile_picture__isnull=True).exclude(
                profile_picture=""
            )

        # Text search
        if filters.get("query"):
            q = filters["query"]
            queryset = queryset.filter(
                models.Q(name__icontains=q)
                | models.Q(bio__icontains=q)
                | models.Q(city__icontains=q)
                | models.Q(state__icontains=q)
                | models.Q(country__icontains=q)
            )

        # Interests & hobbies
        for field in ["interests", "hobbies"]:
            if filters.get(field):
                for value in filters[field]:
                    queryset = queryset.filter(**{f"{field}__icontains": value})

        # Distance filtering
        if filters.get("max_distance") and self.request.user.has_location:
            max_distance = filters["max_distance"]
            nearby_ids = [
                u.id
                for u in queryset
                if u.has_location
                and self.request.user.get_distance_to(u) <= max_distance
            ]
            queryset = queryset.filter(id__in=nearby_ids)

        queryset = queryset.order_by("-date_joined")

        # Optional: Store search query for analytics
        SearchQuery.objects.create(
            user=self.request.user,
            query=filters.get("query", ""),
            filters=filters,
            results_count=queryset.count(),
        )

        return queryset


class UserProfileDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileDetailSerializer
    lookup_field = "id"
    lookup_url_kwarg = "user_id"

    def get_queryset(self):
        return User.objects.filter(is_active=True)

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        # Track profile view
        UserProfileView.objects.get_or_create(
            viewer=request.user,
            viewed_user=self.get_object(),
            defaults={"source": "direct"},
        )
        return response


class UserRecommendationsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RecommendationSerializer

    def get_queryset(self):
        user = self.request.user

        if user.has_location:
            nearby_users = User.objects.filter(
                is_active=True, latitude__isnull=False, longitude__isnull=False
            ).exclude(id=user.id)
            for nearby_user in nearby_users:
                distance = user.get_distance_to(nearby_user)
                if distance and distance <= user.max_distance:
                    from .location_utils import calculate_match_score

                    score = calculate_match_score(user, nearby_user)
                    if score > 50:
                        RecommendationEngine.objects.get_or_create(
                            user=user,
                            recommended_user=nearby_user,
                            defaults={"score": score, "algorithm": "location_based"},
                        )

        return RecommendationEngine.objects.filter(user=user, is_active=True).order_by(
            "-score"
        )[:20]


class CategoryFilterView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSearchSerializer  # Output serializer

    @extend_schema(
        request=None,
        responses=UserSearchSerializer(many=True),
        parameters=[
            OpenApiParameter(
                name="category",
                type=str,
                required=True,
                description="User category to filter",
            ),
            OpenApiParameter(name="page", type=int, required=False),
            OpenApiParameter(name="page_size", type=int, required=False),
        ],
    )
    def get_queryset(self):
        from .serializers import CategoryFilterSerializer

        filter_serializer = CategoryFilterSerializer(data=self.request.GET)
        filter_serializer.is_valid(raise_exception=True)
        category = filter_serializer.validated_data["category"]

        queryset = User.objects.filter(is_active=True).exclude(id=self.request.user.id)

        category_map = {
            "casual_dating": {"dating_type": "casual"},
            "lgbtq": {"gender__in": ["non_binary", "other"]},
            "sugar": {"dating_type": "sugar"},
            "serious": {"dating_type": "serious"},
            "friends": {"dating_type": "friends"},
            "matchmakers": {"is_matchmaker": True},
            "all": {},
        }

        filters = category_map.get(category, {})
        if filters:
            queryset = queryset.filter(**filters)

        return queryset.order_by("-date_joined")


class UserInterestsView(generics.ListAPIView, generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserInterestSerializer  # Output serializer

    def get_queryset(self):
        return UserInterest.objects.filter(is_active=True).order_by("name")

    def update(self, request, *args, **kwargs):
        interests = request.data.get("interests", [])
        hobbies = request.data.get("hobbies", [])

        if not isinstance(interests, list) or not isinstance(hobbies, list):
            return Response(
                {"message": "Interests and hobbies must be arrays", "status": "error"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.interests = interests
        request.user.hobbies = hobbies
        request.user.save()

        return Response(
            {
                "message": "Interests updated successfully",
                "status": "success",
                "interests": request.user.interests,
                "hobbies": request.user.hobbies,
            },
            status=status.HTTP_200_OK,
        )


# =============================================================================
# CHAT AND MESSAGING VIEWS (NEW)
# =============================================================================


# --------------------------
# Chat Views
# --------------------------
class ChatListView(generics.ListCreateAPIView):
    """
    List all chats for the authenticated user or create a new chat.
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ChatCreateSerializer
        return ChatSerializer

    def get_queryset(self):
        user = self.request.user
        return (
            Chat.objects.filter(participants=user, is_active=True)
            .annotate(last_message_at=models.Max("messages__timestamp"))
            .order_by("-last_message_at")
        )

    def perform_create(self, serializer):
        chat = serializer.save(created_by=self.request.user)
        chat.participants.add(self.request.user)


class ChatDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or soft delete a specific chat.
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return ChatSettingsSerializer
        return ChatDetailSerializer

    def get_queryset(self):
        return Chat.objects.filter(participants=self.request.user, is_active=True)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


# --------------------------
# Message Views
# --------------------------
class MessageListView(generics.ListCreateAPIView):
    """
    List messages for a chat or send a new message (supports media and tips).
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return MessageCreateSerializer
        return MessageSerializer

    def get_queryset(self):
        chat = get_object_or_404(
            Chat,
            id=self.kwargs["chat_id"],
            participants=self.request.user,
            is_active=True,
        )
        # Mark unread messages as read
        Message.objects.filter(chat=chat, is_read=False).exclude(
            sender=self.request.user
        ).update(is_read=True, read_at=timezone.now())
        return Message.objects.filter(chat=chat).order_by("timestamp")

    def perform_create(self, serializer):
        user = self.request.user
        chat = get_object_or_404(
            Chat, id=self.kwargs["chat_id"], participants=user, is_active=True
        )

        # Handle uploaded files
        media_fields = {
            "voice_note_file": "voice_notes",
            "image_file": "chat_images",
            "video_file": "chat_videos",
            "document_file": "chat_documents",
        }

        media_urls = {}
        for field, folder in media_fields.items():
            file = self.request.FILES.get(field)
            if file:
                media_urls[field.replace("_file", "_url")] = self._save_file(
                    file, folder
                )
                serializer.validated_data["message_type"] = field.replace("_file", "")

        # Handle tip messages
        msg_type = serializer.validated_data.get("message_type", "text")
        tip_amount = serializer.validated_data.get("tip_amount", 0)
        if msg_type == "tip" and tip_amount > 0:
            if user.bondcoin_balance < tip_amount:
                raise serializers.ValidationError("Insufficient Bondcoins for this tip")
            recipient = chat.participants.exclude(id=user.id).first()
            if not recipient:
                raise serializers.ValidationError("No recipient found for this tip")
            # Deduct and credit Bondcoins
            user.bondcoin_balance -= tip_amount
            recipient.bondcoin_balance += tip_amount
            user.save()
            recipient.save()
            WalletTransaction.objects.create(
                user=user,
                tx_type="debit",
                amount=-tip_amount,
                status="completed",
                payment_method="bondcoin",
            )
            WalletTransaction.objects.create(
                user=recipient,
                tx_type="gift_received",
                amount=tip_amount,
                status="completed",
                payment_method="bondcoin",
            )

        serializer.save(chat=chat, sender=user, **media_urls)

    def _save_file(self, file, folder):
        ext = os.path.splitext(file.name)[1]
        filename = f"{uuid.uuid4()}{ext}"
        path = os.path.join(folder, filename)
        default_storage.save(path, ContentFile(file.read()))
        return default_storage.url(path)


class MessageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or soft-delete a message.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer

    def get_queryset(self):
        chat = get_object_or_404(
            Chat,
            id=self.kwargs["chat_id"],
            participants=self.request.user,
            is_active=True,
        )
        return Message.objects.filter(chat=chat)

    def perform_update(self, serializer):
        serializer.save(is_edited=True, edited_at=timezone.now())

    def perform_destroy(self, instance):
        instance.content = "[Message deleted]"
        instance.message_type = "system"
        instance.save()


class CallInitiateView(generics.CreateAPIView):
    """
    Initiate a voice or video call.
    """

    serializer_class = CallInitiateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        callee_id = serializer.validated_data["callee_id"]
        call_type = serializer.validated_data["call_type"]

        callee = get_object_or_404(User, id=callee_id, is_active=True)

        # Find or create chat
        chat = (
            Chat.objects.filter(participants=self.request.user, chat_type="direct")
            .filter(participants=callee)
            .annotate(participant_count=models.Count("participants"))
            .filter(participant_count=2)
            .first()
        )
        if not chat:
            chat = Chat.objects.create(chat_type="direct", created_by=self.request.user)
            chat.participants.set([self.request.user, callee])

        import uuid

        call_id = str(uuid.uuid4())
        room_id = f"room_{call_id}"

        call = Call.objects.create(
            chat=chat,
            caller=self.request.user,
            callee=callee,
            call_type=call_type,
            call_id=call_id,
            room_id=room_id,
            status="initiated",
        )

        # System message
        Message.objects.create(
            chat=chat,
            sender=None,
            message_type="call_start",
            content=f"{self.request.user.name} started a {call_type} call",
        )

        return call


class CallAnswerView(generics.UpdateAPIView):
    """
    Answer, decline, or mark a call as busy.
    """

    serializer_class = CallSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "call_id"

    def get_queryset(self):
        return Call.objects.filter(
            callee=self.request.user, status__in=["initiated", "ringing"]
        )

    def update(self, request, *args, **kwargs):
        call = self.get_object()
        action = request.data.get("action")

        if action == "answer":
            call.status = "active"
            call.answered_at = timezone.now()
            content = f"{request.user.name} answered the call"
            message_type = "call_start"

        elif action == "decline":
            call.status = "declined"
            call.ended_at = timezone.now()
            content = f"{request.user.name} declined the call"
            message_type = "call_end"

        elif action == "busy":
            call.status = "busy"
            call.ended_at = timezone.now()
            content = f"{request.user.name} is busy"
            message_type = "call_end"

        else:
            return Response(
                {"message": "Invalid action", "status": "error"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        call.save()

        # System message
        Message.objects.create(
            chat=call.chat,
            sender=None,
            message_type=message_type,
            content=content,
        )

        serializer = self.get_serializer(call)
        return Response(
            {
                "message": f"Call {action}ed successfully",
                "status": "success",
                "call": serializer.data,
            }
        )


class CallEndView(generics.UpdateAPIView):
    """
    End an active call.
    """

    serializer_class = CallSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "call_id"

    def get_queryset(self):
        # User must be a participant and call must be active
        return Call.objects.filter(status="active", participants=self.request.user)

    def update(self, request, *args, **kwargs):
        call = self.get_object()

        call.status = "ended"
        call.ended_at = timezone.now()
        if call.answered_at:
            call.duration = int((call.ended_at - call.answered_at).total_seconds())
        call.save()

        Message.objects.create(
            chat=call.chat,
            sender=None,
            message_type="call_end",
            content=f"Call ended. Duration: {call.get_duration_display()}",
        )

        serializer = self.get_serializer(call)
        return Response(
            {
                "message": "Call ended successfully",
                "status": "success",
                "call": serializer.data,
            }
        )


class ChatReportView(generics.CreateAPIView):
    """
    Report a chat, message, or user
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        from .serializers import ChatReportSerializer

        return ChatReportSerializer

    def perform_create(self, serializer):
        """Create report with current user as reporter"""
        chat_id = self.kwargs.get("chat_id")
        message_id = self.kwargs.get("message_id")

        if chat_id:
            chat = get_object_or_404(Chat, id=chat_id, participants=self.request.user)
            serializer.validated_data["chat"] = chat

        if message_id:
            message = get_object_or_404(Message, id=message_id)
            serializer.validated_data["message"] = message

        serializer.save(reporter=self.request.user)


class MatchmakerIntroView(generics.GenericAPIView):
    """
    Create a matchmaker introduction chat between two users
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ChatDetailSerializer

    @extend_schema(
        request=None,  # you can define an input serializer if you want docs for request body
        responses={
            201: ChatDetailSerializer,
            400: OpenApiResponse(description="Bad request"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="User not found"),
            500: OpenApiResponse(description="Server error"),
        },
    )
    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_matchmaker:
                return Response(
                    {
                        "message": "Only matchmakers can create introductions",
                        "status": "error",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            user1_id = request.data.get("user1_id")
            user2_id = request.data.get("user2_id")
            intro_message = request.data.get("intro_message", "")

            if not user1_id or not user2_id:
                return Response(
                    {
                        "message": "Both user1_id and user2_id are required",
                        "status": "error",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                user1 = User.objects.get(id=user1_id, is_active=True)
                user2 = User.objects.get(id=user2_id, is_active=True)

                # Check if chat already exists
                existing_chat = (
                    Chat.objects.filter(
                        participants=user1, chat_type="matchmaker_intro"
                    )
                    .filter(participants=user2)
                    .annotate(participant_count=models.Count("participants"))
                    .filter(participant_count=2)
                    .first()
                )

                if existing_chat:
                    return Response(
                        {
                            "message": "Introduction chat already exists",
                            "status": "error",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Create matchmaker introduction chat
                chat = Chat.objects.create(
                    chat_type="matchmaker_intro",
                    created_by=request.user,
                    chat_name=f"Introduction: {user1.name} & {user2.name}",
                )
                chat.participants.set([user1, user2, request.user])

                # Create system messages
                Message.objects.create(
                    chat=chat,
                    sender=None,
                    message_type="system",
                    content=f"{request.user.name} (moderator) made the match",
                )
                Message.objects.create(
                    chat=chat,
                    sender=None,
                    message_type="system",
                    content=f"{user1.name} was matched",
                )
                Message.objects.create(
                    chat=chat,
                    sender=None,
                    message_type="system",
                    content=f"{user2.name} was added",
                )

                # Create matchmaker introduction message
                intro_content = (
                    intro_message
                    or f"Hi {user1.name} & {user2.name} 👋, I've matched you because I see a good fit. Please introduce yourselves and get to know each other."
                )

                Message.objects.create(
                    chat=chat,
                    sender=request.user,
                    message_type="matchmaker_intro",
                    content=intro_content,
                )

                return Response(
                    {
                        "message": "Matchmaker introduction created successfully",
                        "status": "success",
                        "chat": self.get_serializer(
                            chat, context={"request": request}
                        ).data,
                    },
                    status=status.HTTP_201_CREATED,
                )

            except User.DoesNotExist:
                return Response(
                    {"message": "One or both users not found", "status": "error"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        except Exception as e:
            return Response(
                {
                    "message": f"An unexpected error occurred: {str(e)}",
                    "status": "error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# =============================================================================
# LIVE SESSION VIEWS (NEW)
# =============================================================================


class LiveSessionListView(generics.ListCreateAPIView):
    """
    List active live sessions or create a new live session
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            from .serializers import LiveSessionCreateSerializer

            return LiveSessionCreateSerializer
        from .serializers import LiveSessionSerializer

        return LiveSessionSerializer

    def get_queryset(self):
        from .models import LiveSession
        from django.utils import timezone

        # Get active live sessions
        return (
            LiveSession.objects.filter(
                status="active",
                start_time__gte=timezone.now()
                - timezone.timedelta(hours=24),  # Only recent sessions
            )
            .select_related("user")
            .order_by("-start_time")
        )

    def perform_create(self, serializer):
        """Create live session with current user"""
        serializer.save(user=self.request.user)


class LiveSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or end a specific live session
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return LiveSessionSerializer

    def get_queryset(self):
        return LiveSession.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        """End the live session instead of deleting"""

        instance.status = "ended"
        instance.end_time = timezone.now()
        instance.save()


class LiveSessionJoinView(generics.CreateAPIView):
    """
    Join a live session as a viewer
    """

    permission_classes = [IsAuthenticated]
    serializer_class = LiveParticipantSerializer

    def create(self, request, session_id):
        try:
            session = LiveSession.objects.get(id=session_id, status="active")

            # Check if user is already a participant
            participant, created = LiveParticipant.objects.get_or_create(
                session=session, user=request.user, defaults={"role": "viewer"}
            )

            if created:
                # Update viewers count
                session.viewers_count += 1
                session.save(update_fields=["viewers_count"])

                serializer = self.get_serializer(participant)
                return Response(
                    {
                        "message": "Successfully joined live session",
                        "status": "success",
                        "participant_id": participant.id,
                        "data": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                serializer = self.get_serializer(participant)
                return Response(
                    {
                        "message": "Already participating in this session",
                        "status": "info",
                        "data": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )

        except LiveSession.DoesNotExist:
            return Response(
                {"message": "Live session not found or not active", "status": "error"},
                status=status.HTTP_404_NOT_FOUND,
            )


class LiveSessionLeaveView(generics.GenericAPIView):
    """
    Leave a live session
    """

    permission_classes = [IsAuthenticated]
    serializer_class = LiveParticipantSerializer  # For schema purposes

    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(
                response=LiveParticipantSerializer,
                description="Successfully left the live session",
            ),
            404: OpenApiResponse(description="Live session or participation not found"),
        },
    )
    def post(self, request, session_id, *args, **kwargs):
        # Get the live session
        session = get_object_or_404(LiveSession, id=session_id)

        # Get the participant record
        participant = get_object_or_404(
            LiveParticipant, session=session, user=request.user, left_at__isnull=True
        )

        # Mark as left
        participant.left_at = timezone.now()
        participant.save()

        # Update viewers count safely
        session.viewers_count = max(0, session.viewers_count - 1)
        session.save(update_fields=["viewers_count"])

        return Response(
            {"message": "Successfully left live session", "status": "success"},
            status=status.HTTP_200_OK,
        )


# =============================================================================
# SOCIAL FEED AND STORY VIEWS (NEW)
# =============================================================================


class FeedListView(generics.ListCreateAPIView):
    """
    List posts in the Bond Story feed or create a new post
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    queryset = (
        Post.objects.filter(is_active=True, visibility="public")
        .select_related("author")
        .prefetch_related("comments__author")
        .order_by("-created_at")
    )

    # Use static serializer to satisfy drf-spectacular
    serializer_class = PostSerializer

    @extend_schema(
        request=PostCreateSerializer,
        responses={
            200: OpenApiResponse(PostSerializer),
            201: OpenApiResponse(PostSerializer),
        },
    )
    def post(self, request, *args, **kwargs):
        """Handle post creation with file uploads"""
        serializer = PostCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        image_files = request.FILES.getlist("image_files")
        video_file = request.FILES.get("video_file")

        image_urls = []
        video_url = None
        video_thumbnail = None

        if image_files:
            for image_file in image_files:
                image_urls.append(self._save_uploaded_file(image_file, "post_images"))

        if video_file:
            video_url = self._save_uploaded_file(video_file, "post_videos")
            video_thumbnail = video_url.replace(
                ".mp4", "_thumb.jpg"
            )  # placeholder thumbnail logic

        serializer.save(
            author=request.user,
            image_urls=image_urls,
            video_url=video_url,
            video_thumbnail=video_thumbnail,
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _save_uploaded_file(self, file, folder):
        """Save uploaded file and return URL"""

        ext = os.path.splitext(file.name)[1]
        filename = f"{uuid.uuid4()}{ext}"
        filepath = os.path.join(folder, filename)

        default_storage.save(filepath, ContentFile(file.read()))
        return default_storage.url(filepath)


class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific post
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            from .serializers import PostCreateSerializer

            return PostCreateSerializer
        from .serializers import PostSerializer

        return PostSerializer

    def get_queryset(self):
        from .models import Post

        return (
            Post.objects.filter(is_active=True)
            .select_related("author")
            .prefetch_related("comments__author")
        )

    def perform_destroy(self, instance):
        """Soft delete post by deactivating it"""
        instance.is_active = False
        instance.save()


class PostCommentListView(generics.ListCreateAPIView):
    """
    List comments for a specific post or add a new comment
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PostCommentSerializer  # Static serializer for drf-spectacular

    def get_queryset(self):
        post_id = self.kwargs["post_id"]

        # Ensure the post exists and is active
        post = get_object_or_404(Post, id=post_id, is_active=True)

        return (
            PostComment.objects.filter(
                post=post,
                is_active=True,
                parent_comment__isnull=True,  # Only top-level comments
            )
            .select_related("author")
            .prefetch_related("replies__author")
            .order_by("created_at")
        )

    @extend_schema(
        request=PostCommentSerializer,
        responses={
            201: OpenApiResponse(PostCommentSerializer),
        },
    )
    def post(self, request, *args, **kwargs):
        """Create a new comment for a post"""
        post_id = self.kwargs["post_id"]
        post = get_object_or_404(Post, id=post_id, is_active=True)

        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(post=post, author=request.user)

        # Update post comments count
        post.comments_count = post.comments.filter(is_active=True).count()
        post.save(update_fields=["comments_count"])

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PostInteractionView(generics.CreateAPIView):
    """
    Handle post interactions (like, share, bond)
    """
    serializer_class = PostInteractionSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        post_id = self.kwargs.get("post_id")
        try:
            post = Post.objects.get(id=post_id, is_active=True)
            interaction_type = request.data.get("interaction_type")

            if interaction_type not in ["like", "share", "bond", "save"]:
                return Response(
                    {"message": "Invalid interaction type", "status": "error"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if interaction already exists
            interaction, created = PostInteraction.objects.get_or_create(
                user=request.user, post=post, interaction_type=interaction_type
            )

            if not created:
                # Remove interaction (toggle)
                interaction.delete()
                action = "removed"

                # Update post counts
                if interaction_type == "like":
                    post.likes_count = max(0, post.likes_count - 1)
                elif interaction_type == "share":
                    post.shares_count = max(0, post.shares_count - 1)
                elif interaction_type == "bond":
                    post.bonds_count = max(0, post.bonds_count - 1)
            else:
                # Add interaction
                action = "added"

                # Update post counts
                if interaction_type == "like":
                    post.likes_count += 1
                elif interaction_type == "share":
                    post.shares_count += 1
                elif interaction_type == "bond":
                    post.bonds_count += 1

            post.save(update_fields=["likes_count", "shares_count", "bonds_count"])

            return Response(
                {
                    "message": f"Interaction {action} successfully",
                    "status": "success",
                    "interaction_type": interaction_type,
                    "action": action,
                },
                status=status.HTTP_200_OK,
            )

        except Post.DoesNotExist:
            return Response(
                {"message": "Post not found", "status": "error"},
                status=status.HTTP_404_NOT_FOUND,
            )


class CommentInteractionView(generics.CreateAPIView):
    """
    Handle comment interactions (like)
    """
    serializer_class = CommentInteractionSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        comment_id = self.kwargs.get("comment_id")
        try:
            comment = PostComment.objects.get(id=comment_id, is_active=True)
            interaction_type = request.data.get("interaction_type", "like")

            # Check if interaction already exists
            interaction, created = CommentInteraction.objects.get_or_create(
                user=request.user, comment=comment, interaction_type=interaction_type
            )

            if not created:
                # Remove interaction (toggle)
                interaction.delete()
                action = "removed"
                comment.likes_count = max(0, comment.likes_count - 1)
            else:
                # Add interaction
                action = "added"
                comment.likes_count += 1

            comment.save(update_fields=["likes_count"])

            return Response(
                {
                    "message": f"Comment interaction {action} successfully",
                    "status": "success",
                    "interaction_type": interaction_type,
                    "action": action,
                },
                status=status.HTTP_200_OK,
            )

        except PostComment.DoesNotExist:
            return Response(
                {"message": "Comment not found", "status": "error"},
                status=status.HTTP_404_NOT_FOUND,
            )


class PostReportView(generics.CreateAPIView):
    """
    Report a post or comment
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        from .serializers import PostReportSerializer

        return PostReportSerializer

    def perform_create(self, serializer):
        """Create report with current user as reporter"""
        post_id = self.kwargs.get("post_id")
        comment_id = self.kwargs.get("comment_id")

        if post_id:
            from .models import Post

            post = get_object_or_404(Post, id=post_id, is_active=True)
            serializer.validated_data["post"] = post
            serializer.validated_data["reported_user"] = post.author

        if comment_id:
            from .models import PostComment

            comment = get_object_or_404(PostComment, id=comment_id, is_active=True)
            serializer.validated_data["comment"] = comment
            serializer.validated_data["reported_user"] = comment.author

        serializer.save(reporter=self.request.user)


class PostShareView(generics.CreateAPIView):
    """
    Share a post to external platforms
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PostShareSerializer

    def perform_create(self, serializer):
        """Create share with current user and post"""
        post_id = self.kwargs["post_id"]
        post = get_object_or_404(Post, id=post_id, is_active=True)

        serializer.save(user=self.request.user, post=post)

        # Update post shares count
        post.shares_count += 1
        post.save(update_fields=["shares_count"])


class StoryListView(generics.ListCreateAPIView):
    """
    List active stories or create a new story
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return StoryCreateSerializer
        return StorySerializer

    def get_queryset(self):
        # Get active, non-expired stories
        return (
            Story.objects.filter(is_active=True, expires_at__gt=timezone.now())
            .select_related("author")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        """Create story with current user as author"""
        # Handle file uploads for images and videos
        image_file = self.request.FILES.get("image_file")
        video_file = self.request.FILES.get("video_file")

        # Save uploaded files and get URLs
        image_url = None
        video_url = None

        if image_file:
            image_url = self._save_uploaded_file(image_file, "story_images")

        if video_file:
            video_url = self._save_uploaded_file(video_file, "story_videos")

        serializer.save(
            author=self.request.user, image_url=image_url, video_url=video_url
        )

    def _save_uploaded_file(self, file, folder):
        """Save uploaded file and return URL"""
        # Generate unique filename
        file_extension = os.path.splitext(file.name)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(folder, unique_filename)

        # Save file
        default_storage.save(file_path, ContentFile(file.read()))
        return default_storage.url(file_path)


class StoryDetailView(generics.RetrieveAPIView):
    """
    Retrieve a specific story and mark as viewed
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return StorySerializer

    def get_queryset(self):
        return Story.objects.filter(
            is_active=True, expires_at__gt=timezone.now()
        ).select_related("author")

    def retrieve(self, request, *args, **kwargs):
        """Mark story as viewed by current user"""
        story = self.get_object()

        # Mark as viewed if not already viewed
        StoryView.objects.get_or_create(story=story, viewer=request.user)

        # Update views count
        story.views_count = story.views.count()
        story.save(update_fields=["views_count"])

        serializer = self.get_serializer(story)
        return Response(serializer.data)


class StoryReactionView(generics.CreateAPIView):
    """
    Handle story reactions
    """
    serializer_class = StoryReactionSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        story_id = self.kwargs.get("story_id")
        try:
            story = Story.objects.get(id=story_id, is_active=True)
            reaction_type = request.data.get("reaction_type", "like")

            if reaction_type not in ["like", "love", "laugh", "wow", "sad", "angry"]:
                return Response(
                    {"message": "Invalid reaction type", "status": "error"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if reaction already exists
            reaction, created = StoryReaction.objects.get_or_create(
                user=request.user, story=story, reaction_type=reaction_type
            )

            if not created:
                # Remove reaction (toggle)
                reaction.delete()
                action = "removed"
                story.reactions_count = max(0, story.reactions_count - 1)
            else:
                # Add reaction
                action = "added"
                story.reactions_count += 1

            story.save(update_fields=["reactions_count"])

            return Response(
                {
                    "message": f"Story reaction {action} successfully",
                    "status": "success",
                    "reaction_type": reaction_type,
                    "action": action,
                },
                status=status.HTTP_200_OK,
            )

        except Story.DoesNotExist:
            return Response(
                {"message": "Story not found", "status": "error"},
                status=status.HTTP_404_NOT_FOUND,
            )


class FeedSearchView(generics.ListAPIView):
    """
    Search posts in the Bond Story feed
    """

    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        query = self.request.GET.get("q", "").strip()
        if not query:
            return Post.objects.none()

        # Search posts by content, hashtags, and author name
        return (
            Post.objects.filter(
                Q(content__icontains=query)
                | Q(hashtags__icontains=query)
                | Q(author__name__icontains=query)
                | Q(location__icontains=query),
                is_active=True,
                visibility="public",
            )
            .select_related("author")
            .prefetch_related("comments__author")
            .order_by("-created_at")
        )

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            query = self.request.GET.get("q", "").strip()

            # Store search query for analytics
            FeedSearch.objects.create(
                user=request.user, query=query, results_count=queryset.count()
            )

            # Use paginated response if needed, otherwise standard list
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {
                    "message": "Search completed successfully",
                    "status": "success",
                    "query": query,
                    "results_count": queryset.count(),
                    "posts": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {
                    "message": f"An unexpected error occurred during search: {str(e)}",
                    "status": "error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(responses=FeedSuggestionsResponseSerializer)
class FeedSuggestionsView(generics.ListAPIView):
    """
    Get search suggestions for the Bond Story feed
    """

    permission_classes = [IsAuthenticated]
    serializer_class = FeedSuggestionsResponseSerializer

    def get_queryset(self):
        # Required by ListAPIView but unused
        return FeedSearch.objects.none()

    def list(self, request, *args, **kwargs):
        from .models import FeedSearch, Post
        from django.db.models import Count

        query = request.GET.get("q", "").strip()

        if query:
            suggestions = (
                FeedSearch.objects.filter(query__icontains=query)
                .values("query")
                .annotate(count=Count("query"))
                .order_by("-count")[:5]
            )

            hashtag_suggestions = Post.objects.filter(
                hashtags__icontains=query, is_active=True
            ).values_list("hashtags", flat=True)

            all_hashtags = []
            for hashtags in hashtag_suggestions:
                if hashtags:
                    all_hashtags.extend(hashtags)

            filtered_hashtags = [
                tag for tag in set(all_hashtags) if query.lower() in tag.lower()
            ]

            return Response(
                FeedSuggestionsResponseSerializer(
                    {
                        "message": "Suggestions retrieved successfully",
                        "status": "success",
                        "suggestions": [s["query"] for s in suggestions],
                        "hashtags": filtered_hashtags[:5],
                    }
                ).data
            )
        else:
            popular_searches = (
                FeedSearch.objects.values("query")
                .annotate(count=Count("query"))
                .order_by("-count")[:10]
            )

            return Response(
                FeedSuggestionsResponseSerializer(
                    {
                        "message": "Popular searches retrieved successfully",
                        "status": "success",
                        "popular_searches": [s["query"] for s in popular_searches],
                    }
                ).data
            )


# =============================================================================
# SOCIAL MEDIA HANDLES VIEWS (NEW FROM FIGMA)
# =============================================================================


class UserSocialHandleListView(generics.ListCreateAPIView):
    """
    List and create user social media handles
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":

            return UserSocialHandleCreateSerializer

        return UserSocialHandleSerializer

    def get_queryset(self):

        return UserSocialHandle.objects.filter(user=self.request.user)


class UserSocialHandleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific social media handle
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):

        return UserSocialHandleSerializer

    def get_queryset(self):

        return UserSocialHandle.objects.filter(user=self.request.user)


# =============================================================================
# SECURITY QUESTIONS VIEWS (NEW FROM FIGMA)
# =============================================================================


class UserSecurityQuestionListView(generics.ListCreateAPIView):
    """
    List and create user security question responses
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":

            return UserSecurityQuestionCreateSerializer

        return UserSecurityQuestionSerializer

    def get_queryset(self):

        return UserSecurityQuestion.objects.filter(user=self.request.user)


class UserSecurityQuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific security question response
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return UserSecurityQuestionSerializer

    def get_queryset(self):
        from .models import UserSecurityQuestion

        return UserSecurityQuestion.objects.filter(user=self.request.user)


# =============================================================================
# DOCUMENT VERIFICATION VIEWS (NEW FROM FIGMA)
# =============================================================================


class DocumentVerificationListView(generics.ListCreateAPIView):
    """
    List and create document verification requests
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":

            return DocumentVerificationCreateSerializer

        return DocumentVerificationSerializer

    def get_queryset(self):

        return DocumentVerification.objects.filter(user=self.request.user)


class DocumentVerificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific document verification
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        from .serializers import DocumentVerificationSerializer

        return DocumentVerificationSerializer

    def get_queryset(self):
        from .models import DocumentVerification

        return DocumentVerification.objects.filter(user=self.request.user)


class DocumentUploadView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DocumentVerificationCreateSerializer

    def post(self, request):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        verification, _ = DocumentVerification.objects.get_or_create(
            user=request.user,
            status="pending",
        )

        for field, value in serializer.validated_data.items():
            setattr(verification, field, value)

        verification.save()

        return Response(
            {
                "message": "Document uploaded. Awaiting admin review.",
                "status": "success",
                "verification_id": verification.id,
            },
            status=201,
        )


# =============================================================================
# USERNAME VALIDATION VIEWS (NEW FROM FIGMA)
# =============================================================================


class UsernameValidationView(APIView):
    """
    Validate username availability and format
    """

    permission_classes = [AllowAny]

    @extend_schema(
        request=UsernameValidationSerializer,
        responses={
            200: inline_serializer(
                name="UsernameValidationResponse",
                fields={
                    "message": serializers.CharField(),
                    "status": serializers.CharField(),
                    "data": UsernameValidationSerializer(),
                },
            ),
            400: inline_serializer(
                name="UsernameValidationError",
                fields={
                    "message": serializers.CharField(),
                    "status": serializers.CharField(),
                    "errors": serializers.DictField(),
                },
            ),
            500: inline_serializer(
                name="UsernameValidationServerError",
                fields={
                    "message": serializers.CharField(),
                    "status": serializers.CharField(),
                },
            ),
        },
    )
    def post(self, request):
        """Validate username"""
        try:

            serializer = UsernameValidationSerializer(data=request.data)
            if serializer.is_valid():
                return Response(
                    {
                        "message": "Username validation completed",
                        "status": "success",
                        "data": serializer.validated_data,
                    },
                    status=status.HTTP_200_OK,
                )

            return Response(
                {
                    "message": "Invalid data provided",
                    "status": "error",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return Response(
                {
                    "message": f"Failed to validate username: {str(e)}",
                    "status": "error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UsernameUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UsernameUpdateSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            self.get_object(), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "message": "Username updated successfully",
                "status": "success",
                "username": user.username,
            }
        )


# =============================================================================
# SUBSCRIPTION PLANS VIEWS (NEW FROM FIGMA)
# =============================================================================


class SubscriptionPlanListView(generics.ListAPIView):
    """
    List all available subscription plans
    """

    permission_classes = [AllowAny]

    def get_serializer_class(self):

        return SubscriptionPlanSerializer

    def get_queryset(self):

        return SubscriptionPlan.objects.filter(is_active=True)


class UserSubscriptionListView(generics.ListCreateAPIView):
    """
    List and create user subscriptions
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":

            return UserSubscriptionCreateSerializer

        return UserSubscriptionSerializer

    def get_queryset(self):

        return UserSubscription.objects.filter(user=self.request.user)


class UserSubscriptionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific user subscription
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):

        return UserSubscriptionSerializer

    def get_queryset(self):

        return UserSubscription.objects.filter(user=self.request.user)


class UserCurrentSubscriptionView(generics.RetrieveAPIView):
    """
    Get user's current active subscription
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserSubscriptionSerializer

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=UserSubscriptionSerializer,
                description="Current subscription retrieved successfully",
            ),
            200: OpenApiResponse(description="No active subscription found"),
            500: OpenApiResponse(description="Server error"),
        }
    )
    def get(self, request, *args, **kwargs):
        subscription = request.user.get_current_subscription()
        if subscription:
            serializer = self.get_serializer(subscription)
            return Response(
                {
                    "message": "Current subscription retrieved",
                    "status": "success",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {
                "message": "No active subscription found",
                "status": "info",
                "data": None,
            },
            status=status.HTTP_200_OK,
        )


class UserFeatureAccessView(generics.GenericAPIView):
    """
    Check user's access to specific features
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="feature",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Feature name to check access",
            ),
        ],
        responses={
            200: OpenApiResponse(description="Feature access checked successfully"),
            400: OpenApiResponse(description="Feature name is missing"),
            500: OpenApiResponse(description="Server error"),
        },
    )
    def get(self, request, *args, **kwargs):
        feature_name = request.query_params.get("feature")
        if not feature_name:
            return Response(
                {"message": "Feature name is required", "status": "error"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        has_access = request.user.has_feature_access(feature_name)

        return Response(
            {
                "message": "Feature access checked",
                "status": "success",
                "feature": feature_name,
                "has_access": has_access,
            },
            status=status.HTTP_200_OK,
        )


# =============================================================================
# BONDCOIN WALLET VIEWS (NEW FROM FIGMA)
# =============================================================================


class BondcoinPackageListView(generics.ListAPIView):
    """
    List all active Bondcoin packages available for purchase
    """

    serializer_class = BondcoinPackageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BondcoinPackage.objects.filter(is_active=True).order_by(
            "bondcoin_amount"
        )


class BondcoinTransactionListView(generics.ListAPIView):
    """
    List user's Bondcoin transactions
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):

        return WalletTransactionSerializer

    def get_queryset(self):

        return WalletTransaction.objects.filter(user=self.request.user)


# class BondcoinTransactionDetailView(generics.RetrieveAPIView):
#     """
#     Retrieve a specific Bondcoin transaction
#     """

#     permission_classes = [IsAuthenticated]

#     def get_serializer_class(self):

#         return BondcoinTransactionSerializer

#     def get_queryset(self):
#         return BondcoinTransaction.objects.filter(user=self.request.user)


# =============================================================================
# VIRTUAL GIFTING VIEWS (NEW FROM FIGMA)
# =============================================================================


class GiftCategoryListView(generics.ListAPIView):
    """
    List all gift categories
    """

    permission_classes = [AllowAny]

    def get_serializer_class(self):
        from .serializers import GiftCategorySerializer

        return GiftCategorySerializer

    def get_queryset(self):
        from .models import GiftCategory

        return GiftCategory.objects.filter(is_active=True)


class VirtualGiftListView(generics.ListAPIView):
    """
    List virtual gifts, optionally filtered by category
    """

    permission_classes = [AllowAny]

    def get_serializer_class(self):
        from .serializers import VirtualGiftSerializer

        return VirtualGiftSerializer

    def get_queryset(self):
        from .models import VirtualGift

        queryset = VirtualGift.objects.filter(is_active=True)

        category_id = self.request.query_params.get("category")
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        return queryset


class VirtualGiftDetailView(generics.RetrieveAPIView):
    """
    Retrieve a specific virtual gift
    """
    permission_classes = [AllowAny]
    serializer_class = VirtualGiftSerializer

    def get_queryset(self):
        return VirtualGift.objects.filter(is_active=True)


class SendGiftView(generics.GenericAPIView):
    serializer_class = SendGiftSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        receiver_id = serializer.validated_data["receiver_id"]
        gift_id = serializer.validated_data["gift_id"]
        user = request.user
        receiver = User.objects.get(id=receiver_id)

        try:
            send_gift(user, receiver, gift_id)
        except ValidationError as e:
            return Response({"Failed to send gift": str(e)}, status=400)

        return Response({"message": "Gift sent successfully"}, status=201)


# Convert Gift Cards
class ConvertGiftView(generics.GenericAPIView):
    serializer_class = ConvertGiftSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        gift_id = serializer.validated_data["gift_id"]
        user = request.user

        try:
            convert_gift_to_coins(user, gift_id)
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)

        return Response({"message": "Gift converted to coins successfully"}, status=201)

# =============================================================================
# LIVE STREAMING ENHANCEMENT VIEWS (NEW FROM FIGMA)
# =============================================================================


class LiveGiftListView(generics.ListCreateAPIView):
    """
    List and send gifts in live sessions
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            from .serializers import LiveGiftCreateSerializer

            return LiveGiftCreateSerializer
        from .serializers import LiveGiftSerializer

        return LiveGiftSerializer

    def get_queryset(self):
        from .models import LiveGift

        session_id = self.request.query_params.get("session_id")
        if session_id:
            return LiveGift.objects.filter(session_id=session_id)
        return LiveGift.objects.none()


class LiveJoinRequestListView(generics.ListCreateAPIView):
    """
    List and create live session join requests
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            from .serializers import LiveJoinRequestCreateSerializer

            return LiveJoinRequestCreateSerializer
        from .serializers import LiveJoinRequestSerializer

        return LiveJoinRequestSerializer

    def get_queryset(self):
        from .models import LiveJoinRequest

        session_id = self.request.query_params.get("session_id")
        if session_id:
            return LiveJoinRequest.objects.filter(session_id=session_id)
        return LiveJoinRequest.objects.filter(requester=self.request.user)


class LiveJoinRequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific live join request
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        from .serializers import LiveJoinRequestSerializer

        return LiveJoinRequestSerializer

    def get_queryset(self):
        from .models import LiveJoinRequest

        return LiveJoinRequest.objects.filter(requester=self.request.user)


class LiveJoinRequestManageView(generics.UpdateAPIView):
    """
    Manage live session join requests (for hosts to approve/reject)
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        from .serializers import LiveJoinRequestManageSerializer

        return LiveJoinRequestManageSerializer

    def get_queryset(self):
        from .models import LiveJoinRequest

        # Only allow hosts to manage requests for their sessions
        return LiveJoinRequest.objects.filter(session__user=self.request.user)


class LiveSessionGiftersView(generics.ListAPIView):
    """
    Get top gifters for a live session
    """

    permission_classes = [AllowAny]
    serializer_class = LiveGiftSerializer  # for Swagger/schema generation

    def get_queryset(self):
        session_id = self.kwargs.get("session_id")
        session = get_object_or_404(LiveSession, id=session_id)
        return LiveGift.objects.filter(session=session)

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=LiveGiftSerializer(many=True),
                description="Top gifters retrieved successfully",
            ),
            404: OpenApiResponse(description="Live session not found"),
        }
    )
    def list(self, request, *args, **kwargs):
        session_id = self.kwargs.get("session_id")
        session = get_object_or_404(LiveSession, id=session_id)

        # Aggregate top gifters
        gifters = (
            LiveGift.objects.filter(session=session)
            .values("sender__id", "sender__name", "sender__profile_picture")
            .annotate(total_gifts=Sum("total_cost"))
            .order_by("-total_gifts")[:10]
        )

        return Response(
            {
                "message": "Top gifters retrieved",
                "status": "success",
                "data": list(gifters),
            },
            status=status.HTTP_200_OK,
        )


# Payment Processing Views
class PaymentMethodListView(generics.ListAPIView):
    """List available payment methods"""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        from .serializers import PaymentMethodSerializer

        return PaymentMethodSerializer

    def get_queryset(self):
        return PaymentMethod.objects.filter(is_active=True)


class PaymentTransactionListView(generics.ListAPIView):
    """List user's payment transactions"""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        from .serializers import PaymentTransactionSerializer

        return PaymentTransactionSerializer

    def get_queryset(self):
        from .models import PaymentTransaction

        return PaymentTransaction.objects.filter(user=self.request.user)


class PaymentTransactionDetailView(generics.RetrieveAPIView):
    """Retrieve a specific payment transaction"""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        from .serializers import PaymentTransactionSerializer

        return PaymentTransactionSerializer

    def get_queryset(self):
        from .models import PaymentTransaction

        return PaymentTransaction.objects.filter(user=self.request.user)


class ProcessPaymentView(generics.GenericAPIView):
    """
    Process payment for subscriptions or Bondcoin purchases
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PaymentTransactionCreateSerializer

    @extend_schema(
        request=PaymentTransactionCreateSerializer,
        responses={201: PaymentTransactionSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        transaction_type = validated_data["transaction_type"]
        payment_method = validated_data["payment_method"]
        amount_usd = validated_data["amount_usd"]

        payment_transaction = PaymentTransaction.objects.create(
            user=request.user,
            transaction_type=transaction_type,
            payment_method=payment_method,
            amount_usd=amount_usd,
            processing_fee=validated_data.get("processing_fee", Decimal("0.00")),
            total_amount=validated_data.get("total_amount", amount_usd),
            currency=validated_data.get("currency", "USD"),
            description=validated_data.get("description", ""),
            metadata=validated_data.get("metadata", {}),
            status="pending",
        )

        # Process subscription or Bondcoin purchase
        if transaction_type == "subscription":
            subscription_id = validated_data.get("subscription")
            if subscription_id:
                subscription = UserSubscription.objects.get(
                    id=subscription_id, user=request.user
                )
                payment_transaction.subscription = subscription
                payment_transaction.save()

                subscription.status = "active"
                subscription.save()

                # Update user's Bondcoin balance
                BondcoinTransaction.objects.create(
                    user=request.user,
                    transaction_type="subscription",
                    amount=-subscription.plan.price_bondcoins,
                    subscription=subscription,
                    payment_method="external_payment",
                    description=f"Subscription: {subscription.plan.display_name}",
                    status="completed",
                )
                request.user.bondcoin_balance -= subscription.plan.price_bondcoins
                request.user.save(update_fields=["bondcoin_balance"])

        elif transaction_type == "bondcoin_purchase":
            bondcoin_transaction_id = validated_data.get("bondcoin_transaction")
            if bondcoin_transaction_id:
                bondcoin_transaction = BondcoinTransaction.objects.get(
                    id=bondcoin_transaction_id, user=request.user
                )
                payment_transaction.bondcoin_transaction = bondcoin_transaction
                payment_transaction.save()

                bondcoin_transaction.status = "completed"
                bondcoin_transaction.save()

                request.user.bondcoin_balance += bondcoin_transaction.amount
                request.user.save(update_fields=["bondcoin_balance"])

        # Simulate payment processing
        payment_transaction.status = "processing"
        payment_transaction.save()
        time.sleep(1)  # simulate delay
        payment_transaction.status = "completed"
        payment_transaction.processed_at = timezone.now()
        payment_transaction.provider = "stripe"
        payment_transaction.provider_transaction_id = (
            f"txn_{payment_transaction.id}_{int(timezone.now().timestamp())}"
        )
        payment_transaction.save()

        return Response(
            {
                "message": "Payment processed successfully",
                "status": "success",
                "data": PaymentTransactionSerializer(payment_transaction).data,
            },
            status=status.HTTP_201_CREATED,
        )


class PaymentWebhookView(generics.GenericAPIView):
    """
    Handle payment webhooks from external providers
    """

    permission_classes = [AllowAny]

    @extend_schema(
        request=PaymentWebhookSerializer, responses={200: PaymentWebhookSerializer}
    )
    def post(self, request, provider, *args, **kwargs):
        payload = request.data
        event_id = payload.get("id", f"webhook_{int(timezone.now().timestamp())}")
        event_type = payload.get("type", "unknown")

        webhook = PaymentWebhook.objects.create(
            provider=provider,
            event_type=event_type,
            event_id=event_id,
            payload=payload,
        )

        # Example: handle Stripe
        if provider == "stripe":
            self._process_stripe_webhook(webhook, payload)
        elif provider == "paypal":
            self._process_paypal_webhook(webhook, payload)

        webhook.processed = True
        webhook.processed_at = timezone.now()
        webhook.save()

        return Response(
            {"message": "Webhook processed", "status": "success"}, status=200
        )

    def _process_stripe_webhook(self, webhook, event_data):
        event_type = event_data.get("type")
        # implement actual logic here
        pass

    def _process_paypal_webhook(self, webhook, event_data):
        event_type = event_data.get("event_type")
        # implement actual logic here
        pass


class RefundPaymentView(generics.GenericAPIView):
    """
    Process refund for a payment transaction
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PaymentTransactionSerializer

    @extend_schema(responses={201: PaymentTransactionSerializer})
    def post(self, request, transaction_id, *args, **kwargs):
        transaction = PaymentTransaction.objects.get(
            id=transaction_id, user=request.user, status="completed"
        )

        refund_transaction = PaymentTransaction.objects.create(
            user=request.user,
            transaction_type="refund",
            payment_method=transaction.payment_method,
            amount_usd=transaction.amount_usd,
            processing_fee=Decimal("0.00"),
            total_amount=transaction.amount_usd,
            currency=transaction.currency,
            description=f"Refund for transaction {transaction.id}",
            status="completed",
            processed_at=timezone.now(),
        )

        # Update original transaction
        transaction.status = "refunded"
        transaction.save()

        # Reverse effects
        if transaction.transaction_type == "subscription" and transaction.subscription:
            transaction.subscription.status = "cancelled"
            transaction.subscription.save()
            request.user.bondcoin_balance += (
                transaction.subscription.plan.price_bondcoins
            )
            request.user.save(update_fields=["bondcoin_balance"])
        elif (
            transaction.transaction_type == "bondcoin_purchase"
            and transaction.bondcoin_transaction
        ):
            request.user.bondcoin_balance -= transaction.bondcoin_transaction.amount
            request.user.save(update_fields=["bondcoin_balance"])

        return Response(
            {
                "message": "Refund processed successfully",
                "status": "success",
                "data": PaymentTransactionSerializer(refund_transaction).data,
            },
            status=status.HTTP_201_CREATED,
        )


# Firebase Integration Views
# These views integrate Firebase Auth and Firestore for
# user authentication, profiles, and matches.


class FirebaseLoginView(generics.GenericAPIView):
    """
    Authenticate user with Firebase ID token.
    Returns Django JWT tokens.
    """

    permission_classes = [AllowAny]
    serializer_class = UserSerializer

    @extend_schema(request=None, responses={200: UserSerializer})
    def post(self, request, *args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response(
                {"error": "Missing or invalid Authorization header"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        id_token = auth_header.split(" ")[1]
        decoded_token = verify_firebase_token(id_token)
        if not decoded_token:
            return Response(
                {"error": "Invalid Firebase token"}, status=status.HTTP_401_UNAUTHORIZED
            )

        user = get_or_create_user_from_firebase(decoded_token)

        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Login successful",
                "user": UserSerializer(user).data,
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
            }
        )


class FirebaseUserProfileView(generics.GenericAPIView):
    """
    Get or update user profile in Firestore.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def _get_uid(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        id_token = auth_header.split(" ")[1]
        decoded_token = verify_firebase_token(id_token)
        if not decoded_token:
            return None
        return decoded_token["uid"]

    def get(self, request, *args, **kwargs):
        uid = self._get_uid(request)
        if not uid:
            return Response(
                {"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED
            )

        profile = get_user_profile_from_firestore(uid)
        if not profile:
            return Response(
                {"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(profile)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        uid = self._get_uid(request)
        if not uid:
            return Response(
                {"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        success = update_user_profile_in_firestore(uid, serializer.validated_data)
        if success:
            return Response({"message": "Profile updated"})
        return Response(
            {"error": "Update failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class FirebaseMatchView(generics.GenericAPIView):
    """
    Create a match between users.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = FirebaseMatchSerializer

    def post(self, request, *args, **kwargs):
        uid = FirebaseUserProfileView()._get_uid(request)
        if not uid:
            return Response(
                {"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        matched_uid = serializer.validated_data["matched_uid"]

        success = create_match_in_firestore(uid, matched_uid)
        if success:
            return Response({"message": "Match created"})
        return Response(
            {"error": "Match creation failed"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class FirebaseMatchesListView(generics.ListAPIView):
    """
    Get list of matches for the authenticated user.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = FirebaseMatchSerializer

    def list(self, request, *args, **kwargs):
        uid = FirebaseUserProfileView()._get_uid(request)
        if not uid:
            return Response(
                {"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED
            )
        matches = get_matches_for_user(uid)
        serializer = self.get_serializer(matches, many=True)
        return Response(serializer.data)


class FirebasePushNotificationView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PushNotificationSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        title = serializer.validated_data.get("title", "Notification")
        body = serializer.validated_data.get("body", "Message")

        response = send_push_notification(token, title, body)
        if response:
            return Response({"message": "Notification sent", "response": response})
        return Response(
            {"error": "Failed to send notification"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ==========================
# TRANSLATION
# ==========================


LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "auto": "Auto-detect",
    # ... include all other supported languages here
}


class TranslationView(generics.GenericAPIView):
    serializer_class = TranslationRequestSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=TranslationRequestSerializer,
        responses={
            200: TranslationResponseSerializer,
            500: CustomErrorResponseSerializer,
        },
        description="Translate text from source language to target language",
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data["text"]
        source = serializer.validated_data.get("source_language", "auto")
        target = serializer.validated_data["target_language"]

        try:
            # Perform translation
            translator = GoogleTranslator(source=source, target=target)
            translated_text = translator.translate(text)

            # Log translation
            log = TranslationLog.objects.create(
                source_text=text,
                translated_text=translated_text,
                source_language=source,
                target_language=target,
                character_count=len(text),
                translation_time=0,
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )

            response_serializer = TranslationResponseSerializer(log)
            return Response(
                {
                    "message": "Translation successful",
                    "status": "success",
                    "data": response_serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"message": f"Translation failed: {str(e)}", "status": "error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    operation_id="supported_languages",
    summary="Get supported languages",
    responses=SupportedLanguagesResponseSerializer,
)
def get(self, request, *args, **kwargs):
    translator = GoogleTranslator()
    languages = translator.get_supported_languages(as_dict=True)
    serializer = SupportedLanguagesResponseSerializer(
        {"languages": languages, "total": len(languages)}
    )
    return Response(
        {
            "message": "Supported languages retrieved",
            "status": "success",
            "data": serializer.data,
        },
        status=status.HTTP_200_OK,
    )


class TranslationHistoryView(generics.ListAPIView):
    """
    Retrieve the latest 50 translation logs.
    """

    serializer_class = TranslationResponseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Order by most recent and limit to 50
        return TranslationLog.objects.order_by("-created_at")[:50]

    @extend_schema(
        operation_id="translation_history",
        summary="Get latest translations",
        description="Retrieve the 50 most recent translation logs.",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "status": {"type": "string"},
                    "data": {
                        "type": "array",
                        "items": TranslationResponseSerializer,
                    },
                },
            }
        },
    )
    def list(self, request, *args, **kwargs):
        """Override list to include message and status in response"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "message": "History retrieved",
                "status": "success",
                "data": serializer.data,
            }
        )


class TranslationStatsView(APIView):
    @extend_schema(responses={200: TranslationStatsResponseSerializer})
    def get(self, request):
        # Aggregate statistics
        total_translations = TranslationLog.objects.count()
        total_characters = (
            TranslationLog.objects.aggregate(total_chars=Sum("character_count"))[
                "total_chars"
            ]
            or 0
        )
        avg_time = (
            TranslationLog.objects.aggregate(avg_time=Avg("translation_time"))[
                "avg_time"
            ]
            or 0
        )

        # Popular target languages
        popular_targets = (
            TranslationLog.objects.values("target_language")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        # Popular source languages
        popular_sources = (
            TranslationLog.objects.values("source_language")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        # Serialize language counts
        popular_targets_serialized = [
            {"language": item["target_language"], "count": item["count"]}
            for item in popular_targets
        ]
        popular_sources_serialized = [
            {"language": item["source_language"], "count": item["count"]}
            for item in popular_sources
        ]

        stats_data = {
            "total_translations": total_translations,
            "total_characters_translated": total_characters,
            "average_translation_time": round(avg_time, 3),
            "popular_target_languages": popular_targets_serialized,
            "popular_source_languages": popular_sources_serialized,
        }

        response_data = {
            "status": "success",
            "message": "Translation statistics retrieved successfully",
            "stats": stats_data,
        }

        # Use DRF serializer for consistent output & OpenAPI docs
        serializer = TranslationStatsResponseSerializer(response_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ==========================
# JOB OPTIONS
# ==========================


# class JobOptionsView(APIView):
#     def get(self, request):
#         return Response(
#             {
#                 "message": "Job options retrieved",
#                 "status": "success",
#                 "data": {
#                     "categories": [{"value": k, "label": v} for k, v in Job.CATEGORIES],
#                     "types": [{"value": k, "label": v} for k, v in Job.JOB_TYPES],
#                     "statuses": [
#                         {"value": k, "label": v} for k, v in Job.STATUS_CHOICES
#                     ],
#                 },
#             }
#         )


# ==========================
# EMAIL
# ==========================


class SendGenericEmailView(GenericAPIView):
    serializer_class = GenericEmailSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        EmailLog.objects.create(
            email_type="generic",
            recipient_email=data["to_email"],
            subject=data["subject"],
            message=data["message"],
        )

        send_mail(
            data["subject"],
            data["message"],
            settings.DEFAULT_FROM_EMAIL,
            [data["to_email"]],
        )

        return Response({"message": "Email sent", "status": "success"})


class SendNewsletterWelcomeEmailView(generics.GenericAPIView):
    """
    Send a welcome email to new newsletter subscribers.
    """

    serializer_class = NewsletterWelcomeEmailSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Send the welcome email
        send_mail(
            subject="Welcome to Bondah",
            message="Welcome to Bondah Dating!",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[data["email"]],
        )

        return Response(
            {"message": "Welcome email sent", "status": "success"},
            status=status.HTTP_200_OK,
        )


class SendWaitlistConfirmationEmailView(GenericAPIView):
    serializer_class = WaitlistConfirmationEmailSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        send_mail(
            "Waitlist confirmation",
            "You are on the waitlist!",
            settings.DEFAULT_FROM_EMAIL,
            [data["email"]],
        )

        return Response({"message": "Waitlist email sent", "status": "success"})


# ==========================
# ADMIN
# ==========================


class AdminWaitlistListView(GenericAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = WaitlistEntrySerializer
    queryset = Waitlist.objects.all()

    @extend_schema(
        responses={200: WaitlistEntrySerializer(many=True)},
        description="Retrieve all waitlist entries",
    )
    def get(self, request, *args, **kwargs):
        entries = self.get_queryset()
        serializer = self.get_serializer(entries, many=True)
        return Response(
            {
                "message": "Waitlist retrieved",
                "status": "success",
                "data": serializer.data,
            }
        )


@authentication_required_schema()
class AdminNewsletterListView(GenericAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = NewsletterSubscriberSerializer
    queryset = NewsletterSubscriber.objects.all()

    @extend_schema(
        responses={200: NewsletterSubscriberSerializer(many=True)},
        description="Retrieve all newsletter subscribers",
    )
    def get(self, request, *args, **kwargs):
        entries = self.get_queryset()
        serializer = self.get_serializer(entries, many=True)
        return Response(
            {
                "message": "Subscribers retrieved",
                "status": "success",
                "data": serializer.data,
            }
        )


# Bondmaker Application Review View
class AdminBondmakerReviewView(GenericAPIView):
    permission_classes = [IsAdminUser]

    class InputSerializer(serializers.Serializer):
        action = serializers.ChoiceField(choices=["approve", "reject"])
        reason = serializers.CharField(required=False, allow_blank=True)

    serializer_class = InputSerializer

    def post(self, request, verification_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]
        reason = serializer.validated_data.get("reason", "")

        verification = get_object_or_404(DocumentVerification, id=verification_id)

        user = verification.user

        if action == "approve":
            verification.status = "approved"
            verification.is_authentic = True
            verification.verified_at = timezone.now()
            verification.save()

            user.is_matchmaker = True
            user.save(update_fields=["is_matchmaker"])

            return Response({"message": "User approved as bondmaker"})

        if action == "reject":
            verification.status = "rejected"
            verification.rejection_reason = reason or "Rejected by admin"
            verification.save()

            user.is_matchmaker = False
            user.save(update_fields=["is_matchmaker"])

            return Response({"message": "Bondmaker request rejected"})


# View for admin to check pending bondamker Application
class AdminPendingBondmakersView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = DocumentVerificationSerializer

    def get_queryset(self):
        return DocumentVerification.objects.filter(status="pending")


# Bondmaker List View (Admin, Filterable, Searchable)
class AdminBondmakerListView(generics.ListAPIView):
    serializer_class = BondmakerListSerializer
    permission_classes = [IsAdminUser]
    pagination_class = BondmakerPagination

    def get_queryset(self):
        queryset = User.objects.select_related("documentverification").all()

        #  Search
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(email__icontains=search)
                | Q(phone_number__icontains=search)
            )

        #  Filter by status
        status = self.request.query_params.get(
            "status"
        )  # pending / approved / rejected
        if status:
            queryset = queryset.filter(documentverification__status=status)

        #  Optional: only bondmakers or applicants
        role = self.request.query_params.get("role")
        if role == "bondmaker":
            queryset = queryset.filter(is_matchmaker=True)
        elif role == "applicant":
            queryset = queryset.filter(is_matchmaker=False)

        return queryset.order_by("-id")


# bondmaker profile Detail view
class BondmakerProfileDetailView(generics.RetrieveAPIView):
    serializer_class = PublicBondmakerProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            User.objects.filter(
                is_matchmaker=True,
                document_verifications__status="approved",
                document_verifications__is_authentic=True,
            )
            .distinct()
            .prefetch_related("document_verifications")
        )


# Bondmaker List view
class PublicBondmakerListView(generics.ListAPIView):
    serializer_class = PublicBondmakerProfileSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = BondmakerPublicPagination

    def get_queryset(self):
        qs = (
            User.objects.filter(
                is_matchmaker=True,
                document_verifications__status="approved",
                document_verifications__is_authentic=True,
            )
            .distinct()
            .prefetch_related("document_verifications")
        )

        # Search
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(location__icontains=search))

        # Filter by availability
        availability = self.request.query_params.get("availability")  # online / offline
        if availability in ["online", "offline"]:
            qs = qs.filter(availability_status=availability)

        return qs.order_by("-id")


# List View of User Subscribed to a Bondmaker
class SubscribedUsersForBondmakerView(generics.ListAPIView):
    serializer_class = BondmakerSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        bondmaker = self.request.user
        if not bondmaker.is_matchmaker:
            return User.objects.none()  # Only bondmakers can access

        # Get all users subscribed to this bondmaker
        subscriptions = BondmakerSubscription.objects.filter(
            bondmaker=bondmaker, active=True
        ).select_related("user")

        subscribed_user_ids = subscriptions.values_list("user_id", flat=True)

        # Return users who are subscribed to this bondmaker
        return User.objects.filter(id__in=subscribed_user_ids, looking_for_love=True)


# Subcription view for Bondmaker
class SubscribeBondmakerView(generics.CreateAPIView):
    serializer_class = SubscribeBondmakerSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        bondmaker_id = request.data.get("bondmaker_id")
        try:
            bondmaker = User.objects.get(id=bondmaker_id, is_matchmaker=True)
        except User.DoesNotExist:
            return Response(
                {"error": "Bondmaker not found"}, status=status.HTTP_404_NOT_FOUND
            )

        subscription, created = BondmakerSubscription.objects.get_or_create(
            bondmaker=bondmaker,
            user=request.user,
            defaults={
                "start_date": timezone.now(),
                "end_date": timezone.now() + timedelta(days=30),
                "active": True,
            },
        )

        if not created:
            # Renew subscription if it expired or update dates
            if not subscription.is_active():
                subscription.start_date = timezone.now()
                subscription.end_date = timezone.now() + timedelta(days=30)
                subscription.active = True
                subscription.save()

        return Response(
            {
                "message": "Subscribed successfully",
                "subscription_id": subscription.id,
                "start_date": subscription.start_date,
                "end_date": subscription.end_date,
                "active": subscription.active,
            }
        )


# End Bondmaker Subscription
class EndBondmakerSubscriptionView(generics.UpdateAPIView):
    serializer_class = BondmakerSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, subscription_id, *args, **kwargs):
        try:
            subscription = BondmakerSubscription.objects.get(
                id=subscription_id, user=request.user, active=True
            )
        except BondmakerSubscription.DoesNotExist:
            return Response({"error": "Active subscription not found"}, status=404)

        subscription.active = False
        subscription.end_date = timezone.now()
        subscription.save()

        return Response({"message": "Subscription ended successfully"})


# All Subscribed User list view
class AllSubscribedUsersListView(generics.ListAPIView):
    serializer_class = BondmakerSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Return all active subscriptions
        return (
            BondmakerSubscription.objects.filter(active=True)
            .select_related("user", "bondmaker")
            .distinct()
        )


#           MATCH CREATE VIEW


# class BondmakerMatchCreateView(generics.CreateAPIView):
#     permission_classes = [IsAuthenticated]
#     serializer_class = UserMatchSerializer

#     # @extend_schema(
#     #     request=None,
#     #     responses=UserMatchSerializer,
#     #     description="Bondmaker creates a valid match between two users.",
#     # )
#     def post(self, request):
#         bondmaker = request.user

#         # Only bondmakers allowed
#         if not bondmaker.is_matchmaker:
#             return Response(
#                 {"error": "Only bondmakers can create matches"},
#                 status=403,
#             )

#         # Validate input IDs
#         user_a_id = request.data.get("user_a_id")
#         user_b_id = request.data.get("user_b_id")

#         if not user_a_id or not user_b_id:
#             return Response(
#                 {"error": "user_a_id and user_b_id are required"},
#                 status=400,
#             )

#         if user_a_id == user_b_id:
#             return Response(
#                 {"error": "Cannot create match with the same user"},
#                 status=400,
#             )

#         # Fetch users
#         user_a = get_object_or_404(User, id=user_a_id)
#         user_b = get_object_or_404(User, id=user_b_id)

#         # -----------------------------------
#         # Visibility check
#         # -----------------------------------
#         user_a_visible = is_user_visible_to(bondmaker, user_a)
#         user_b_visible = is_user_visible_to(bondmaker, user_b)

#         # At least one user must be visible to bondmaker
#         if not (user_a_visible or user_b_visible):
#             return Response(
#                 {"error": "At least one user must be visible to this bondmaker"},
#                 status=400,
#             )

#         # If only one is visible, the other must be suggested
#         if user_a_visible ^ user_b_visible:
#             subscriber = user_a if user_a_visible else user_b
#             suggested = user_b if user_a_visible else user_a

#             is_suggested = SuggestedMatch.objects.filter(
#                 bondmaker=bondmaker,
#                 user=subscriber,
#                 suggested_user=suggested,
#             ).exists()

#             if not is_suggested:
#                 return Response(
#                     {
#                         "error": "Unsubscribed user must be explicitly suggested by the bondmaker"
#                     },
#                     status=400,
#                 )

#         # -----------------------------------
#         # Mutual like check
#         # -----------------------------------
#         mutual_like = (
#             UserInteraction.objects.filter(
#                 user=user_a,
#                 target_user=user_b,
#                 interaction_type="like",
#             ).exists()
#             and UserInteraction.objects.filter(
#                 user=user_b,
#                 target_user=user_a,
#                 interaction_type="like",
#             ).exists()
#         )

#         if not mutual_like:
#             return Response(
#                 {"error": "Users have not liked each other"},
#                 status=400,
#             )

#         # -----------------------------------
#         # Compatibility score For future
#         # -----------------------------------
#         match_score = calculate_match_score(user_a, user_b)

#         # if match_score <= 50:
#         #     return Response(
#         #         {
#         #             "error": "Compatibility score must be greater than 50",
#         #             "score": match_score,
#         #         },
#         #         status=400,
#         #     )

#         # -----------------------------------
#         # Distance calculation
#         # -----------------------------------
#         distance = user_a.get_distance_to(user_b) or 0

#         # -----------------------------------
#         # Canonical ordering for DB uniqueness
#         # -----------------------------------
#         user1, user2 = sorted([user_a, user_b], key=lambda u: u.id)

#         # -----------------------------------
#         # Create match (DB constraint prevents duplicates)
#         # -----------------------------------
#         match = UserMatch.objects.create(
#             user1=user1,
#             user2=user2,
#             distance=distance,
#             match_score=match_score,
#             status="matched",
#         )

#         # -----------------------------------
#         # Serialize for response / OpenAPI
#         # -----------------------------------
#         serializer = UserMatchSerializer(match)

#         return Response(serializer.data, status=201)


#           MATCH SUGGESTION VIEW

class BondmakerSuggestionView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BondmakerSuggestionSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bondmaker = request.user
        subscriber = serializer.validated_data["subscriber"]
        suggested_user = serializer.validated_data["suggested_user"]

        if SuggestedMatch.objects.filter(
            bondmaker=bondmaker,
            user=subscriber,
            suggested_user=suggested_user,
        ).exists():
            return Response(
                {"detail": "You have already suggested this user to this person."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        SuggestedMatch.objects.create(
            bondmaker=bondmaker,
            user=subscriber,
            suggested_user=suggested_user,
        )

        return Response(
            {"status": "Suggestion created and notifications sent"},
            status=status.HTTP_201_CREATED,
        )


class SetVisibilityView(generics.CreateAPIView):
    serializer_class = VisibilitySerializer
    permission_classes = [IsAuthenticated]


# a reusable “active visibility” filter
ACTIVE_VISIBILITY_FILTER = Q(
    visibility_settings__is_active=True,
    visibility_settings__expires_at__gt=timezone.now(),
)


# visibility ListView for Public User
class GlobalPublicUsersListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = VisibilitySerializer

    def get_queryset(self):
        return User.objects.filter(
            ACTIVE_VISIBILITY_FILTER,
            visibility_settings__visibility="public",
        ).distinct()


# private ListView for a Bondmaker
class PrivateUsersForBondmakerListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = VisibilitySerializer

    def get_queryset(self):
        bondmaker = self.request.user

        return User.objects.filter(
            ACTIVE_VISIBILITY_FILTER,
            visibility_settings__visibility="private",
            visibility_settings__bondmaker=bondmaker,
        ).distinct()


class EndVisbilityView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(description="Visibility ended successfully"),
            400: OpenApiResponse(description="No active visibility to end"),
        },
        description="End the currently active visibility before 7 days expiry.",
    )
    def post(
        self,
        request,
    ):
        visibility = Visibility.objects.filter(
            owner=request.user,
            is_active=True,
            expires_at__gt=timezone.now(),
        ).first()
        if not visibility:
            return Response({"Message": "No active visibility to end."}, status=400)

        visibility.is_active = False
        visibility.expires_at = timezone.now()
        visibility.save()

        return Response({"message": "Visibility ended successfully."}, status=200)


class MyWalletView(generics.RetrieveAPIView):
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user.wallet


class MyLedgerView(generics.ListAPIView):
    serializer_class = WalletTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.wallet_ledger.all()


class MatchRequestCreateView(generics.GenericAPIView):
    """
    User creates a match request (swipe/like) for a target user.
    Coins are charged (escrow) and bondmaker is notified.
    """

    serializer_class = MatchRequestSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        bondmaker = get_object_or_404(
            User, id=serializer.validated_data["bondmaker_id"]
        )
        target_user = get_object_or_404(
            User, id=serializer.validated_data["target_user_id"]
        )
        coins = serializer.validated_data["coins"]

        # Charge coins and create MatchRequest (escrow)
        try:
            match_request = charge_match_request(
                user=user,
                bondmaker=bondmaker,
                target_user=target_user,
                coins=coins,
            )
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)

        # Create or update UserMatch record
        distance = user.get_distance_to(target_user) or 0
        user_match, created = UserMatch.objects.update_or_create(
            user1=user,
            user2=target_user,
            defaults={
                "distance": distance,
                "status": "pending",
                "match_score": 0,
            },
        )

        # Create notification for bondmaker
        notification = Notification.objects.create(
            user=bondmaker,
            title="New Match Request",
            message=f"{user.name} liked {target_user.name}. Review the request.",
        )

        # Send push notification
        send_push_notification(
            bondmaker,
            title=notification.title,
            message=notification.message,
            data={"match_request_id": match_request.id},
        )

        return Response(
            {
                "message": "Match request created successfully",
                "match_request_id": match_request.id,
                "coins_charged": match_request.coins_charged,
                "user_match_id": user_match.id,
                "status": user_match.status,
                "user_balance": user.wallet.available_balance,
            },
            status=status.HTTP_201_CREATED,
        )


# Bondmaker Accept View for swiping and match Request
class BondmakerAcceptMatchView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BondmakerMatchActionSerializer

    @extend_schema(
        request=BondmakerMatchActionSerializer,
        responses=BondmakerMatchActionResponseSerializer,
        description="Bondmaker accepts a pending match and releases escrow coins.",
    )
    def post(self, request, usermatch_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bondmaker = request.user

        match = get_object_or_404(
            UserMatch,
            id=usermatch_id,
            user2__bondmaker=bondmaker,
            status="pending",
        )

        platform_usd, bondmaker_usd = accept_match_request(match.match_request)

        match.status = "matched"
        match.save()

        # user_a = match.user1
        # user_b = match.user2

        # #  Create notifications
        # notif_a = Notification.objects.create(
        #     user=user_a,
        #     title="It's a Match!",
        #     message=f"You have been matched with {user_b.name}",
        # )

        # notif_b = Notification.objects.create(
        #     user=user_b,
        #     title="It's a Match!",
        #     message=f"You have been matched with {user_a.name}",
        # )

        # #  Push notifications
        # send_push_notification(
        #     user_a,
        #     title=notif_a.title,
        #     message=notif_a.message,
        #     data={"match_id": match.id},
        # )

        # send_push_notification(
        #     user_b,
        #     title=notif_b.title,
        #     message=notif_b.message,
        #     data={"match_id": match.id},
        # )

        return Response(
            {
                "message": "Match accepted",
                "platform_share_usd": float(platform_usd),
                "bondmaker_share_usd": float(bondmaker_usd),
            },
            status=status.HTTP_200_OK,
        )


class BondmakerRejectMatchView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BondmakerMatchActionSerializer

    @extend_schema(
        request=BondmakerMatchActionSerializer,
        responses=BondmakerMatchActionResponseSerializer,
        description="Bondmaker rejects a pending match and refunds coins.",
    )
    def post(self, request, usermatch_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bondmaker = request.user

        match = get_object_or_404(
            UserMatch,
            id=usermatch_id,
            user2__bondmaker=bondmaker,
            status="pending",
        )

        reject_match_request(match.match_request)

        match.status = "disliked"
        match.save()

        return Response(
            {
                "message": "Match rejected and coins refunded",
            },
            status=status.HTTP_200_OK,
        )


# Purchase Coins
class PurchaseCoinView(generics.GenericAPIView):
    serializer_class = PurchaseSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        package_id = serializer.validated_data["package_id"]
        platform = serializer.validated_data["platform"]
        receipt_data = serializer.validated_data.get("receipt_data")
        purchase_token = serializer.validated_data.get("purchase_token")
        user = request.user

        # --------------------------
        # 1. Validate Package
        # --------------------------
        try:
            package = BondcoinPackage.objects.get(id=package_id, is_active=True)
        except BondcoinPackage.DoesNotExist:
            return Response({"error": "Invalid or inactive package"}, status=400)

        # --------------------------
        # 2. Verify purchase
        # --------------------------
        try:
            if platform == "apple":
                # Will raise ValidationError if invalid
                process_apple_purchase(user, receipt_data, package)
            elif platform == "google":
                # Will raise ValidationError if invalid
                process_google_purchase(user, purchase_token, package)
            else:
                return Response({"error": "Invalid platform"}, status=400)
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)

        # --------------------------
        # 3. Credit Wallet & Log Ledger
        # --------------------------
        with transaction.atomic():
            # Credit user's wallet
            credit_wallet(
                user=user,
                amount=package.bondcoin_amount,
                source="purchase",
                reference_id=receipt_data or purchase_token,
            )

            # Track revenue from purchase
            amount_usd = package.price_usd
            store_fee = (amount_usd * Decimal("0.30")).quantize(Decimal("0.01"))
            net_revenue = (amount_usd - store_fee).quantize(Decimal("0.01"))

            RevenueRecord.objects.create(
                user=user,
                store=platform,
                product_id=package.id,
                transaction_id=receipt_data or purchase_token,
                amount_usd=amount_usd,
                store_fee_usd=store_fee,
                net_revenue_usd=net_revenue,
                coins_awarded=package.bondcoin_amount,
            )

        return Response(
            {
                "message": "Coins purchased successfully",
                "coins_received": package.bondcoin_amount,
                "user_balance": user.wallet.available_balance,
            },
            status=status.HTTP_201_CREATED,
        )


class UserInteractionView(generics.CreateAPIView):
    """
    Handles all swipe interactions.

    LIKE  -> Charge coins, create MatchRequest, create/update UserMatch(pending),
             notify bondmaker.
    PASS/DISLIKE -> Only store interaction (temporary memory).
    BLOCK/REPORT -> Update UserMatch to blocked.
    """

    serializer_class = UserInteractionSerializer
    permission_classes = [IsAuthenticated]

    SWIPE_COST = 10  # coins per like

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        target_user = serializer.validated_data["target_user"]
        interaction_type = serializer.validated_data["interaction_type"]
        metadata = serializer.validated_data.get("metadata", {})

        # Save interaction history (always)
        interaction, _ = UserInteraction.objects.update_or_create(
            user=user,
            target_user=target_user,
            interaction_type=interaction_type,
            defaults={"metadata": metadata},
        )

        # ---------------------------------------------------------
        # LIKE  → CHARGE COINS → CREATE MATCH REQUEST → USERMATCH
        # ---------------------------------------------------------
        if interaction_type == "like":
            bondmaker = getattr(target_user, "bondmaker", None)

            if not bondmaker:
                return Response(
                    {"error": "Target user is not under any bondmaker"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                match_request = charge_match_request(
                    user=user,
                    bondmaker=bondmaker,
                    target_user=target_user,
                    coins=self.SWIPE_COST,
                )
            except ValidationError as e:
                raise ValidationError({"detail": str(e)})

            # Create or update UserMatch as pending
            distance = user.get_distance_to(target_user) or 0

            UserMatch.objects.update_or_create(
                user1=user,
                user2=target_user,
                defaults={
                    "distance": distance,
                    "status": "pending",
                },
            )

            # Track notification in DB
            notification = Notification.objects.create(
                user=bondmaker,
                title="New Match Request",
                message=f"{user.name} liked {target_user.name}. Review request.",
            )

            # Push notification to bondmaker
            send_push_notification(
                bondmaker,
                title=notification.title,
                body=notification.message,
                data={"match_request_id": match_request.id},
            )

        # ---------------------------------------------------------
        # BLOCK / REPORT  → RELATIONSHIP STATE (UserMatch)
        # ---------------------------------------------------------
        elif interaction_type == "block":
            # Mark the match as blocked or create it if it doesn't exist
            user_match, _ = UserMatch.objects.update_or_create(
                user1=user,
                user2=target_user,
                defaults={"status": "blocked", "distance": user.get_distance_to(target_user) or 0},
            )

        elif interaction_type == "report":
            # Mark the match as blocked
            user_match, _ = UserMatch.objects.update_or_create(
                user1=user,
                user2=target_user,
                defaults={"status": "blocked", "distance": user.get_distance_to(target_user) or 0},
            )

            # Create a report record
            Report.objects.create(
                reporter=user,
                reported_user=target_user,
                reason=serializer.validated_data.get("metadata", {}).get("reason", "other"),
                description=serializer.validated_data.get("metadata", {}).get("description", ""),
                user_match=user_match,
            )

        # ---------------------------------------------------------
        # PASS / DISLIKE → DO NOTHING (temporary memory only)
        # ---------------------------------------------------------

        return Response(
            {
                "message": "Interaction recorded successfully",
                "interaction_type": interaction_type,
            },
            status=status.HTTP_201_CREATED,
        )


class UserSwipeDeckView(generics.ListAPIView):
    """
    Returns users for swipe deck:
    - Only public users with active visibility
    - Exclude already swiped users
    - Filter by distance (optional max_distance query param)
    """

    serializer_class = UserSwipeCardSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Use pagination if needed

    def get_queryset(self):
        user = self.request.user
        max_distance = self.request.query_params.get("max_distance", None)

        # 1. Only public visible users
        visible_users = User.objects.filter(
            visibility_settings__visibility="public",
            visibility_settings__is_active=True,
            visibility_settings__expires_at__gt=timezone.now(),
        ).exclude(id=user.id)

        # 2. Exclude already swiped users
        swiped_ids = UserInteraction.objects.filter(user=user).values_list(
            "target_user_id", flat=True
        )
        visible_users = visible_users.exclude(id__in=swiped_ids)

        # 3. Filter by max_distance if provided
        if max_distance and user.has_location:
            lat_rad = float(user.latitude) * 3.14159265359 / 180
            lon_rad = float(user.longitude) * 3.14159265359 / 180

            visible_users = visible_users.annotate(
                distance_km=6371
                * ACos(
                    Cos(Radians(F("latitude")))
                    * Cos(lat_rad)
                    * Cos(Radians(F("longitude")) - lon_rad)
                    + Sin(Radians(F("latitude"))) * Sin(lat_rad)
                )
            )
            visible_users = visible_users.filter(distance_km__lte=float(max_distance))
            visible_users = visible_users.order_by("distance_km")
        else:
            visible_users = visible_users.order_by("?")  # random order

        return visible_users

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class PendingMatchUserListView(generics.ListAPIView):
    serializer_class = PendingMatchUserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PendingRequestListPagination

    def get_queryset(self):
        bondmaker = self.request.user

        return (
            UserMatch.objects.filter(
                user2__bondmaker=bondmaker,
                status="pending",
            )
            .select_related("user1", "user2", "match_request")
            .order_by("-created_at")
        )
