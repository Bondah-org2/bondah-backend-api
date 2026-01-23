import random
import re

from django.core.exceptions import ValidationError

from .users import User


def validate_username_format(value):
    """Validate username format: letters, numbers, and underscore only"""
    if not re.match(r"^[a-zA-Z0-9_]+$", value):
        raise ValidationError(
            "Invalid characters, use letters/numbers and underscore only"
        )
    if len(value) < 3:
        raise ValidationError("Username must be at least 3 characters long")
    if len(value) > 30:
        raise ValidationError("Username must be less than 30 characters long")


class UsernameValidation:
    """Utility class for username validation and suggestions"""

    @staticmethod
    def is_username_available(username):
        """Check if username is available"""
        return not User.objects.filter(username=username).exists()

    @staticmethod
    def validate_username(username):
        """Validate username format and availability"""
        # Remove @ symbol if present
        clean_username = username.lstrip("@")

        # Validate format
        try:
            validate_username_format(clean_username)
        except ValidationError as e:
            return False, str(e), []

        # Check availability
        if UsernameValidation.is_username_available(clean_username):
            return True, "Nice pick! This username is yours.", []
        else:
            suggestions = UsernameValidation.generate_suggestions(clean_username)
            return False, "Username already taken.", suggestions

    @staticmethod
    def generate_suggestions(base_username):
        """Generate username suggestions based on base username"""
        suggestions = []
        clean_username = base_username.lstrip("@")

        # Add random numbers
        for _ in range(3):
            number = random.randint(10, 99)
            suggestion = f"{clean_username}_{number}"
            if UsernameValidation.is_username_available(suggestion):
                suggestions.append(suggestion)

        # Add 'x' suffix
        suggestion = f"{clean_username}x"
        if UsernameValidation.is_username_available(suggestion):
            suggestions.append(suggestion)

        # Add random letters
        for _ in range(2):
            letter = random.choice("abcdefghijklmnopqrstuvwxyz")
            suggestion = f"{clean_username}{letter}"
            if UsernameValidation.is_username_available(suggestion):
                suggestions.append(suggestion)

        return suggestions[:5]  # Return max 5 suggestions
