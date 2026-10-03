from dating.location_utils import find_nearby_users
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from ..location_utils import update_user_location, geocode_address
from ..models import LocationHistory, LocationPermission
from ..serializers import LocationUpdateSerializer, AddressGeocodeSerializer, LocationPrivacyUpdateSerializer, LocationPermissionSerializer, LocationHistorySerializer, UserProfileWithLocationSerializer, NearbyUserSerializer, MatchPreferencesSerializer, LocationStatisticsSerializer
from ..location_utils import get_location_statistics
from drf_spectacular.utils import OpenApiResponse
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView


@extend_schema(
    tags=["Location"],
    )
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


@extend_schema(
    tags=["Location"],
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


@extend_schema(
    tags=["Location"],
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


@extend_schema(
    tags=["Location"],
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


@extend_schema(
    tags=["Location"],
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


@extend_schema(
    tags=["Location"],
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
        if not self.request.user.country:
            return Response(
                {"message": "Enable location access to see users in your region"},
                status=status.HTTP_200_OK
            )

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


@extend_schema(
    tags=["Matchmaker"],
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


@extend_schema(
    tags=["Location"],
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


@extend_schema(
    tags=["Location"],
    )
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
