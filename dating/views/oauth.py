from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
import requests
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
import os
from ..models import SocialAccount
from ..serializers import GoogleOAuthSerializer, AppleOAuthSerializer, OAuthLoginSerializer, SocialAccountSerializer, GoogleCallbackSerializer
from rest_framework import permissions
from django.db import transaction
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema
from dating.openapi.response_serializers import CustomErrorResponseSerializer, ValidationErrorResponseSerializer, OAuthLinkAccountResponseSerializer, OAuthLinkAccountRequestSerializer, OAuthUnlinkAccountResponseSerializer, SocialAccountsListResponseSerializer, OAuthLoginResponseSerializer, UserProfileWithSocialSerializer


@extend_schema(
    tags=["Authentication"],
    # tags=["OAuth"],
    )
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

        id_token = serializer.validated_data["id_token"]

        try:
            from ..integrations.oauth import (
                GoogleOAuthVerifier,
                OAuthUserManager,
                OAuthTokenGenerator,
            )

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
                    "deletion_cancelled": getattr(user, "deletion_cancelled", False),
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

        if getattr(request, "limited", False):
            return Response(
                {"error": "Too many requests. Please try again in a minute."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        identity_token = serializer.validated_data["identity_token"]

        try:
            from ..integrations.oauth import (
                AppleOAuthVerifier,
                OAuthUserManager,
                OAuthTokenGenerator,
            )

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
                    "deletion_cancelled": getattr(user, "deletion_cancelled", False),
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
class GoogleOAuthCallbackView(generics.GenericAPIView):
    serializer_class = GoogleCallbackSerializer
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

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


@extend_schema(
    # tags=["OAuth"],
    tags=["Authentication"],
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

                from ..integrations.oauth import (
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

                from ..integrations.oauth import (
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
                    "deletion_cancelled": getattr(user, "deletion_cancelled", False),
                },
                status=200,
            )

        except Exception as e:
            return Response(
                {"message": f"Social login failed: {str(e)}", "status": "error"},
                status=500,
            )


class OAuthLinkAccountView(generics.GenericAPIView):
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
            from ..integrations.oauth import (
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
