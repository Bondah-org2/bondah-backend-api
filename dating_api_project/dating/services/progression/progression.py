from typing import Any

from dating.services.progression.config import PROGRESSION_CONFIG


class ProgressionService:
    """
    Service responsible for calculating Bondmaker progression,
    connection levels, badge tiers, and progress metrics.
    """

    @staticmethod
    def calculate_level(matches: int) -> int:
        """
        Calculate current connection level based on total successful matches.
        """

        if matches < 0:
            raise ValueError("Successful matches cannot be negative")

        level = 0
        remaining_matches = matches

        for phase in PROGRESSION_CONFIG["phases"]:
            max_level = phase["max_level"]
            matches_per_level = phase["matches_per_level"]

            # Infinite terminal phase (Level 60+)
            if max_level == float("inf"):
                level += remaining_matches // matches_per_level
                return level

            levels_available = max_level - level
            matches_needed_for_phase = levels_available * matches_per_level

            # User is still within this phase
            if remaining_matches <= matches_needed_for_phase:
                level += remaining_matches // matches_per_level
                return level

            # Consume entire phase and continue
            level += levels_available
            remaining_matches -= matches_needed_for_phase

        return level

    @staticmethod
    def get_badge(level: int) -> str:
        """
        Return badge title based on current connection level.
        """

        for badge in PROGRESSION_CONFIG["badges"]:
            if badge["min_level"] <= level <= badge["max_level"]:
                return badge["title"]

        return "Uprising"

    @staticmethod
    def get_level_phase(level: int) -> dict[str, Any]:
        """
        Return the active progression phase based on level.
        """

        for phase in PROGRESSION_CONFIG["phases"]:
            if level <= phase["max_level"]:
                return phase

        return PROGRESSION_CONFIG["phases"][-1]

    @staticmethod
    def calculate_progress(matches: int) -> dict[str, Any]:
        """
        Calculate complete progression information required by the frontend.
        """

        if matches < 0:
            raise ValueError("Successful matches cannot be negative")

        level = ProgressionService.calculate_level(matches)
        badge = ProgressionService.get_badge(level)
        phase = ProgressionService.get_level_phase(level)

        matches_consumed = 0
        previous_max_level = 0

        for config_phase in PROGRESSION_CONFIG["phases"]:
            max_level = config_phase["max_level"]

            if max_level == float("inf"):
                break

            levels_in_phase = max_level - previous_max_level
            phase_matches = levels_in_phase * config_phase["matches_per_level"]

            if matches >= matches_consumed + phase_matches:
                matches_consumed += phase_matches
                previous_max_level = max_level
            else:
                break

        matches_in_current_phase = matches - matches_consumed

        matches_completed_within_level = (
            matches_in_current_phase % phase["matches_per_level"]
        )

        matches_required_for_next_level = phase["matches_per_level"]

        progress_percentage = (
            matches_completed_within_level / matches_required_for_next_level
        ) * 100

        return {
            "level": level,
            "badge": badge,
            "matches_completed_within_level": matches_completed_within_level,
            "matches_required_for_next_level": matches_required_for_next_level,
            "progress_percentage_gauge": round(progress_percentage, 1),
        }
        