# analytics/services.py

from datetime import timedelta
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.core.cache import cache
from django.db.models.functions import TruncMonth

from .constants import (
    CACHE_TIMEOUT_SECONDS,
    MATCH_STATUS_ACCEPTED,
    VISIBILITY_PUBLIC,
    VISIBILITY_APPROVED,
    INTERACTION_LIKE,
    MATCHES_PER_LEVEL,
)
from ..models import MatchRequest
from ..models import Visibility
from ..models import BondmakerSubscription
from ..models import PostInteraction, PostComment, BondmakerTaskCompletion


class BondmakerAnalyticsService:

    def __init__(self, user, days):
        self.user = user
        self.days = days
        self.now = timezone.now()
        self.start_date = self.now - timedelta(days=days)
        self.previous_start = self.start_date - timedelta(days=days)

    # ==========================
    # PUBLIC ENTRY POINT
    # ==========================
    def get_analytics(self):
        cache_key = self._generate_cache_key()
        cached = cache.get(cache_key)
        if cached:
            return cached

        data = {
            "period_days": self.days,
            **self._get_match_metrics(),
            **self._get_live_profile_metrics(),
            **self._get_subscription_metrics(),
            **self._get_engagement_metrics(),
            **self._get_badge_metrics(),
            **self._get_task_metrics(),
            "chart_data": self._get_chart_data(),
        }

        cache.set(cache_key, data, CACHE_TIMEOUT_SECONDS)
        return data

    # ==========================
    # MATCH METRICS
    # ==========================
    def _get_match_metrics(self):
        stats = MatchRequest.objects.filter(
            bondmaker=self.user,
            status=MATCH_STATUS_ACCEPTED,
        ).aggregate(
            current=Count("id", filter=Q(created_at__gte=self.start_date)),
            previous=Count(
                "id",
                filter=Q(created_at__range=(self.previous_start, self.start_date)),
            ),
            earnings=Sum(
                "coins_charged",
                filter=Q(created_at__gte=self.start_date),
            ),
        )

        current = stats["current"] or 0
        previous = stats["previous"] or 0

        return {
            "matches": current,
            "matches_growth_percentage": self._calculate_growth(current, previous),
            "earnings": (stats["earnings"] or 0) / 100,
        }

    # ==========================
    # LIVE PROFILES
    # ==========================
    def _get_live_profile_metrics(self):
        stats = Visibility.objects.filter(
            bondmaker=self.user,
            visibility=VISIBILITY_PUBLIC,
            status=VISIBILITY_APPROVED,
        ).aggregate(
            current=Count("id", filter=Q(expires_at__gt=self.now)),
            previous=Count(
                "id",
                filter=Q(created_at__lte=self.start_date)
                & (Q(expires_at__isnull=True) | Q(expires_at__gt=self.previous_start)),
            ),
        )

        current = stats["current"] or 0
        previous = stats["previous"] or 0

        return {
            "live_profiles": current,
            "live_profiles_growth_percentage": self._calculate_growth(
                current, previous
            ),
        }

    # ==========================
    # SUBSCRIPTIONS
    # ==========================
    def _get_subscription_metrics(self):
        stats = BondmakerSubscription.objects.filter(bondmaker=self.user).aggregate(
            current=Count("id", filter=Q(active=True, end_date__gt=self.now)),
            previous=Count(
                "id",
                filter=Q(
                    start_date__lte=self.start_date, end_date__gt=self.previous_start
                ),
            ),
        )

        current = stats["current"] or 0
        previous = stats["previous"] or 0

        return {
            "net_subscribers": current,
            "net_subscribers_growth_percentage": self._calculate_growth(
                current, previous
            ),
        }

    # ==========================
    # ENGAGEMENT
    # ==========================
    def _get_engagement_metrics(self):
        like_stats = PostInteraction.objects.filter(
            post__author=self.user,
            interaction_type=INTERACTION_LIKE,
        ).aggregate(
            current=Count("id", filter=Q(created_at__gte=self.start_date)),
            previous=Count(
                "id",
                filter=Q(created_at__range=(self.previous_start, self.start_date)),
            ),
        )

        comment_stats = PostComment.objects.filter(
            post__author=self.user,
            is_active=True,
        ).aggregate(
            current=Count("id", filter=Q(created_at__gte=self.start_date)),
            previous=Count(
                "id",
                filter=Q(created_at__range=(self.previous_start, self.start_date)),
            ),
        )

        return {
            "likes": like_stats["current"] or 0,
            "likes_growth_percentage": self._calculate_growth(
                like_stats["current"] or 0,
                like_stats["previous"] or 0,
            ),
            "comments": comment_stats["current"] or 0,
            "comments_growth_percentage": self._calculate_growth(
                comment_stats["current"] or 0,
                comment_stats["previous"] or 0,
            ),
        }

    # ==========================
    # BADGE
    # ==========================
    def _get_badge_metrics(self):
        total_matches = MatchRequest.objects.filter(
            bondmaker=self.user,
            status=MATCH_STATUS_ACCEPTED,
        ).count()

        current_level = total_matches // MATCHES_PER_LEVEL + 1
        next_badge_level = 10

        levels_remaining = max(next_badge_level - current_level, 0)

        return {
            "badge_progress_levels_remaining": levels_remaining
        }

    def _get_chart_data(self):
        monthly_matches = (
            MatchRequest.objects.filter(bondmaker=self.user, status=MATCH_STATUS_ACCEPTED)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(total=Count("id"))
            .order_by("month")
        )

        return [
            {"month": entry["month"].strftime("%b"), "matches": entry["total"]}
            for entry in monthly_matches
        ]

    def _get_task_metrics(self):
        stats = BondmakerTaskCompletion.objects.filter(
            bondmaker=self.user
        ).aggregate(
            current=Count("id", filter=Q(completed_at__gte=self.start_date)),
            previous=Count(
                "id",
                filter=Q(completed_at__range=(self.previous_start, self.start_date)),
            ),
        )

        current = stats["current"] or 0
        previous = stats["previous"] or 0

        return {
            "completed_tasks": current,
            "completed_tasks_growth_percentage": self._calculate_growth(current, previous),
        }


    # ==========================
    # UTILITIES
    # ==========================
    def _generate_cache_key(self):
        return f"bondmaker_analytics_{self.user.id}_{self.days}"

    def _calculate_growth(self, current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 2)
