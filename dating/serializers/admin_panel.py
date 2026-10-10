from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from ..models import User, Job, JobApplication, AdminPermission, AdminRole, DocumentVerification
from typing import List
from .users import SecurityQuestionSerializer, UserSocialHandleCreateSerializer
from .verification import SelfieVerificationSerializer


class AdminBondmakerDetailSerializer(serializers.ModelSerializer):
    # User fields
    name = serializers.CharField(source="user.name")
    username = serializers.CharField(source="user.username")
    email = serializers.EmailField(source="user.email")
    gender = serializers.CharField(source="user.gender")
    location = serializers.CharField(source="user.location")
    bio = serializers.CharField(source="user.bio")
    bondmaker_bio = serializers.CharField(source="user.bondmaker_bio")
    profile_picture = serializers.CharField(source="user.profile_picture")
    date_of_birth = serializers.DateField(
        source="user.date_of_birth", read_only=True)
    relationship_status = serializers.CharField(
        source="user.relationship_status", read_only=True)
    qualification = serializers.CharField(
        source="user.education_level", read_only=True)

    date_of_birth = serializers.DateField(source="user.date_of_birth")
    relationship_status = serializers.CharField(source="user.relationship_status")
    qualification = serializers.CharField(source="user.education_level")

    # Document images
    front_image = serializers.CharField(source="front_image_url")
    back_image = serializers.CharField(source="back_image_url")

    # Selfie
    selfie = serializers.SerializerMethodField()
    # security
    security_questions = SecurityQuestionSerializer(
        source="user.security_questions",
        many=True
    )
    social_handles = UserSocialHandleCreateSerializer(
        source="user.social_handles", read_only=True, many=True)

    class Meta:
        model = DocumentVerification
        fields = [
            "id",
            "user",
            "name",
            "username",
            "email",
            "gender",
            "location",
            "bio",
            "bondmaker_bio",
            "profile_picture",
            "date_of_birth",
            "relationship_status",
            "qualification",
            "uploaded_at",

            # document
            "document_type",
            "front_image",
            "back_image",
            # selfie
            "selfie",
            "security_questions",
            "social_handles"
        ]

    def get_selfie(self, obj) -> str:
        selfie = obj.selfie_checks.first()
        return SelfieVerificationSerializer(selfie).data if selfie else None


class AdminBondmakerStatsSerializer(serializers.Serializer):
    pending = serializers.IntegerField()
    approved = serializers.IntegerField()
    rejected = serializers.IntegerField()


class AdminJobCreateSerializer(serializers.ModelSerializer):
    jobType = serializers.CharField(source="job_type")
    salaryRange = serializers.CharField(source="salary_range")
    requirements = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )

    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "jobType",
            "category",
            "status",
            "description",
            "location",
            "salaryRange",
            "requirements",
            "responsibilities",
            "benefits",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        # Convert requirements list to JSON
        requirements = validated_data.pop("requirements", [])
        job = Job.objects.create(**validated_data, requirements=requirements)
        return job


class AdminJobUpdateSerializer(serializers.ModelSerializer):
    jobType = serializers.CharField(source="job_type")
    salaryRange = serializers.CharField(source="salary_range")
    requirements = serializers.ListField(child=serializers.CharField(), required=False)

    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "jobType",
            "category",
            "status",
            "description",
            "location",
            "salaryRange",
            "requirements",
            "responsibilities",
            "benefits",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def update(self, instance, validated_data):
        # Handle requirements separately
        requirements = validated_data.pop("requirements", None)
        if requirements is not None:
            instance.requirements = requirements

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class AdminJobListSerializer(serializers.ModelSerializer):
    jobType = serializers.CharField(source="job_type")
    salaryRange = serializers.CharField(source="salary_range")
    applications_count = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "jobType",
            "category",
            "status",
            "location",
            "salaryRange",
            "applications_count",
            "created_at",
        ]

    def get_applications_count(self, obj) -> int:
        return obj.applications.count()


class AdminJobApplicationSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source="job.title", read_only=True)
    job_category = serializers.CharField(source="job.category", read_only=True)
    applicant_name = serializers.SerializerMethodField()

    class Meta:
        model = JobApplication
        fields = [
            "id",
            "job_title",
            "job_category",
            "applicant_name",
            "email",
            "phone",
            "experience_years",
            "current_company",
            "expected_salary",
            "status",
            "applied_at",
        ]
        read_only_fields = ["id", "applied_at"]

    def get_applicant_name(self, obj) -> str:

        return f"{obj.first_name} {obj.last_name}"


class AdminUpdateApplicationStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=JobApplication.STATUS_CHOICES)


class AdminJobApplicationDetailSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source="job.title", read_only=True)
    job_category = serializers.CharField(source="job.category", read_only=True)
    job_type = serializers.CharField(source="job.job_type", read_only=True)
    job_location = serializers.CharField(source="job.location", read_only=True)
    job_salary_range = serializers.CharField(source="job.salary_range", read_only=True)

    applicant_name = serializers.SerializerMethodField()

    class Meta:
        model = JobApplication
        fields = [
            "id",
            "job_title",
            "job_category",
            "job_type",
            "job_location",
            "job_salary_range",
            "applicant_name",
            "email",
            "phone",
            "cover_letter",
            "resume_url",
            "experience_years",
            "current_company",
            "expected_salary",
            "status",
            "applied_at",
            "updated_at",
        ]
        read_only_fields = ["id", "applied_at", "updated_at"]

    def get_applicant_name(self, obj) -> str:
        return f"{obj.first_name} {obj.last_name}"


class AdminOverviewSerializer(serializers.Serializer):
    period_days = serializers.IntegerField()

    users_stats = serializers.DictField()
    financial_summary = serializers.DictField()
    subscription_summary = serializers.DictField()
    applications_stats = serializers.DictField()
    reports_stats = serializers.DictField()


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


TEAM_STATUSES = ("active", "inactive")


def _role_flags(role) -> dict:
    from ..permissions import ADMIN_FLAGS

    return {f: bool(getattr(role, f, False)) for f in ADMIN_FLAGS}


def _check_grantable(actor, flags: dict):
    """A team manager can only hand out access they have themselves."""
    from ..permissions import admin_flags

    if actor.is_principal_admin:
        return
    mine = admin_flags(actor)
    over = [f for f, on in flags.items() if on and not mine.get(f)]
    if over:
        raise serializers.ValidationError(
            {"permissions": f"You can't grant access you don't have: {', '.join(over)}."}
        )


class CreateTeamMemberSerializer(serializers.ModelSerializer):
    role = serializers.SlugRelatedField(
        queryset=AdminRole.objects.all(), slug_field="name"
    )
    permissions = AdminPermissionSerializer(
        required=False,
        write_only=True
    )
    permission_data = AdminPermissionSerializer(source="admin_permissions",
                                                required=False,
                                                read_only=True)

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
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_password(self, value):
        from .auth import ConfirmRegistrationSerializer

        return ConfirmRegistrationSerializer.validate_password_strength(value)

    def validate_status(self, value):
        if value not in TEAM_STATUSES:
            raise serializers.ValidationError("A team member is active or inactive.")
        return value

    def validate(self, attrs):
        flags = _role_flags(attrs["role"])
        flags.update(attrs.get("permissions") or {})
        _check_grantable(self.context["request"].user, flags)
        return attrs

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


class AdminLoginSerializer(serializers.Serializer):

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):

        email = data.get("email")
        password = data.get("password")

        user = authenticate(username=email, password=password)

        if not user:
            raise serializers.ValidationError("Invalid login credentials")

        if not user.is_staff and not user.is_principal_admin:
            raise serializers.ValidationError("Not an admin account")

        if user.status != "active":
            raise serializers.ValidationError("This admin account is not active")

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
            "is_principal_admin",
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
            "can_approve_applications": "Approve applications",
        }

        return [label for field, label in mapping.items() if getattr(perm, field, False)]

    def get_joined_date(self, obj) -> str:
        return obj.date_joined.strftime("%d-%m-%y")

    def get_last_active(self, obj) -> str:
        return obj.last_active.strftime("%d-%m-%y") if obj.last_active else None


class UpdateAdminMemberSerializer(serializers.ModelSerializer):

    role = serializers.SlugRelatedField(
        queryset=AdminRole.objects.all(),
        slug_field="name"
    )

    permissions = AdminPermissionSerializer(write_only=True, required=False)

    permission_data = AdminPermissionSerializer(source="admin_permissions",
                                                required=False,
                                                read_only=True)

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

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_status(self, value):
        if value not in TEAM_STATUSES:
            raise serializers.ValidationError("A team member is active or inactive.")
        return value

    def validate(self, attrs):
        if "permissions" in attrs:
            flags = attrs["permissions"]
        elif attrs.get("role"):
            flags = _role_flags(attrs["role"])
        else:
            flags = {}
        _check_grantable(self.context["request"].user, flags)
        return attrs

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
