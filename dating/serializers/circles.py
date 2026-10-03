from rest_framework import serializers
from django.db import transaction
from django.db.models import Q
from ..models import UserMatch, BondCirclePost, BondCirclePostComment, BondCirclePostLike, BondCircle, BondCircleMember


# Bond Circle Create View
class AddCircleMembersSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )

    def validate(self, attrs):
        bondmaker = self.context["request"].user

        if not bondmaker.is_matchmaker:
            raise serializers.ValidationError("Only bondmakers can add members.")

        if not hasattr(bondmaker, "bond_circle"):
            raise serializers.ValidationError("You must create a bond circle first.")

        user_ids = set(attrs["user_ids"])

        matched_user_ids = set(
            UserMatch.objects.filter(
                match_request__bondmaker=bondmaker,
                status="matched"
            ).filter(
                Q(user1_id__in=user_ids) | Q(user2_id__in=user_ids)
            ).values_list("user1_id", "user2_id")
        )

        # Flatten the tuples into a single set
        flattened_ids = set()
        for u1, u2 in matched_user_ids:
            if u1 in user_ids:
                flattened_ids.add(u1)
            if u2 in user_ids:
                flattened_ids.add(u2)

        invalid_ids = user_ids - flattened_ids

        if invalid_ids:
            raise serializers.ValidationError(
                f"Some users are not matched under you: {list(invalid_ids)}"
            )

        attrs["validated_user_ids"] = user_ids
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        bondmaker = self.context["request"].user
        circle = bondmaker.bond_circle
        user_ids = validated_data["validated_user_ids"]

        created_members = []

        for user_id in user_ids:
            member, created = BondCircleMember.objects.get_or_create(
                circle=circle, user_id=user_id, defaults={"added_by": bondmaker}
            )
            if created:
                created_members.append(user_id)

        return {"added_members": created_members, "count": len(created_members)}


class BondCirclePostSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.BooleanField(read_only=True)

    class Meta:
        model = BondCirclePost
        fields = [
            "id",
            "content",
            "author_name",
            "created_at",
            "likes_count",
            "comments_count",
            "is_liked",
        ]


class BondCircleCommentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = BondCirclePostComment
        fields = ["id", "post", "user", "user_name", "content", "created_at"]
        read_only_fields = ["user"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class BondCircleSerializer(serializers.ModelSerializer):
    bondmaker_name = serializers.CharField(source="bondmaker.name", read_only=True)
    class Meta:
        model = BondCircle
        fields = ["id", "name", "bondmaker_name", "description", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        user = self.context["request"].user

        if not user.is_matchmaker:
            raise serializers.ValidationError(
                "Only bondmakers can create a bond circle."
            )

        if hasattr(user, "bond_circle"):
            raise serializers.ValidationError("You already have a bond circle.")

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = self.context["request"].user

        return BondCircle.objects.create(bondmaker=user, **validated_data)


class TogglePostLikeSerializer(serializers.Serializer):
    post_id = serializers.IntegerField(write_only=True)
    liked = serializers.BooleanField(read_only=True)

    def validate_post_id(self, value):
        try:
            post = BondCirclePost.objects.select_related("circle").get(id=value)
        except BondCirclePost.DoesNotExist:
            raise serializers.ValidationError("Post does not exist.")

        user = self.context["request"].user
        circle = post.circle

        # Permission check
        is_member = BondCircleMember.objects.filter(circle=circle, user=user).exists()

        if not (user == circle.bondmaker or is_member):
            raise serializers.ValidationError(
                "You are not allowed to interact with this post."
            )

        self.context["post"] = post
        return value

    @transaction.atomic
    def create(self, validated_data):
        user = self.context["request"].user
        post = self.context["post"]

        like, created = BondCirclePostLike.objects.get_or_create(post=post, user=user)

        if not created:
            like.delete()
            return {"liked": False}

        return {"liked": True}
