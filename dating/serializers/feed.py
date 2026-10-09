from rest_framework import serializers
from datetime import timedelta
from django.utils import timezone
from ..models import Activity, Post, PostComment, PostInteraction, Story, StoryView, StoryInteraction
from django.db.models import F

from ..media_refs import MediaRefsMixin


class PostCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)
    is_liked = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PostComment
        fields = [
            "id",
            "author",
            "author_name",
            "content",
            "parent_comment",
            "likes_count",
            "is_liked",
            "created_at",
        ]

    def get_is_liked(self, obj):
        user = self.context.get("request").user
        if not user.is_authenticated:
            return False
        return obj.interactions.filter(user=user).exists()


class PostCommentNestedSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)
    replies_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PostComment
        fields = [
            "id",
            "author",
            "author_name",
            "content",
            "parent_comment",
            "replies_count",
            "created_at",
        ]


def _author_card(user):
    return {
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "country": user.country or "",
        "profile_picture": getattr(user, "bondmaker_profile_picture", None) or user.profile_picture or None,
        "is_bondmaker": bool(user.is_matchmaker),
    }


class PostCommentCreateSerializer(serializers.ModelSerializer):
    """A comment; is_liked comes from an annotation on the list query."""

    author_name = serializers.CharField(source="author.name", read_only=True)
    author_card = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(read_only=True)
    content = serializers.CharField(max_length=1000, trim_whitespace=True)
    is_liked = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = PostComment
        fields = [
            "id",
            "author",
            "author_name",
            "author_card",
            "content",
            "likes_count",
            "is_liked",
            "is_mine",
            "is_edited",
            "created_at",
        ]
        read_only_fields = ["author", "likes_count", "is_edited", "created_at"]

    def get_author_card(self, obj):
        return _author_card(obj.author)

    def get_is_liked(self, obj) -> bool:
        return bool(getattr(obj, "liked", False))

    def get_is_mine(self, obj) -> bool:
        request = self.context.get("request")
        return bool(request and obj.author_id == request.user.id)


class PostSerializer(MediaRefsMixin, serializers.ModelSerializer):
    MAX_IMAGES = 5
    MAX_VIDEOS = 2

    media_ref_fields = {
        "image_urls": ("post_image",),
        "video_url": ("post_video",),
        "video_thumbnail": ("post_image",),
    }

    author_name = serializers.CharField(source="author.name", read_only=True)
    author_card = serializers.SerializerMethodField()
    content = serializers.CharField(max_length=5000, allow_blank=True, required=False, default="")
    visibility = serializers.ChoiceField(choices=Post.VISIBILITY_CHOICES, default="everyone")
    image_urls = serializers.ListField(
        child=serializers.CharField(max_length=500),
        required=False,
        allow_empty=True,
        max_length=MAX_IMAGES,
    )
    hashtags = serializers.ListField(
        child=serializers.CharField(max_length=50), required=False, allow_empty=True, max_length=20
    )
    mentions = serializers.ListField(
        child=serializers.CharField(max_length=50), required=False, allow_empty=True, max_length=20
    )
    has_liked = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()
    following_author = serializers.SerializerMethodField()
    video_thumbnail = serializers.ListField(
        child=serializers.CharField(max_length=500),
        required=False,
        allow_empty=True,
        max_length=MAX_VIDEOS,
    )
    video_url = serializers.ListField(
        child=serializers.CharField(max_length=500),
        required=False,
        allow_empty=True,
        max_length=MAX_VIDEOS,
    )

    class Meta:
        model = Post
        fields = [
            "id",
            "author",
            "author_name",
            "author_card",
            "content",
            "image_urls",
            "video_url",
            "video_thumbnail",
            "visibility",
            "location",
            "hashtags",
            "mentions",
            "likes_count",
            "comments_count",
            # "shares_count",
            # "bonds_count",
            "has_liked",
            "is_mine",
            "following_author",
            "created_at",
            "updated_at",
            "edited_at",
            "is_reported",
            "is_featured",
        ]
        # Moderation flags are Team Bondah's; authors can't set them.
        read_only_fields = [
            "id",
            "likes_count",
            "comments_count",
            "author",
            "edited_at",
            "is_reported",
            "is_featured",
        ]

    def validate(self, attrs):
        content = attrs.get("content", getattr(self.instance, "content", "") or "").strip()
        images = attrs.get("image_urls", getattr(self.instance, "image_urls", []) or [])
        videos = attrs.get("video_url", getattr(self.instance, "video_url", []) or [])
        if not content and not images and not videos:
            raise serializers.ValidationError("Write something or add a photo or video.")
        if "content" in attrs:
            attrs["content"] = content
        return super().validate(attrs)

    def get_author_card(self, obj):
        return _author_card(obj.author)

    def get_has_liked(self, obj) -> bool:
        # Annotated on list/detail queries; one query per post otherwise.
        if hasattr(obj, "liked"):
            return bool(obj.liked)
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.interactions.filter(user=request.user, interaction_type="like").exists()

    def get_is_mine(self, obj) -> bool:
        request = self.context.get("request")
        return bool(request and obj.author_id == request.user.id)

    def get_following_author(self, obj) -> bool:
        return bool(getattr(obj, "following_author", False))


class StorySerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)
    has_liked = serializers.BooleanField(read_only=True)
    has_viewed = serializers.BooleanField(read_only=True)
    reactions_count = serializers.IntegerField(read_only=True)
    views_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Story
        fields = [
            "id",
            "author",
            "author_name",
            "story_type",
            "content",
            "image_url",
            "video_url",
            "video_duration",
            "background_color",
            "text_color",
            "font_size",
            "views_count",
            "reactions_count",
            "has_viewed",
            "has_liked",
            "created_at",
            "expires_at",
        ]


class StoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Story
        fields = [
            "story_type",
            "content",
            "image_url",
            "video_url",
            "video_duration",
            "background_color",
            "text_color",
            "font_size",
        ]

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["author"] = user
        validated_data["expires_at"] = timezone.now() + timedelta(hours=24)
        return super().create(validated_data)


class StoryListSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)
    author_avatar = serializers.CharField(
        source="author.profile_picture", read_only=True
    )

    views_count = serializers.IntegerField(read_only=True)
    reactions_count = serializers.IntegerField(read_only=True)
    has_viewed = serializers.BooleanField(read_only=True)
    is_liked = serializers.BooleanField(read_only=True)

    class Meta:
        model = Story
        fields = [
            "id",
            "author",
            "author_name",
            "author_avatar",
            "story_type",
            "views_count",
            "reactions_count",
            "has_viewed",
            "is_liked",
            "created_at",
        ]


class StoryDetailSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)
    author_avatar = serializers.CharField(
        source="author.profile_picture", read_only=True
    )
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = "__all__"

    def get_is_liked(self, obj):
        user = self.context["request"].user
        return StoryInteraction.objects.filter(
            story=obj, user=user, interaction_type="like"
        ).exists()


class StoryViewerSerializer(serializers.ModelSerializer):
    viewer_name = serializers.CharField(source="viewer.name", read_only=True)
    viewer_avatar = serializers.CharField(
        source="viewer.profile_picture", read_only=True
    )

    class Meta:
        model = StoryView
        fields = ["viewer", "viewer_name", "viewer_avatar", "viewed_at"]


class PostInteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostInteraction
        fields = ["interaction_type"]

    def validate_interaction_type(self, value):
        allowed = ["like", "save"]
        if value not in allowed:
            raise serializers.ValidationError("Invalid interaction type")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        post = self.context["post"]
        interaction_type = validated_data["interaction_type"]

        interaction, created = PostInteraction.objects.get_or_create(
            user=user,
            post=post,
            interaction_type=interaction_type,
        )

        # LIKE (Toggle with counter)
        if interaction_type == "like":
            if created:
                Post.objects.filter(id=post.id).update(
                    likes_count=F("likes_count") + 1
                )
                if post.author_id != user.id:
                    Activity.objects.create(
                        actor=user,
                        recipient=post.author,
                        action="post_like",
                        metadata={"post_id": post.id},
                    )
            else:
                interaction.delete()
                Post.objects.filter(id=post.id).update(
                    likes_count=F("likes_count") - 1
                )

        # SAVE (Toggle without counter)
        elif interaction_type == "save":
            if not created:
                interaction.delete()

        return interaction


class StoryInteractionSerializer(serializers.Serializer):

    story_id = serializers.IntegerField()
    interaction_type = serializers.ChoiceField(
        choices=StoryInteraction.INTERACTION_TYPES
    )

    def create(self, validated_data):
        user = self.context["request"].user
        story = Story.objects.get(id=validated_data["story_id"])

        obj, created = StoryInteraction.objects.get_or_create(
            user=user, story=story, interaction_type=validated_data["interaction_type"]
        )

        if not created:
            obj.delete()
            return {"status": "removed"}

        return {"status": "added"}
