from django.test import override_settings
from django.test import TestCase
from django.urls import reverse
# pyrefly: ignore [missing-import]
from rest_framework.test import APITestCase
# pyrefly: ignore [missing-import]
from rest_framework import status

from dating.models import User, MatchRequest, UserMatch
# pyrefly: ignore [missing-import]
from dating.services.progression.progression import ProgressionService
from unittest.mock import patch
from django.db import connection
from threading import Thread



class ProgressionServiceTestCase(TestCase):
    """Unit tests for ProgressionService."""

    def test_negative_matches_raise_exception(self):
        with self.assertRaises(ValueError):
            ProgressionService.calculate_level(-1)

    def test_level_zero(self):
        self.assertEqual(
            ProgressionService.calculate_level(0),
            0
        )

    def test_first_level_boundary(self):
        self.assertEqual(
            ProgressionService.calculate_level(500),
            1
        )

    def test_multiple_levels_first_phase(self):
        self.assertEqual(
            ProgressionService.calculate_level(2500),
            5
        )

    def test_last_level_first_phase(self):
        self.assertEqual(
            ProgressionService.calculate_level(10000),
            20
        )

    def test_second_phase_starts(self):
        self.assertEqual(
            ProgressionService.calculate_level(10800),
            21
        )

    def test_badge_uprising(self):
        self.assertEqual(
            ProgressionService.get_badge(0),
            "Uprising"
        )

    def test_badge_connector(self):
        self.assertEqual(
            ProgressionService.get_badge(10),
            "Connector"
        )

    def test_badge_influencer(self):
        self.assertEqual(
            ProgressionService.get_badge(30),
            "Expert"
        )

    def test_badge_legend(self):
        self.assertEqual(
            ProgressionService.get_badge(55),
            "Professional"
        )

    def test_badge_principal(self):
        self.assertEqual(
            ProgressionService.get_badge(75),
            "Principal"
        )

    def test_progress_structure(self):
        progress = ProgressionService.calculate_progress(750)

        self.assertIn("level", progress)
        self.assertIn("badge", progress)
        self.assertIn("matches_completed_within_level", progress)
        self.assertIn("matches_required_for_next_level", progress)
        self.assertIn("progress_percentage_gauge", progress)

    def test_progress_values(self):
        progress = ProgressionService.calculate_progress(750)

        self.assertEqual(progress["level"], 1)
        self.assertEqual(
            progress["matches_completed_within_level"],
            250
        )
        self.assertEqual(
            progress["matches_required_for_next_level"],
            500
        )
        self.assertEqual(
            progress["progress_percentage_gauge"],
            50.0
        )
    
    def test_level_10_boundary_transition(self):
        progress = ProgressionService.calculate_progress(5000)

        self.assertEqual(progress["level"], 10)
        self.assertEqual(progress["badge"], "Connector")

@override_settings(RATELIMIT_ENABLE=False)
@patch("dating.signals.notify_user.delay")
class BondmakerProgressionSignalTestCase(TestCase):

    def setUp(self):
        self.bondmaker = User.objects.create_user(
            email="bondmaker@test.com",
            password="password",
            is_matchmaker=True,
        )

        self.user1 = User.objects.create_user(
            email="user1@test.com",
            password="password",
        )

        self.user2 = User.objects.create_user(
            email="user2@test.com",
            password="password",
        )

        self.match_request = MatchRequest.objects.create(
            requester=self.user1,
            bondmaker=self.bondmaker,
            coins_charged=10,
            platform_revenue=2,
            bondmaker_earning=8,
        )

        self.match = UserMatch.objects.create(
            match_request=self.match_request,
            user1=self.user1,
            user2=self.user2,
            distance=3.5,
            match_score=91.5,
            status="pending",
        )

    def test_match_completion_increments_successful_matches(self, mock_delay):

        self.match.status = "matched"
        self.match.save()

        self.bondmaker.refresh_from_db()

        self.assertEqual(
            self.bondmaker.cumulative_successful_matches,
            1
        )

    def test_level_is_updated(self, mock_delay):

        self.bondmaker.cumulative_successful_matches = 499
        self.bondmaker.save()

        self.match.status = "matched"
        self.match.save()

        self.bondmaker.refresh_from_db()

        self.assertEqual(
            self.bondmaker.current_cached_level,
            1
        )

    def test_badge_updates(self, mock_delay):

        self.bondmaker.cumulative_successful_matches = 4999
        self.bondmaker.current_cached_level = 9
        self.bondmaker.save()

        self.match.status = "matched"
        self.match.save()

        self.bondmaker.refresh_from_db()

        self.assertEqual(
            self.bondmaker.current_cached_badge_tier,
            "Connector"
        )

    def test_last_level_up_is_set(self, mock_delay):

        self.bondmaker.cumulative_successful_matches = 499
        self.bondmaker.save()

        self.assertIsNone(
            self.bondmaker.last_level_up_at
        )

        self.match.status = "matched"
        self.match.save()

        self.bondmaker.refresh_from_db()

        self.assertIsNotNone(
            self.bondmaker.last_level_up_at
        )

    def test_signal_only_runs_once(self, mock_delay):

        self.match.status = "matched"
        self.match.save()

        # Reload so progression_processed=True is loaded
        self.match.refresh_from_db()

        self.match.save()

        self.bondmaker.refresh_from_db()

        self.assertEqual(
            self.bondmaker.cumulative_successful_matches,
            1
        )


    def test_cached_level_matches_calculated_level_after_multiple_matches(
        self,
        mock_delay,
    ):
        self.bondmaker.cumulative_successful_matches = 499
        self.bondmaker.save()

        self.match.status = "matched"
        self.match.save()

        self.bondmaker.refresh_from_db()

        expected_level = ProgressionService.calculate_level(
            self.bondmaker.cumulative_successful_matches
        )

        self.assertEqual(
            self.bondmaker.current_cached_level,
            expected_level
        )

@override_settings(RATELIMIT_ENABLE=False)
class BondmakerProgressionAPITestCase(APITestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            email="bondmaker@test.com",
            password="password",
            is_matchmaker=True,
            cumulative_successful_matches=750,
            current_cached_level=1,
            current_cached_badge_tier="Uprising",
        )

        self.client.force_authenticate(
            self.user
        )

        self.url = reverse(
            "bondmaker-progression"
        )

    def test_returns_200(self):

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

    def test_response_contains_expected_keys(self):

        response = self.client.get(self.url)

        self.assertIn(
            "bondmaker_id",
            response.data
        )

        self.assertIn(
            "metrics",
            response.data
        )

        self.assertIn(
            "ui_progress_tracker",
            response.data
        )

    def test_metrics_are_correct(self):

        response = self.client.get(self.url)

        metrics = response.data["metrics"]

        self.assertEqual(
            metrics["current_level"],
            1
        )

        self.assertEqual(
            metrics["badge_tier"],
            "Uprising"
        )

        self.assertEqual(
            metrics["cumulative_successful_matches"],
            750
        )

    def test_progress_tracker(self):

        response = self.client.get(self.url)

        tracker = response.data["ui_progress_tracker"]

        self.assertEqual(
            tracker["current_connection_level_string"],
            "Level 1"
        )

        self.assertEqual(
            tracker["matches_completed_within_level"],
            250
        )

        self.assertEqual(
            tracker["matches_required_for_next_level"],
            500
        )

        self.assertEqual(
            tracker["progress_percentage_gauge"],
            50.0
        )

    def test_requires_authentication(self):

        self.client.logout()

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )
    
    def test_progress_percentage_is_valid(self):
        response = self.client.get(self.url)

        percentage = response.data["ui_progress_tracker"][
            "progress_percentage_gauge"
        ]

        self.assertGreaterEqual(
            percentage,
            0.0
        )

        self.assertLessEqual(
            percentage,
            100.0
        )

# SQL Verification Test
def test_cached_level_matches_sql_match_count(self, mock_delay):
    self.bondmaker.cumulative_successful_matches = 5000
    self.bondmaker.current_cached_level = 10
    self.bondmaker.save()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT cumulative_successful_matches
            FROM dating_user
            WHERE id = %s
            """,
            [self.bondmaker.id],
        )

        sql_matches = cursor.fetchone()[0]

    expected_level = ProgressionService.calculate_level(sql_matches)

    self.bondmaker.refresh_from_db()

    self.assertEqual(
        self.bondmaker.current_cached_level,
        expected_level,
    )


# Duplicate Concurrent Signal Test
def test_concurrent_match_completion_only_counts_once(self, mock_delay):

    def complete_match():
        match = UserMatch.objects.get(pk=self.match.pk)
        match.status = "matched"
        match.save()

    threads = [
        Thread(target=complete_match),
        Thread(target=complete_match),
        Thread(target=complete_match),
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    self.bondmaker.refresh_from_db()

    self.assertEqual(
        self.bondmaker.cumulative_successful_matches,
        1,
    )

    self.match.refresh_from_db()

    self.assertTrue(
        self.match.progression_processed,
    )


# Match Reversal Test
def test_reversal_decrements_match_count(self, mock_delay):

    self.match.status = "matched"
    self.match.save()

    self.bondmaker.refresh_from_db()

    self.assertEqual(
        self.bondmaker.cumulative_successful_matches,
        1,
    )

    self.match.status = "blocked"
    self.match.save()

    self.bondmaker.refresh_from_db()

    self.assertEqual(
        self.bondmaker.cumulative_successful_matches,
        0,
    )


# Badge Downgrade Test
def test_badge_downgrades_after_reversal(self, mock_delay):

    self.bondmaker.cumulative_successful_matches = 5000
    self.bondmaker.current_cached_level = 10
    self.bondmaker.current_cached_badge_tier = "Connector"
    self.bondmaker.save()

    self.match.status = "matched"
    self.match.progression_processed = True
    self.match.save()

    self.bondmaker.cumulative_successful_matches = 4999
    self.bondmaker.save()

    self.match.status = "blocked"
    self.match.save()

    self.bondmaker.refresh_from_db()

    self.assertEqual(
        self.bondmaker.current_cached_badge_tier,
        "Uprising",
    )


# Level Downgrade Test
def test_level_downgrades_after_reversal(self, mock_delay):

    self.bondmaker.cumulative_successful_matches = 5000
    self.bondmaker.current_cached_level = 10
    self.bondmaker.save()

    self.match.status = "matched"
    self.match.progression_processed = True
    self.match.save()

    self.bondmaker.cumulative_successful_matches = 4999
    self.bondmaker.save()

    self.match.status = "blocked"
    self.match.save()

    self.bondmaker.refresh_from_db()

    self.assertEqual(
        self.bondmaker.current_cached_level,
        9,
    )


# Terminal Phase Support Test
def test_terminal_phase_support(self):

    progress = ProgressionService.calculate_progress(250000)

    self.assertGreaterEqual(
        progress["level"],
        60,
    )

    self.assertIsInstance(
        progress["level"],
        int,
    )


# Negative Match Count Test
def test_reversal_never_creates_negative_match_count(self, mock_delay):

    self.assertEqual(
        self.bondmaker.cumulative_successful_matches,
        0,
    )

    self.match.status = "blocked"
    self.match.save()

    self.bondmaker.refresh_from_db()

    self.assertEqual(
        self.bondmaker.cumulative_successful_matches,
        0,
    )


# Level Up Notification Test
def test_level_up_notification_sent(self, mock_delay):

    self.bondmaker.cumulative_successful_matches = 499
    self.bondmaker.save()

    self.match.status = "matched"
    self.match.save()

    mock_delay.assert_called_once()


# Match Processed Flag Test
def test_match_is_marked_processed(self, mock_delay):

    self.match.status = "matched"
    self.match.save()

    self.match.refresh_from_db()

    self.assertTrue(
        self.match.progression_processed,
    )
