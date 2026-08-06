# analytics/services.py

from datetime import timedelta
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.core.cache import cache
from django.db.models.functions import TruncMonth

from ..models import (
    MatchRequest,
    Visibility,
    BondmakerSubscription,
    PostInteraction,
    PostComment,
    BondmakerTaskCompletion,
    DocumentVerification,
    ProductRevenueRecord,
    Report,
    User,
)
from django.db.models import Case, When, DecimalField


# Constants
CACHE_TIMEOUT_SECONDS = 600  # 10 min cache
MATCHES_PER_LEVEL = 50
MATCH_STATUS_ACCEPTED = "accepted"
VISIBILITY_PUBLIC = "public"
VISIBILITY_APPROVED = "approved"
INTERACTION_LIKE = "like"


class BondmakerAnalyticsService:
    """Service to compute and cache bondmaker analytics."""

    def __init__(self, user, days=30):
        self.user = user
        self.days = days
        self.now = timezone.now()
        self.start_date = self.now - timedelta(days=days)
        self.previous_start = self.start_date - timedelta(days=days)

    # ==========================
    # PUBLIC ENTRY POINT
    # ==========================
    def get_analytics(self):
        """Return analytics from cache or compute fresh data."""
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
            bondmaker=self.user, status=MATCH_STATUS_ACCEPTED
        ).aggregate(
            current=Count("id", filter=Q(created_at__gte=self.start_date)),
            previous=Count(
                "id", filter=Q(created_at__range=(self.previous_start, self.start_date))
            ),
            earnings=Sum("coins_charged", filter=Q(created_at__gte=self.start_date)),
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
            post__author=self.user, interaction_type=INTERACTION_LIKE
        ).aggregate(
            current=Count("id", filter=Q(created_at__gte=self.start_date)),
            previous=Count(
                "id", filter=Q(created_at__range=(self.previous_start, self.start_date))
            ),
        )

        comment_stats = PostComment.objects.filter(
            post__author=self.user, is_active=True
        ).aggregate(
            current=Count("id", filter=Q(created_at__gte=self.start_date)),
            previous=Count(
                "id", filter=Q(created_at__range=(self.previous_start, self.start_date))
            ),
        )

        return {
            "likes": like_stats["current"] or 0,
            "likes_growth_percentage": self._calculate_growth(
                like_stats["current"] or 0, like_stats["previous"] or 0
            ),
            "comments": comment_stats["current"] or 0,
            "comments_growth_percentage": self._calculate_growth(
                comment_stats["current"] or 0, comment_stats["previous"] or 0
            ),
        }

    # ==========================
    # BADGE METRICS
    # ==========================
    def _get_badge_metrics(self):
        total_matches = MatchRequest.objects.filter(
            bondmaker=self.user, status=MATCH_STATUS_ACCEPTED
        ).count()
        current_level = total_matches // MATCHES_PER_LEVEL + 1
        next_badge_level = 10
        levels_remaining = max(next_badge_level - current_level, 0)
        return {"badge_progress_levels_remaining": levels_remaining,
                "badge_earned": current_level
                }

    # ==========================
    # TASK METRICS
    # ==========================
    def _get_task_metrics(self):
        stats = BondmakerTaskCompletion.objects.filter(bondmaker=self.user).aggregate(
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
            "completed_tasks_growth_percentage": self._calculate_growth(
                current, previous
            ),
        }

    # ==========================
    # CHART DATA
    # ==========================
    def _get_chart_data(self):
        monthly_matches = (
            MatchRequest.objects.filter(
                bondmaker=self.user, status=MATCH_STATUS_ACCEPTED
            )
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(total=Count("id"))
            .order_by("month")
        )
        return [
            {"month": entry["month"].strftime("%b"), "matches": entry["total"]}
            for entry in monthly_matches
        ]

    # ==========================
    # UTILITIES
    # ==========================
    def _calculate_growth(self, current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 2)

    def _generate_cache_key(self):
        return f"bondmaker_analytics_{self.user.id}_{self.days}"

    def clear_cache(self):
        """Clear cached analytics (useful for signals)."""
        cache.delete(self._generate_cache_key())


# ---------------------------------------------------------------------------
# Overview statistics service used by admin/overview page
# ---------------------------------------------------------------------------


class OverviewAnalyticsService:
    """
    Enterprise-grade platform overview analytics service.
    Designed for Admin Overview Page.
    Cached, growth-aware, fine-grained.
    """

    def __init__(self, days=7):
        self.days = days
        self.now = timezone.now()
        self.start_date = self.now - timedelta(days=days)
        self.previous_start = self.start_date - timedelta(days=days)

    # ==========================================================
    # PUBLIC ENTRY
    # ==========================================================

    def get_overview(self):
        cache_key = self._generate_cache_key()
        cached = cache.get(cache_key)
        if cached:
            return cached

        data = {
            "period_days": self.days,
            "users_stats": self._get_user_stats(),
            "financial_summary": self._financial_summary(),
            "applications_stats": self._application_stats(),
            "reports_stats": self._report_stats(),
        }

        cache.set(cache_key, data, CACHE_TIMEOUT_SECONDS)
        return data

    # ==========================================================
    # USERS STATS
    # ==========================================================

    def _get_user_stats(self):
        total_seekers = User.objects.filter(is_matchmaker=False).count()

        total_bondmakers = User.objects.filter(
            is_matchmaker=True
        ).count()

        # New signups
        new_current = User.objects.filter(
            date_joined__gte=self.start_date
        ).count()

        new_previous = User.objects.filter(
            date_joined__range=(self.previous_start, self.start_date)
        ).count()

        # Applications (DocumentVerification)
        total_applications = DocumentVerification.objects.count()

        applications_current = DocumentVerification.objects.filter(
            uploaded_at__gte=self.start_date
        ).count()

        applications_previous = DocumentVerification.objects.filter(
            uploaded_at__range=(self.previous_start, self.start_date)
        ).count()

        return {
            "total_seekers": total_seekers,
            "total_bondmakers": total_bondmakers,
            "new_signups": new_current,
            "new_signups_growth_percentage": self._calculate_growth(
                new_current, new_previous
            ),
            "total_applications": total_applications,
            "applications_growth_percentage": self._calculate_growth(
                applications_current,
                applications_previous,
            ),
        }

    def _financial_summary(self):
        total_requests = MatchRequest.objects.count()

        # Total estimated payout from accepted matches (coins → USD logic if needed)
        stats = ProductRevenueRecord.objects.aggregate(
            total_estimated=Sum("bondmaker_share_usd"),
            pending=Sum(
                Case(
                    When(paid=False, then="bondmaker_share_usd"),
                    output_field=DecimalField(),
                )
            ),
            completed=Sum(
                Case(
                    When(paid=True, then="bondmaker_share_usd"),
                    output_field=DecimalField(),
                )
            ),
            platform_total=Sum("platform_share_usd"),
        )

        return {
            "total_estimated_payout": stats["total_estimated"] or 0,
            "total_requests": total_requests,
            "pending_payout": stats["pending"] or 0,
            "completed_payout": stats["completed"] or 0,
            "platform_revenue": stats["platform_total"] or 0,
        }

    def _application_stats(self):
        pending_bondmaker = DocumentVerification.objects.filter(
            status="pending"
        ).count()

        processing_bondmaker = DocumentVerification.objects.filter(
            status="processing"
        ).count()

        approved_this_month = DocumentVerification.objects.filter(
            status="approved",
            verified_at__month=self.now.month,
            verified_at__year=self.now.year,
        ).count()

        rejected_this_month = DocumentVerification.objects.filter(
            status="rejected",
            updated_at__month=self.now.month,
            updated_at__year=self.now.year,
        ).count()

        return {
            "pending_bondmaker": pending_bondmaker,
            "processing_bondmaker": processing_bondmaker,
            "approved_this_month": approved_this_month,
            "rejected_this_month": rejected_this_month,
        }

    def _report_stats(self):
        total_reports = Report.objects.count()

        pending_reports = Report.objects.filter(
            resolved=False
        ).count()

        resolved_reports = Report.objects.filter(
            resolved=True
        ).count()

        return {
            "total_reports": total_reports,
            "pending_reports": pending_reports,
            "resolved_reports": resolved_reports,
        }

    # ==========================================================
    # UTILITIES
    # ==========================================================

    def _calculate_growth(self, current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 2)

    def _generate_cache_key(self):
        return f"platform_overview_{self.days}"

    def clear_cache(self):
        cache.delete(self._generate_cache_key())
