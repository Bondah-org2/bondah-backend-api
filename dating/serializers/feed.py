from rest_framework import serializers
from datetime import timedelta
from django.utils import timezone
from ..models import Activity, Post, PostComment, PostInteraction, Story, StoryView, StoryInteraction
from django.db.models import F


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


class PostDetailSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)
    comments = PostCommentNestedSerializer(many=True, read_only=True)
    has_liked = serializers.SerializerMethodField()
    # has_bonded = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = "__all__"

    def get_has_liked(self, obj) -> bool:
        user = self.context["request"].user
        return obj.interactions.filter(user=user, interaction_type="like").exists()


    # def get_has_bonded(self, obj) -> bool:
    #     user = self.context["request"].user
    #     return obj.interactions.filter(user=user, interaction_type="bond").exists()
class PostCommentCreateSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)
    likes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PostComment
        fields = [
            "id",
            "author",
            "author_name",
            "content",
            "likes_count",
            "created_at",
        ]
        read_only_fields = ["author", "likes_count", "created_at"]


class PostSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)
    image_urls = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    hashtags = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    mentions = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    has_liked = serializers.SerializerMethodField(default=False)
    # has_bonded = serializers.SerializerMethodField(default=False)
    is_featured = serializers.BooleanField(default=False)
    is_reported = serializers.BooleanField(default=False)
    video_thumbnail = serializers.ListField(child=serializers.URLField(), required=False, allow_empty=True)
    video_url = serializers.ListField(child=serializers.URLField(), required=False, allow_empty=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "author",
            "author_name",
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
            # "has_bonded",
            "created_at",
            "updated_at",
            "is_reported",
            "is_featured",
        ]
        read_only_fields = [
            "id",
            "likes_count",
            "comments_count",
            # "shares_count",
            # "bonds_count",
            "author",
        ]

    def get_has_liked(self, obj) -> bool:
        user = self.context["request"].user
        return obj.interactions.filter(user=user, interaction_type="like").exists()


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
