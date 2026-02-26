# dashboard/services.py

from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count

from ..models import MatchRequest, Visibility, BondmakerSubscription, UserProfileView

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
        recent_activity = []

        client_ids = BondmakerSubscription.objects.filter(
            bondmaker=self.user, active=True, end_date__gt=self.now
        ).values_list("user_id", flat=True)

        # Recent profile views
        recent_views = (
            UserProfileView.objects.filter(viewed_user_id__in=client_ids)
            .select_related("viewer", "viewed_user")
            .order_by("-viewed_at")[:5]
        )
        for view in recent_views:
            recent_activity.append(
                {
                    "type": "profile_view",
                    "viewer_name": view.viewer.name or view.viewer.username,
                    "viewer_country": view.viewer.country,
                    "viewed_client_name": view.viewed_user.name
                    or view.viewed_user.username,
                    "source": view.source,
                    "time": view.viewed_at,
                }
            )

        # Recent accepted matches
        recent_matches = (
            MatchRequest.objects.filter(bondmaker=self.user, status="accepted")
            .select_related("requester")
            .order_by("-created_at")[:5]
        )
        for match in recent_matches:
            recent_activity.append(
                {
                    "type": "match_accepted",
                    "requester_name": match.requester.name or match.requester.username,
                    "coins_charged": match.coins_charged,
                    "time": match.created_at,
                }
            )
