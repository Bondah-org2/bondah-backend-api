from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework import generics
from django.shortcuts import get_object_or_404
from ..pagination import ActivityFeedPagination
from django.db.models import Exists, F, OuterRef
from django.utils import timezone
from ..services import feed_service
from ..permissions import IsBondmakerOrReadOnly
from ..models import Activity, Post, PostComment, PostInteraction, PostReport, BondmakerSubscription, CommentInteraction
from rest_framework import serializers
from ..serializers import ActivityFeedSerializer, PostSerializer, PostInteractionSerializer, PostCommentCreateSerializer
from ..serializers.feed import _author_card
from rest_framework import permissions
from drf_spectacular.utils import extend_schema_view
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action


class ReportContentSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(choices=[c for c, _ in PostReport.REPORT_TYPES])
    description = serializers.CharField(required=False, allow_blank=True, max_length=2000, default="")


@extend_schema(
    tags=["Post"],
    )
@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name="author",
                description="Only posts by this Bondmaker (user id)",
                location=OpenApiParameter.QUERY,
                type=int,
            ),
        ]
    ),
    retrieve=extend_schema(
        parameters=[
            OpenApiParameter(name="pk", description="Post ID", location=OpenApiParameter.PATH, type=int),
        ]
    ),
    update=extend_schema(
        parameters=[
            OpenApiParameter(name="pk", description="Post ID", location=OpenApiParameter.PATH, type=int),
        ]
    ),
    partial_update=extend_schema(
        parameters=[
            OpenApiParameter(name="pk", description="Post ID", location=OpenApiParameter.PATH, type=int),
        ]
    ),
    destroy=extend_schema(
        parameters=[
            OpenApiParameter(name="pk", description="Post ID", location=OpenApiParameter.PATH, type=int),
        ]
    ),
)

class PostViewSet(viewsets.ModelViewSet):
    """Bond Story posts. Rules: services/feed_service.py.

    - list: posts I may see, newest first. ?author=<id> ?search=<text>
      ?scope=following (bondmakers I follow).
    - retrieve: one post, only if I may see it (404 otherwise).
    - create: bondmakers only. update / destroy: the author only.
    - interact: like (toggle) or save.
    - report: report a post to Team Bondah.
    """

    permission_classes = [IsBondmakerOrReadOnly]
    lookup_field = "pk"
    throttle_scope = None  # reports set "report_write" per action

    def get_permissions(self):
        if self.action in ("interact", "report"):
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        qs = (
            feed_service.visible_posts(user)
            .select_related("author")
            .annotate(
                liked=Exists(
                    PostInteraction.objects.filter(post=OuterRef("pk"), user=user, interaction_type="like")
                ),
                # For the Follow button on each card, without a query per post
                following_author=Exists(feed_service.following(user).filter(bondmaker=OuterRef("author"))),
            )
        )
        if self.action == "list":
            params = self.request.query_params
            if params.get("author"):
                try:
                    qs = qs.filter(author_id=int(params["author"]))
                except ValueError:
                    raise serializers.ValidationError({"author": "Must be a user id."})
            if params.get("scope") == "following":
                qs = qs.filter(
                    author_id__in=feed_service.following(user).values("bondmaker_id")
                )
            qs = feed_service.search(qs, params.get("search"))
        return qs.order_by("-created_at", "-id")

    def get_serializer_class(self):
        if self.action == "interact":
            return PostInteractionSerializer
        if self.action == "report":
            return ReportContentSerializer
        return PostSerializer

    def perform_create(self, serializer):
        if not self.request.user.is_matchmaker:
            raise PermissionDenied("Only bondmakers can create posts.")
        serializer.save(author=self.request.user)

    def _own(self, post):
        if post.author_id != self.request.user.id:
            raise PermissionDenied("You can only change your own posts.")

    def perform_update(self, serializer):
        self._own(serializer.instance)
        serializer.save(edited_at=timezone.now())

    def perform_destroy(self, instance):
        self._own(instance)
        instance.is_active = False
        instance.save(update_fields=["is_active"])

    @extend_schema(parameters=[OpenApiParameter(name="pk", location=OpenApiParameter.PATH, type=int)])
    @action(detail=True, methods=["post"])
    def interact(self, request, pk=None):
        post = self.get_object()
        serializer = PostInteractionSerializer(data=request.data, context={"request": request, "post": post})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        post.refresh_from_db(fields=["likes_count"])
        liked = PostInteraction.objects.filter(post=post, user=request.user, interaction_type="like").exists()
        return Response(
            {"message": "Interaction processed", "likes_count": max(0, post.likes_count), "liked": liked},
            status=status.HTTP_200_OK,
        )

    @extend_schema(parameters=[OpenApiParameter(name="pk", location=OpenApiParameter.PATH, type=int)])
    @action(detail=True, methods=["post"], throttle_scope="report_write")
    def report(self, request, pk=None):
        post = self.get_object()
        body = ReportContentSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            _, created = feed_service.report(reporter=request.user, post=post, **body.validated_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"reported": True, "already": not created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


@extend_schema_view(
    list=extend_schema(parameters=[OpenApiParameter(name="post_pk", location=OpenApiParameter.PATH, type=int)]),
    create=extend_schema(parameters=[OpenApiParameter(name="post_pk", location=OpenApiParameter.PATH, type=int)]),
)
@extend_schema(tags=["PostComment"])
class PostCommentViewSet(viewsets.ModelViewSet):
    """Comments on a post I may see. Oldest first, paged.

    Writers edit their own; writers and the post's author can delete.
    """

    serializer_class = PostCommentCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ActivityFeedPagination
    http_method_names = ["get", "post", "patch", "delete"]
    throttle_scope = None  # reports set "report_write" per action

    def _post(self):
        if not hasattr(self, "_post_obj"):
            self._post_obj = get_object_or_404(
                feed_service.visible_posts(self.request.user).select_related("author"), pk=self.kwargs["post_pk"]
            )
        return self._post_obj

    def get_queryset(self):
        user = self.request.user
        return (
            PostComment.objects.filter(post=self._post(), is_active=True)
            .select_related("author")
            .annotate(liked=Exists(CommentInteraction.objects.filter(comment=OuterRef("pk"), user=user)))
            .order_by("created_at", "id")
        )

    def perform_create(self, serializer):
        post = self._post()
        with transaction.atomic():
            comment = serializer.save(author=self.request.user, post=post)
            Post.objects.filter(id=post.id).update(comments_count=F("comments_count") + 1)
        if post.author_id != self.request.user.id:
            Activity.objects.create(
                actor=self.request.user, recipient=post.author, action="post_comment",
                metadata={"post_id": post.id, "comment_id": comment.id},
            )

    def perform_update(self, serializer):
        if serializer.instance.author_id != self.request.user.id:
            raise PermissionDenied("You can only edit your own comments.")
        serializer.save(is_edited=True)

    def perform_destroy(self, instance):
        if instance.author_id != self.request.user.id and self._post().author_id != self.request.user.id:
            raise PermissionDenied("You can only delete your own comments.")
        with transaction.atomic():
            updated = PostComment.objects.filter(pk=instance.pk, is_active=True).update(is_active=False)
            if updated:
                Post.objects.filter(id=instance.post_id, comments_count__gt=0).update(
                    comments_count=F("comments_count") - 1
                )

    @extend_schema(parameters=[OpenApiParameter(name="post_pk", location=OpenApiParameter.PATH, type=int)])
    @action(detail=True, methods=["post"])
    def like(self, request, post_pk=None, pk=None):
        """Like or unlike a comment (one like per person)."""
        comment = self.get_object()
        with transaction.atomic():
            obj, created = CommentInteraction.objects.get_or_create(user=request.user, comment=comment)
            if created:
                PostComment.objects.filter(id=comment.id).update(likes_count=F("likes_count") + 1)
                if comment.author_id != request.user.id:
                    Activity.objects.create(
                        actor=request.user, recipient=comment.author, action="comment_like",
                        metadata={
                            "post_id": comment.post_id,
                            "comment_id": comment.id,
                            "post_author_name": self._post().author.name,
                        },
                    )
            else:
                obj.delete()
                PostComment.objects.filter(id=comment.id, likes_count__gt=0).update(likes_count=F("likes_count") - 1)
        comment.refresh_from_db(fields=["likes_count"])
        return Response({"liked": created, "likes_count": comment.likes_count})

    @extend_schema(parameters=[OpenApiParameter(name="post_pk", location=OpenApiParameter.PATH, type=int)])
    @action(detail=True, methods=["post"], throttle_scope="report_write")
    def report(self, request, post_pk=None, pk=None):
        comment = self.get_object()
        body = ReportContentSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            _, created = feed_service.report(
                reporter=request.user, comment=comment, post=comment.post, **body.validated_data
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"reported": True, "already": not created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


# ======================================== ACTIVITY FEEDS
@extend_schema(
    tags=["Activity Feeds"]
)
class ActivityFeedView(generics.ListAPIView):
    """activity/  ?kind=bondstory: only Bond Story likes and comments."""

    permission_classes = [IsAuthenticated]
    serializer_class = ActivityFeedSerializer
    pagination_class = ActivityFeedPagination

    def get_queryset(self):
        qs = Activity.objects.filter(recipient=self.request.user).select_related("actor")
        if self.request.query_params.get("kind") == "bondstory":
            qs = qs.filter(action__in=Activity.BOND_STORY_ACTIONS)
        return qs


@extend_schema(tags=["Activity Feeds"])
class ActivityDeleteView(generics.DestroyAPIView):
    """activity/<id>/: remove one of my notifications."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Activity.objects.filter(recipient=self.request.user)


@extend_schema(tags=["Bondmaker"])
class FollowingListView(generics.ListAPIView):
    """bondmaker/following/: bondmakers I follow, most recent first."""

    permission_classes = [IsAuthenticated]
    pagination_class = ActivityFeedPagination

    def get_queryset(self):
        return feed_service.following(self.request.user).select_related("bondmaker").order_by("-start_date", "-id")

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(
            [
                {**_author_card(f.bondmaker), "following": True, "followed_at": f.start_date}
                for f in page
            ]
        )
