from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework import generics
from django.shortcuts import get_object_or_404
from ..pagination import ActivityFeedPagination
from django.db.models import F
from ..permissions import IsBondmakerOrReadOnly
from ..models import Activity, Post, PostComment, BondmakerSubscription, CommentInteraction
from rest_framework import serializers
from ..serializers import ActivityFeedSerializer, PostSerializer, PostInteractionSerializer, PostDetailSerializer, PostCommentCreateSerializer
from rest_framework import permissions
from drf_spectacular.utils import extend_schema_view
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action


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
    """
    Handles posts:
    - list: feed (following + public posts)
    - retrieve: single post with comments_count
    - create / update / partial_update: create or edit post
    - destroy: soft delete post
    - interact: like, share, bond (custom action)
    """

    permission_classes = [IsBondmakerOrReadOnly]
    lookup_field = "pk"

    def get_permissions(self):
        """
        Allow normal authenticated users to interact with posts,
        but restrict post creation to bondmakers.
        """
        if self.action == "interact":
            return [permissions.IsAuthenticated()]

        return super().get_permissions()

    # -------- Queryset --------
    def get_queryset(self):
        user = self.request.user

        base_queryset = Post.objects.filter(is_active=True).select_related("author")

        if self.action == "list":
            # Feed view: posts from followed bondmakers or public posts
            following_ids = BondmakerSubscription.objects.filter(
                user=user, active=True
            ).values_list("bondmaker_id", flat=True)

            author_param = self.request.query_params.get("author")
            if author_param:
                try:
                    author_id = int(author_param)
                except ValueError:
                    raise serializers.ValidationError({"author": "Must be a user id."})
                # Authors see all of their own posts; everyone else gets the
                # same visibility rules as the feed.
                if author_id == user.id:
                    return base_queryset.filter(author_id=author_id).order_by("-created_at")
                base_queryset = base_queryset.filter(author_id=author_id)

            return base_queryset.filter(
                Q(author_id__in=following_ids) | Q(visibility="public")
            ).order_by("-created_at")

        # For retrieve/update/delete actions
        return base_queryset

    # -------- Serializer selection --------
    def get_serializer_class(self):
        if self.action == "retrieve":
            return PostDetailSerializer
        elif self.action in ["create", "update", "partial_update"]:
            return PostSerializer
        elif self.action == "interact":
            return PostInteractionSerializer
        return PostSerializer

    # -------- CRUD Hooks --------
    def perform_create(self, serializer):
        if not self.request.user.is_matchmaker:
            raise PermissionDenied("Only bondmakers can create posts.")

        serializer.save(author=self.request.user)

    def perform_destroy(self, instance):
        # Soft delete
        instance.is_active = False
        instance.save(update_fields=["is_active"])

    # -------- Custom Actions --------
    @extend_schema(
        parameters=[
            OpenApiParameter(name="pk", description="Post ID", location=OpenApiParameter.PATH, type=int),
        ]
    )
    @action(detail=True, methods=["post"])
    def interact(self, request, pk=None):
        post = self.get_object()

        serializer = PostInteractionSerializer(
            data=request.data,
            context={"request": request, "post": post},
        )
        serializer.is_valid(raise_exception=True)

        interaction = serializer.save()

        post.refresh_from_db()

        return Response({
            "message": "Interaction processed",
            "likes_count": post.likes_count,
        }, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(name="post_pk", description="Post ID", location=OpenApiParameter.PATH, type=int),
        ]
    ),
    create=extend_schema(
        parameters=[
            OpenApiParameter(name="post_pk", description="Post ID", location=OpenApiParameter.PATH, type=int),
        ]
    ),
    retrieve=extend_schema(
        parameters=[
            OpenApiParameter(name="post_pk", description="Post ID", location=OpenApiParameter.PATH, type=int),
            OpenApiParameter(name="id", description="Comment ID", location=OpenApiParameter.PATH, type=int),
        ]
    ),
    update=extend_schema(
        parameters=[
            OpenApiParameter(name="post_pk", description="Post ID", location=OpenApiParameter.PATH, type=int),
            OpenApiParameter(name="id", description="Comment ID", location=OpenApiParameter.PATH, type=int),
        ]
    ),
    partial_update=extend_schema(
        parameters=[
            OpenApiParameter(name="post_pk", description="Post ID", location=OpenApiParameter.PATH, type=int),
            OpenApiParameter(name="id", description="Comment ID", location=OpenApiParameter.PATH, type=int),
        ]
    ),
    destroy=extend_schema(
        parameters=[
            OpenApiParameter(name="post_pk", description="Post ID", location=OpenApiParameter.PATH, type=int),
            OpenApiParameter(name="id", description="Comment ID", location=OpenApiParameter.PATH, type=int),
        ]
    ),
)
@extend_schema(
    tags=["PostComment"],
    )
class PostCommentViewSet(viewsets.ModelViewSet):
    serializer_class = PostCommentCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        post_id = self.kwargs["post_pk"]
        return (
            PostComment.objects.filter(post_id=post_id, is_active=True)
            .select_related("author")
            .order_by("-created_at")
        )

    # Create comment + increment Post.comments_count safely
    def perform_create(self, serializer):
        post = get_object_or_404(Post, pk=self.kwargs["post_pk"])

        with transaction.atomic():
            serializer.save(author=self.request.user, post=post)

            Post.objects.filter(id=post.id).update(
                comments_count=F("comments_count") + 1
            )

    # Soft delete comment + decrement Post.comments_count safely
    def perform_destroy(self, instance):
        with transaction.atomic():
            instance.is_active = False
            instance.save(update_fields=["is_active"])

            Post.objects.filter(id=instance.post_id).update(
                comments_count=F("comments_count") - 1
            )

    # Safe Like Toggle (Atomic + No Double Count)
    @extend_schema(
        parameters=[
            OpenApiParameter(name="post_pk", description="Post ID", location=OpenApiParameter.PATH, type=int),
            OpenApiParameter(name="id", description="Comment ID", location=OpenApiParameter.PATH, type=int),
        ]
    )
    @action(detail=True, methods=["post"])
    def like(self, request, post_pk=None, id=None):
        """
        Like/unlike a comment.
        Each user can only like a comment once.
        """
        comment = self.get_object()

        with transaction.atomic():
            # Try to create a like; ensures 1 like per user per comment
            obj, created = CommentInteraction.objects.get_or_create(
                user=request.user,
                comment=comment,
            )

            if not created:
                # User already liked → toggle OFF
                obj.delete()
                PostComment.objects.filter(id=comment.id).update(
                    likes_count=F("likes_count") - 1
                )
                comment.refresh_from_db()
                return Response({"liked": False, "likes_count": comment.likes_count})

            # New like → increment safely
            PostComment.objects.filter(id=comment.id).update(
                likes_count=F("likes_count") + 1
            )
            comment.refresh_from_db()
            return Response(
                {"liked": True, "likes_count": comment.likes_count},
                status=status.HTTP_201_CREATED,
            )


# ======================================== ACTIVITY FEEDS
@extend_schema(
    tags=["Activity Feeds"]
)
class ActivityFeedView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ActivityFeedSerializer
    pagination_class = ActivityFeedPagination

    def get_queryset(self):
        return Activity.objects.filter(recipient=self.request.user)
