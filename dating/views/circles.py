from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from django.shortcuts import get_object_or_404
from ..pagination import BondCirclePostPagination
from ..models import BondCircleMember, BondCirclePost, BondCircle, BondCirclePostLike
from ..serializers import BondCirclePostSerializer, AddCircleMembersSerializer, BondCircleCommentSerializer, TogglePostLikeSerializer, BondCircleSerializer
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.exceptions import PermissionDenied
from django.db.models import Count, Exists, OuterRef


@extend_schema(
    tags=["BondCircle"],
    )
class AddBondCircleMembersView(GenericAPIView):
    serializer_class = AddCircleMembersSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        return Response(
            {
                "message": f"{result['count']} members added successfully",
                "added_members": result["added_members"],
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=["BondCircle"],
    )
class BondCircleCreateView(generics.CreateAPIView):
    serializer_class = BondCircleSerializer
    permission_classes = [IsAuthenticated]


@extend_schema(
    tags=["BondCircle"],
    )
class BondCircleFeedView(generics.ListAPIView):
    serializer_class = BondCirclePostSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = BondCirclePostPagination

    def get_queryset(self):
        circle = get_object_or_404(
            BondCircle.objects.select_related("bondmaker"), id=self.kwargs["circle_id"]
        )

        user = self.request.user

        # Permission check
        is_member = BondCircleMember.objects.filter(circle=circle, user=user).exists()

        if not (user == circle.bondmaker or is_member):
            raise PermissionDenied("You are not part of this circle.")

        # Subquery to check if current user liked each post
        user_like_subquery = BondCirclePostLike.objects.filter(
            post=OuterRef("pk"), user=user
        )

        return (
            BondCirclePost.objects.filter(circle=circle)
            .select_related("author")
            .annotate(
                likes_count=Count("likes", distinct=True),
                comments_count=Count("comments", distinct=True),
                is_liked=Exists(user_like_subquery),
            )
            .order_by("-created_at")
        )


@extend_schema(
    tags=["BondCircle"],
    )
class BondCirclePostCreateView(generics.CreateAPIView):
    serializer_class = BondCirclePostSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        circle = get_object_or_404(BondCircle, id=self.kwargs["circle_id"])

        if not (
            self.request.user == circle.bondmaker
            or BondCircleMember.objects.filter(
                circle=circle, user=self.request.user
            ).exists()
        ):
            raise PermissionDenied("Not allowed.")

        serializer.save(author=self.request.user, circle=circle)


@extend_schema(
    tags=["Bond Story"],
)
class BondCircleListView(generics.ListAPIView):
    serializer_class = BondCircleSerializer
    permission_classes = [IsAuthenticated]
    queryset = BondCircle.objects.select_related("bondmaker").order_by("-created_at")


@extend_schema(
    tags=["Comment"],
    )
class CreateCommentView(generics.CreateAPIView):
    serializer_class = BondCircleCommentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        post = get_object_or_404(BondCirclePost, id=self.kwargs["post_id"])
        serializer.save(user=self.request.user, post=post)


@extend_schema(
    tags=["TogglePost"],
    )
class TogglePostLikeView(GenericAPIView):
    serializer_class = TogglePostLikeSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        return Response(result, status=status.HTTP_200_OK)
