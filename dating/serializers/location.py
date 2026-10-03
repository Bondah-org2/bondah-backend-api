from rest_framework import serializers
from ..models import User, LocationHistory, LocationPermission
from .oauth import SocialAccountSerializer


# Location Serializers
class LocationUpdateSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=10, decimal_places=8, required=True)
    longitude = serializers.DecimalField(max_digits=11, decimal_places=8, required=True)
    accuracy = serializers.FloatField(required=False, allow_null=True)
    source = serializers.ChoiceField(
        choices=["gps", "network", "manual", "ip"], default="gps"
    )

    def validate_latitude(self, value):
        if not (-90 <= value <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if not (-180 <= value <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value


class AddressGeocodeSerializer(serializers.Serializer):
    address = serializers.CharField(max_length=500, required=True)

    def validate_address(self, value):
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Address must be at least 3 characters long."
            )
        return value.strip()


class LocationPrivacyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "location_privacy",
            "location_sharing_enabled",
            "location_update_frequency",
            "max_distance",
        ]


class LocationPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationPermission
        fields = [
            "location_enabled",
            "background_location_enabled",
            "precise_location_enabled",
            "location_services_consent",
            "location_data_sharing",
        ]


class LocationHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationHistory
        fields = [
            "latitude",
            "longitude",
            "accuracy",
            "address",
            "city",
            "state",
            "country",
            "timestamp",
            "source",
        ]
        read_only_fields = ["timestamp"]


class UserProfileWithLocationSerializer(serializers.ModelSerializer):
    social_accounts = SocialAccountSerializer(many=True, read_only=True)
    location_permissions = LocationPermissionSerializer(read_only=True)
    has_location = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "gender",
            "age",
            "location",
            "latitude",
            "longitude",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "location_privacy",
            "location_sharing_enabled",
            "location_update_frequency",
            "max_distance",
            "age_range_min",
            "age_range_max",
            "preferred_gender",
            "bio",
            "is_matchmaker",
            "social_accounts",
            "location_permissions",
            "has_location",
            "last_location_update",
        ]
        read_only_fields = ["id", "email", "has_location", "last_location_update"]


class PrivacyDistributionSerializer(serializers.Serializer):
    public = serializers.IntegerField()
    friends = serializers.IntegerField()
    private = serializers.IntegerField()
    hidden = serializers.IntegerField()


class LocationStatisticsSerializer(serializers.Serializer):
    total_users_with_location = serializers.IntegerField()
    location_updates_24h = serializers.IntegerField()
    location_updates_7d = serializers.IntegerField()
    active_users_with_location = serializers.IntegerField()
    privacy_distribution = PrivacyDistributionSerializer()


class NearbyUserSerializer(serializers.ModelSerializer):
    distance = serializers.FloatField()
    coordinates = serializers.ListField(child=serializers.FloatField())

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "age",
            "gender",
            "city",
            "bio",
            "distance",
            "coordinates",
        ]


class MatchPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["max_distance", "age_range_min", "age_range_max", "preferred_gender"]

    def validate(self, attrs):
        age_min = attrs.get("age_range_min")
        age_max = attrs.get("age_range_max")

        if age_min and age_max and age_min > age_max:
            raise serializers.ValidationError(
                "Minimum age cannot be greater than maximum age."
            )

        return attrs
