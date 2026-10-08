import logging
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from django.utils import timezone
from datetime import timedelta
from rest_framework import serializers
from ..utils import get_cached_static_profile, get_cached_my_profile
from django.core.cache import cache
from ..models import Activity, DeviceRegistration, UserRoleSelection, DocumentVerification, UserSecurityQuestion, UserSocialHandle, UserInterest, UserProfileView
from django.contrib.auth import get_user_model
from ..serializers import LanguageSettingsSerializer, UserProfileDetailSerializer, DeviceRegistrationSerializer, NotificationSettingsSerializer, UsernameUpdateSerializer, UserSecurityQuestionSerializer, UserSecurityQuestionCreateSerializer, UserSocialHandleSerializer, UserSocialHandleCreateSerializer, UserInterestSerializer, UserRoleSelectionSerializer, UserRoleStatusSerializer, StaticUserProfileSerializer
from ..location_utils import calculate_match_score
from drf_spectacular.utils import extend_schema_view, OpenApiResponse
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema
from dating.openapi.response_serializers import SimpleStatusResponseSerializer, CustomErrorResponseSerializer, NotificationSettingsErrorSerializer, LanguageSettingsResponseSerializer, LanguageSettingsErrorSerializer, NotificationSettingsResponseSerializer
from rest_framework.generics import GenericAPIView

User = get_user_model()
logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Profile"],
    )
class UserProfileViews(generics.RetrieveUpdateAPIView):
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
            # from .integrations.firebase import update_user_profile_in_firestore

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

        except serializers.ValidationError:
            # Invalid input is the client's error (400), not a server failure
            raise
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
class AccountDeactivationView(generics.GenericAPIView):
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

class LanguageSettingsView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LanguageSettingsSerializer


@extend_schema(
    tags=["Authentication"],
    responses={
        401: OpenApiResponse(description="User Not Authenticated")
    }
    )

class DeviceRegistrationView(generics.CreateAPIView):
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
class UserProfileDetailView(generics.RetrieveAPIView):
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


@extend_schema(
    tags=["Profile"],
    )
class UserInterestsView(generics.ListAPIView, generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserInterestSerializer  # Output serializer

    def get_queryset(self):
        return UserInterest.objects.filter(is_active=True).order_by("name")

    def update(self, request, *args, **kwargs):
        # Only the lists that are sent change (sign-up step 3 sends no interests).
        interests = request.data.get("interests")
        hobbies = request.data.get("hobbies")
        # The user's own personality (Friendly, Calm, ...); sign-up sends it here.
        traits = request.data.get("personality_traits")

        if traits is not None and (
            not isinstance(traits, list)
            or len(traits) > 3
            or not all(isinstance(t, str) and len(t) <= 40 for t in traits)
        ):
            return Response(
                {"message": "Choose up to 3 personality traits", "status": "error"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (interests is not None and not isinstance(interests, list)) or (
            hobbies is not None and not isinstance(hobbies, list)
        ):
            return Response(
                {"message": "Interests and hobbies must be arrays", "status": "error"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        fields = []
        if interests is not None:
            request.user.interests = interests
            fields.append("interests")
        if hobbies is not None:
            request.user.hobbies = hobbies
            fields.append("hobbies")
        if traits is not None:
            request.user.traits = traits
            fields.append("traits")
        if fields:
            request.user.save(update_fields=fields)

        return Response(
            {
                "message": "Interests updated successfully",
                "status": "success",
                "interests": request.user.interests,
                "hobbies": request.user.hobbies,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Bond Circle"],
    )
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


@extend_schema(
    tags=["Social"],
    )
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
@extend_schema(
    tags=["Profile"],
    )
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


@extend_schema(
    tags=["Profile"],
    )
class UserSecurityQuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific security question response
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return UserSecurityQuestionSerializer

    def get_queryset(self):
        from ..models import UserSecurityQuestion

        return UserSecurityQuestion.objects.filter(user=self.request.user)


@extend_schema(
    tags=["Profile"],
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
