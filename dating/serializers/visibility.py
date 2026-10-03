from dating.tasks import notify_user
from rest_framework import serializers
from django.utils import timezone
from ..models import User, Visibility
from ..services.visibility_services import VisibilityService


class VisibilityOwnerSerializer(serializers.ModelSerializer):
    age = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = ["id", "name", "age", "bio", "profile_picture"]


class VisibilitySerializer(serializers.ModelSerializer):
    bondmaker_id = serializers.IntegerField(write_only=True)
    owner_id = serializers.IntegerField(source="owner.id", read_only=True)

    class Meta:
        model = Visibility
        fields = ["id", "owner_id", "bondmaker_id", "visibility", "status"]
        read_only_fields = ["owner_id", "status"]

    def validate(self, attrs):
        owner = self.context["request"].user
        bondmaker_id = attrs["bondmaker_id"]
        visibility_type = attrs["visibility"]

        try:
            bondmaker = User.objects.get(id=bondmaker_id, is_matchmaker=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid bondmaker.")

        # Prevent multiple active public visibility
        if visibility_type == "public":
            already_public = (
                Visibility.objects.filter(
                    owner=owner,
                    visibility="public",
                    status="approved",
                    expires_at__gt=timezone.now(),
                )
                .exclude(bondmaker=bondmaker)
                .exists()
            )

            if already_public:
                raise serializers.ValidationError(
                    "You are already publicly visible under another bondmaker."
                )

            existing = Visibility.objects.filter(
                owner=owner, bondmaker=bondmaker, status="pending"
            ).exists()

            if existing:
                raise serializers.ValidationError(
                    "You have already sent a visibility request to this bondmaker."
                )

        attrs["bondmaker"] = bondmaker
        return attrs

    def create(self, validated_data):
        owner = self.context["request"].user
        bondmaker = validated_data.pop("bondmaker")
        visibility_type = validated_data["visibility"]

        visibility, _ = Visibility.objects.update_or_create(
            owner=owner,
            bondmaker=bondmaker,
            defaults={
                "visibility": visibility_type,
                "status": "pending",
                "expires_at": None,
            },
        )

        # Notify Bondmaker
        notify_user.delay(
            user=visibility.bondmaker.id,
            title="New Public Visibility Request",
            message=f"{visibility.owner.email} requested public visibility.",
            data={
                "type": "public_visibility_request",
                "visibility_id": visibility.id,
                "visibility_type": visibility_type,
            },
        )

        # Delegate to service layer
        if visibility_type == "private":
            VisibilityService.request_private_visibility(visibility)

        return visibility


class PendingVisibilitySerializer(serializers.ModelSerializer):
    owner = VisibilityOwnerSerializer(read_only=True)

    class Meta:
        model = Visibility
        fields = ["id", "owner", "visibility", "status", "created_at"]


class ApproveVisibilitySerializer(serializers.ModelSerializer):

    class Meta:
        model = Visibility
        fields = ["id", "owner_id", "status"]
        read_only_fields = ["id", "owner_id"]

    def validate_status(self, value):
        if value not in ["approved", "rejected"]:
            raise serializers.ValidationError("Invalid action.")
        return value

    def update(self, instance, validated_data):
        status = validated_data["status"]

        if status == "approved":
            VisibilityService.approve(instance)
        else:
            VisibilityService.reject(instance)

        return instance


class VisibilityStatusSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(source="owner.id", read_only=True)
    bondmaker_id = serializers.IntegerField(source="bondmaker.id", read_only=True)
    visibility_choice = serializers.CharField(source="visibility", read_only=True)
    current_status = serializers.CharField(source="status", read_only=True)

    class Meta:
        model = Visibility
        fields = ["id", "owner_id", "bondmaker_id", "visibility_choice", "current_status"]
