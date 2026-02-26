from django.db.models import Count, Exists, OuterRef
from django.utils import timezone
from .models import Story, StoryView, StoryInteraction


class StoryQueryMixin:
    def base_queryset(self):
        user = self.request.user

        viewed_subquery = StoryView.objects.filter(story=OuterRef("pk"), viewer=user)
        liked_subquery = StoryInteraction.objects.filter(
            story=OuterRef("pk"), user=user, interaction_type="like"
        )

        return (
            Story.objects.filter(is_active=True, expires_at__gt=timezone.now())
            .select_related("author")
            .annotate(
                views_count=Count("views", distinct=True),
                reactions_count=Count("interactions", distinct=True),
                has_viewed=Exists(viewed_subquery),
                is_liked=Exists(liked_subquery),
            )
        )
