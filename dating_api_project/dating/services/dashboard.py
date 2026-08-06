# dashboard/services.py

from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count, Q

from ..models import (
    Activity,
    MatchRequest,
    Visibility,
    BondmakerSubscription,
    UserProfileView,
)

CACHE_TIMEOUT = 600  # seconds (10 minutes)
MATCHES_PER_LEVEL = 50


class BondmakerDashboardService:
    def __init__(self, user):
        self.user = user
        self.now = timezone.now()

    # ==========================
    # PUBLIC ENTRY POINT
    # ==========================
    def get_dashboard_data(self):
        cache_key = self._generate_cache_key()
        cached = cache.get(cache_key)
        if cached:
            return cached

        data = self._build_dashboard()
        cache.set(cache_key, data, CACHE_TIMEOUT)
        return data

    # ==========================
    # CACHE KEY GENERATION
    # ==========================
    def _generate_cache_key(self):
        return f"bondmaker_dashboard_{self.user.id}"

    def clear_cache(self):
        """Clear the cached dashboard for this bondmaker."""
        cache.delete(self._generate_cache_key())

    # ==========================
    # BUILD DASHBOARD
    # ==========================
    def _build_dashboard(self):
        return {
            **self._get_level_metrics(),
            **self._get_profile_metrics(),
            **self._get_engagement_metrics(),
            "recent_activity": self._get_recent_activity(),
        }

    # ==========================
    # LEVEL & MATCH METRICS
    # ==========================
    def _get_level_metrics(self):
        total_accepted_matches = MatchRequest.objects.filter(
            bondmaker=self.user, status="accepted"
        ).count()

        level = total_accepted_matches // MATCHES_PER_LEVEL + 1
        matches_in_current_level = total_accepted_matches % MATCHES_PER_LEVEL
        matches_to_next_level = (
            MATCHES_PER_LEVEL - matches_in_current_level
            if matches_in_current_level > 0
            else 0
        )
        progress_percentage = (
            100
            if matches_to_next_level == 0
            else int((matches_in_current_level / MATCHES_PER_LEVEL) * 100)
        )

        return {
            "level": level,
            "total_matches": total_accepted_matches,
            "matches_to_next_level": matches_to_next_level,
            "progress_to_next_level": progress_percentage,
        }

    # ==========================
    # LIVE PROFILES & SUBSCRIBERS
    # ==========================
    def _get_profile_metrics(self):
        active_subscriptions = BondmakerSubscription.objects.filter(
            bondmaker=self.user, active=True, end_date__gt=self.now
        )

        live_profiles = Visibility.objects.filter(
            bondmaker=self.user, status="approved", expires_at__gt=self.now
        ).count()

        return {
            "live_profiles": live_profiles,
            "net_subscribers": active_subscriptions.count(),
        }

    # ==========================
    # PROFILE VIEWS
    # ==========================
    def _get_engagement_metrics(self):
        client_ids = BondmakerSubscription.objects.filter(
            bondmaker=self.user, active=True, end_date__gt=self.now
        ).values_list("user_id", flat=True)

        profile_views = UserProfileView.objects.filter(
            viewed_user_id__in=client_ids
        ).count()

        return {"profile_views": profile_views}

    # ==========================
    # RECENT ACTIVITY
    # ==========================
    def _get_recent_activity(self):
        """
        Snapshot for the dashboard: events about the bondmaker themself
        (e.g. match_made) plus events about their active clients
        (profile views, gifts, likes) — sourced from the single Activity
        log instead of querying each event table separately.
        """
        client_ids = list(
            BondmakerSubscription.objects.filter(
                bondmaker=self.user, active=True, end_date__gt=self.now
            ).values_list("user_id", flat=True)
        )

        activities = (
            Activity.objects.filter(
                Q(recipient=self.user) | Q(recipient_id__in=client_ids)
            )
            .select_related("actor", "recipient")
            .order_by("-created_at")[:5]
        )

        return [
            {
                "type": activity.action,
                "message": activity.render_message(),
                "time": activity.created_at,
            }
            for activity in activities
        ]
