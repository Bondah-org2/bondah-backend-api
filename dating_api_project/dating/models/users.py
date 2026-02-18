import random
import string
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import re
from django.core.exceptions import ValidationError
from datetime import timedelta
from django.conf import settings
import uuid
from dating.location_utils import reverse_geocode, get_approximate_location_from_ip
from datetime import date
from .user_manager import UserManager


class Specialisation(models.Model):

    class Category(models.TextChoices):
        CASUAL = "casual", "Casual Dating"
        LGBTQ = "lgbtq", "LGBTQ+"
        LAVENDER = "lavender", "Lavender Marriage"
        SUGAR = "sugar", "Sugar Relationship"
        MARRIAGE = "marriage", "Marriage-Oriented"
        COMPANIONSHIP = "companionship", "Companionship"
        CULTURAL = "cultural", "Cultural Matching"
        ELITE = "elite", "Elite Only Matching"
        WIDOW = "widow", "Widow/Widower Matchmaking"
        DIVORCED = "divorced", "Divorced/Single Parent Matching"
        CAREER = "career", "Career Focused Matching"
        ARABS = "arabs", "Arabs/Khaṭṭābah Matching"
        HINDI = "hindi", "Hindi/Punjabi Matching"
        CHRISTIAN = "christian", "Christian Matching"
        ISLAM = "islam", "Islam Matching"

    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        unique=True,
    )

    def __str__(self):
        return self.get_category_display()


class User(AbstractUser):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    gender = models.CharField(
        max_length=20,
        choices=[
            ("male", "Male"),
            ("female", "Female"),
            ("trans_man", "Trans Man"),
            ("trans_woman", "Trans Womman"),
            ("non_binary", "Non Binary"),
        ],
        blank=True,
        null=True,
    )
    username = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
    )
    date_of_birth = models.DateField(null=True, blank=True)
    phone_number = models.CharField(blank=True, null=True)
    traits = models.JSONField(default=list, blank=True, null=True)

    # Location Fields
    location = models.CharField(
        max_length=100, blank=True, null=True
    )  # Keep for backward compatibility
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        blank=True,
        null=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        blank=True,
        null=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )

    AVAILABILITY_CHOICES = (
        ("online", "Online"),
        ("offline", "Offline"),
    )

    availability_status = models.CharField(
        max_length=10, choices=AVAILABILITY_CHOICES, default="offline", null=True
    )

    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    state = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    country = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    deal_breaker = models.CharField(max_length=100, blank=True, null=True)
    partner_qualities = models.JSONField(default=list, blank=True, null=True)
    specialisations = models.ManyToManyField(
        Specialisation, blank=True, related_name="bondmakers"
    )

    # Location Privacy Settings
    location_privacy = models.CharField(
        max_length=20,
        choices=[
            ("public", "Public"),
            ("friends", "Friends Only"),
            ("private", "Private"),
            ("hidden", "Hidden"),
        ],
        default="public",
    )
    location_sharing_enabled = models.BooleanField(default=True)
    location_update_frequency = models.CharField(
        max_length=20,
        choices=[
            ("realtime", "Real-time"),
            ("hourly", "Hourly"),
            ("daily", "Daily"),
            ("manual", "Manual Only"),
        ],
        default="manual",
    )

    # Dating App Specific Fields
    is_matchmaker = models.BooleanField(default=False)
    bio = models.TextField(blank=True)
    last_location_update = models.DateTimeField(blank=True, null=True)

    # Profile Pictures
    profile_picture = models.URLField(
        blank=True, null=True, help_text="Main profile picture URL"
    )
    profile_gallery = models.JSONField(
        default=list, help_text="Array of additional profile picture URLs"
    )

    # Personal Information (From Figma Designs)
    # Basic Info
    education_level = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ("high_school", "High School"),
            ("undergrad", "Undergraduate"),
            ("bachelors", "Bachelor's Degree"),
            ("masters", "Master's Degree"),
            ("phd", "PhD"),
            ("other", "Other"),
        ],
    )
    height = models.CharField(
        max_length=10, blank=True, null=True, help_text="Height in feet/inches or cm"
    )
    zodiac_sign = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ("aries", "Aries"),
            ("taurus", "Taurus"),
            ("gemini", "Gemini"),
            ("cancer", "Cancer"),
            ("leo", "Leo"),
            ("virgo", "Virgo"),
            ("libra", "Libra"),
            ("scorpio", "Scorpio"),
            ("sagittarius", "Sagittarius"),
            ("capricorn", "Capricorn"),
            ("aquarius", "Aquarius"),
            ("pisces", "Pisces"),
        ],
    )

    GENOTYPE_CHOICES = [
        ("AA", "AA"),
        ("AS", "AS"),
        ("SS", "SS"),
        ("AC", "AC"),
        ("SC", "SC"),
        ("PNTS", "Prefer not to say"),
    ]

    genotype = models.CharField(
        max_length=4,
        choices=GENOTYPE_CHOICES,
        null=True,
        blank=True,
        help_text="User's genotype (optional)",
    )

    languages = models.JSONField(
        default=list, help_text="Languages spoken (e.g., ['English', 'French'])"
    )
    relationship_status = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ("single", "Single"),
            ("divorced", "Divorced"),
            ("widowed", "Widowed"),
            ("separated", "Separated"),
            ("engaged", "Engaged"),
            ("married", "Married")
        ],
    )

    # Lifestyle & Preferences
    smoking_preference = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ("never", "Never"),
            ("occasionally", "Occasionally"),
            ("regularly", "Regularly"),
            ("quit", "Quit"),
        ],
    )

    last_seen = models.DateTimeField(null=True, blank=True)

    drinking_preference = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ("never", "Never"),
            ("occasionally", "Occasionally"),
            ("regularly", "Regularly"),
            ("quit", "Quit"),
        ],
    )
    pet_preference = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ("dog", "Dog"),
            ("cat", "Cat"),
            ("both", "Both"),
            ("none", "None"),
            ("other", "Other"),
        ],
    )
    exercise_frequency = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ("never", "Never"),
            ("1x_week", "1x/week"),
            ("2x_week", "2x/week"),
            ("3x_week", "3x/week"),
            ("4x_week", "4x/week"),
            ("5x_week", "5x/week"),
            ("daily", "Daily"),
        ],
    )
    # Personality & Communication
    personality_type = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        choices=[
            ("INTJ", "INTJ"),
            ("INTP", "INTP"),
            ("ENTJ", "ENTJ"),
            ("ENTP", "ENTP"),
            ("INFJ", "INFJ"),
            ("INFP", "INFP"),
            ("ENFJ", "ENFJ"),
            ("ENFP", "ENFP"),
            ("ISTJ", "ISTJ"),
            ("ISFJ", "ISFJ"),
            ("ESTJ", "ESTJ"),
            ("ESFJ", "ESFJ"),
            ("ISTP", "ISTP"),
            ("ISFP", "ISFP"),
            ("ESTP", "ESTP"),
            ("ESFP", "ESFP"),
        ],
    )
    love_language = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ("physical_touch", "Physical Touch"),
            ("gifts", "Gifts"),
            ("quality_time", "Quality Time"),
            ("words_of_affirmation", "Words of Affirmation"),
            ("acts_of_service", "Acts of Service"),
        ],
    )
    communication_style = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ("direct", "Direct"),
            ("romantic", "Romantic"),
            ("playful", "Playful"),
            ("reserved", "Reserved"),
        ],
    )

    # Interests & Hobbies
    hobbies = models.JSONField(default=list, help_text="List of hobbies and interests")
    interests = models.JSONField(default=list, blank=True, null=True, help_text="List of general interests")

    # Future Plans & Values
    marriage_plans = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[("yes", "Yes"), ("no", "No"), ("maybe", "Maybe")],
    )
    have_kids = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[("yes", "Yes"), ("no", "No")],
    )

    no_of_kids = models.IntegerField(
        blank=True,
        null=True,
    )

    future_kids = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[("yes", "Yes"), ("no", "No"), ("maybe", "Maybe")],
    )

    religion_importance = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ("very", "Very Important"),
            ("somewhat", "Somewhat Important"),
            ("not_at_all", "Not At All"),
        ],
    )
    religion = models.CharField(max_length=50, blank=True, null=True)

    # Dating Preferences
    dating_type = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ("casual", "Casual Dating"),
            ("serious", "Serious Relationship"),
            ("marriage", "Marriage"),
            ("sugar", "Sugar Relationship"),
            ("friendship", "Friendship"),
            ("short_term", "Short Term"),
            ("not_sure_yet", "Not Sure Yet")
        ],
    )
    open_to_long_distance = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[("yes", "Yes"), ("no", "No"), ("maybe", "Maybe")],
    )

    # Matching Preferences
    max_distance = models.PositiveIntegerField(
        default=50, help_text="Maximum distance in kilometers"
    )
    age_range_min = models.PositiveIntegerField(default=18)
    age_range_max = models.PositiveIntegerField(default=100)
    preferred_gender = models.CharField(
        max_length=10,
        choices=[("male", "Male"), ("female", "Female"), ("others", "Others")],
        blank=True,
        null=True,
    )

    # What I'm Looking For (From Figma Design)
    looking_for = models.TextField(
        blank=True,
        null=True,
        help_text="Free text describing what the user is looking for",
    )

    # Notification Settings (From Figma Design)
    push_notifications_enabled = models.BooleanField(
        default=True, help_text="Enable push notifications"
    )
    email_notifications_enabled = models.BooleanField(
        default=True, help_text="Enable email notifications"
    )

    # Language Settings (From Figma Design)
    preferred_language = models.CharField(
        max_length=10, default="en", help_text="User's preferred app language"
    )

    # Bondcoin Wallet (From Figma Design)
    bondcoin_balance = models.PositiveIntegerField(
        default=0, help_text="User's Bondcoin balance"
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

    @property
    def has_location(self):
        """Check if user has valid GPS coordinates"""
        return self.latitude is not None and self.longitude is not None

    def get_profile_completion_percentage(self):
        """Calculate profile completion percentage based on filled fields"""
        required_fields = [
            "name",
            "email",
            "gender",
            "age",
            "bio",
            "profile_picture",
            "education_level",
            "height",
            "zodiac_sign",
            "languages",
            "smoking_preference",
            "drinking_preference",
            "exercise_frequency",
            "personality_type",
            "love_language",
            "communication_style",
            "hobbies",
            "interests",
            "looking_for",
        ]

        filled_fields = 0
        total_fields = len(required_fields)

        for field_name in required_fields:
            field_value = getattr(self, field_name, None)
            if (
                field_value is not None
                and field_value != ""
                and field_value != []
                and field_value != {}
            ):
                filled_fields += 1

        # Add bonus for profile gallery
        if self.profile_gallery and len(self.profile_gallery) > 0:
            filled_fields += 1
            total_fields += 1

        return min(100, int((filled_fields / total_fields) * 100))

    def get_current_subscription(self):
        """Get user's current active subscription"""
        from django.utils import timezone

        current_subscription = self.subscriptions.filter(
            status="active", end_date__gt=timezone.now()
        ).first()
        return current_subscription

    def has_feature_access(self, feature_name):
        """Check if user has access to a specific feature based on subscription"""
        subscription = self.get_current_subscription()
        if not subscription:
            return False

        plan = subscription.plan
        feature_map = {
            "unlimited_swipes": plan.unlimited_swipes,
            "undo_swipes": plan.undo_swipes,
            "unlimited_unwind": plan.unlimited_unwind,
            "global_access": plan.global_access,
            "read_receipt": plan.read_receipt,
        }

        return feature_map.get(feature_name, False)

    def get_live_hours_days(self):
        """Get live hours days based on subscription"""
        subscription = self.get_current_subscription()
        if subscription:
            return subscription.plan.live_hours_days
        return 7  # Default for free users

    @property
    def location_coordinates(self):
        """Get location as tuple of (latitude, longitude)"""
        if self.has_location:
            return (float(self.latitude), float(self.longitude))
        return None

    def get_distance_to(self, other_user):
        """Calculate distance to another user in kilometers"""
        if not (self.has_location and other_user.has_location):
            return None

        from ..location_utils import calculate_distance

        return calculate_distance(
            self.location_coordinates, other_user.location_coordinates
        )

    @property
    def age(self) -> int:
        if not self.date_of_birth:
            return None

        today = date.today()
        return (
            today.year
            - self.date_of_birth.year
            - (
                (today.month, today.day)
                < (self.date_of_birth.month, self.date_of_birth.day)
            )
        )

    _request_ip = None  # internal use, not DB field

    def set_request_ip(self, ip: str):
        """Optional: set IP for fallback location if GPS not available"""
        self._request_ip = ip

    def save(self, *args, **kwargs):
        """Override save to compute location automatically"""
        try:
            # Only compute location if sharing enabled
            if self.location_sharing_enabled:
                if self.latitude and self.longitude:
                    # Use GPS first
                    data = reverse_geocode(float(self.latitude), float(self.longitude))
                    if data:
                        self.city = data.get("city", self.city)
                        self.state = data.get("state", self.state)
                        self.country = data.get("country", self.country)
                elif self._request_ip:
                    # Fallback to IP geolocation
                    ip_data = get_approximate_location_from_ip(self._request_ip)
                    if ip_data:
                        self.latitude = ip_data.get("latitude", self.latitude)
                        self.longitude = ip_data.get("longitude", self.longitude)
                        self.city = ip_data.get("city", self.city)
                        self.state = ip_data.get("state", self.state)
                        self.country = ip_data.get("country", self.country)

                # Only include state and country in location
                parts = filter(None, [self.state, self.country])
                self.location = ", ".join(parts) if parts else None
            else:
                self.location = None
        except Exception as e:
            print(f"Error computing location: {e}")

        super().save(*args, **kwargs)


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    date_subscribed = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class PuzzleVerification(models.Model):
    """
    Tracks a user's attempt at solving a puzzle.
    Also includes a static method to generate new random puzzles.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="puzzle_attempts"
    )
    question = models.CharField(max_length=255)
    answer = models.CharField(max_length=50)  # correct answer (hidden from user)
    user_answer = models.CharField(max_length=50, blank=True)
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Puzzle Verification"
        verbose_name_plural = "Puzzle Verifications"
        ordering = ["-created_at"]

    def __str__(self):
        status = "Correct" if self.is_correct else "Pending"
        return f"Puzzle for {self.user.name} – {status}"

    def verify_answer(self):
        """
        Compares user's answer with the correct answer and updates is_correct.
        Returns True if correct, False otherwise.
        """
        self.is_correct = self.user_answer.strip() == self.answer.strip()
        self.save(update_fields=["is_correct"])
        return self.is_correct

    @staticmethod
    def generate_puzzle():
        """
        Generates a simple random addition puzzle.
        Returns a tuple: (question, answer)
        """
        num1 = random.randint(1, 20)
        num2 = random.randint(1, 20)
        question = f"What is {num1} + {num2}?"
        answer = str(num1 + num2)
        return question, answer


# class CoinTransaction(models.Model):
#     TRANSACTION_TYPES = (
#         ("earn", "Earn"),
#         ("spend", "Spend"),
#     )

#     user = models.ForeignKey("User", on_delete=models.CASCADE)
#     transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
#     amount = models.PositiveIntegerField()
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.user.name} - {self.transaction_type} {self.amount} coins"


class Waitlist(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email}"

    class Meta:
        ordering = ["-date_joined"]


class EmailLog(models.Model):
    EMAIL_TYPES = (
        ("newsletter_welcome", "Newsletter Welcome"),
        ("waitlist_confirmation", "Waitlist Confirmation"),
        ("generic", "Generic Email"),
    )

    email_type = models.CharField(max_length=50, choices=EMAIL_TYPES)
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_sent = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.email_type} to {self.recipient_email} - {'Sent' if self.is_sent else 'Failed'}"

    class Meta:
        ordering = ["-sent_at"]


class Job(models.Model):
    JOB_TYPES = (
        ("full-time", "Full-time"),
        ("part-time", "Part-time"),
        ("contract", "Contract"),
        ("internship", "Internship"),
        ("freelance", "Freelance"),
    )

    CATEGORIES = (
        ("engineering", "Engineering"),
        ("design", "Design"),
        ("marketing", "Marketing"),
        ("sales", "Sales"),
        ("product", "Product"),
        ("operations", "Operations"),
        ("hr", "Human Resources"),
        ("finance", "Finance"),
        ("other", "Other"),
    )

    STATUS_CHOICES = (
        ("open", "Open"),
        ("closed", "Closed"),
        ("draft", "Draft"),
        ("archived", "Archived"),
    )

    title = models.CharField(max_length=200)
    job_type = models.CharField(max_length=20, choices=JOB_TYPES)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    description = models.TextField()
    location = models.CharField(max_length=100)
    salary_range = models.CharField(max_length=100, blank=True, null=True)
    requirements = models.JSONField(default=list)  # Store as JSON array
    responsibilities = models.TextField(blank=True, null=True)  # New field
    benefits = models.TextField(blank=True, null=True)  # New field
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.get_job_type_display()}"

    class Meta:
        ordering = ["-created_at"]


class JobApplication(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("reviewed", "Reviewed"),
        ("shortlisted", "Shortlisted"),
        ("interviewed", "Interviewed"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    )

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    resume_url = models.URLField(blank=True, null=True)  # Link to uploaded resume
    cover_letter = models.TextField(blank=True, null=True)
    experience_years = models.PositiveIntegerField(blank=True, null=True)
    current_company = models.CharField(max_length=100, blank=True, null=True)
    expected_salary = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.job.title}"

    class Meta:
        ordering = ["-applied_at"]
        unique_together = ["job", "email"]  # Prevent duplicate applications


class AdminUser(models.Model):
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  # Will be hashed
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Admin: {self.email}"

    class Meta:
        verbose_name = "Admin User"
        verbose_name_plural = "Admin Users"


class AdminOTP(models.Model):
    admin_user = models.ForeignKey(AdminUser, on_delete=models.CASCADE)
    otp_code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"OTP for {self.admin_user.email}"

    def is_expired(self):
        return timezone.now() > self.expires_at

    class Meta:
        ordering = ["-created_at"]


class TranslationLog(models.Model):
    source_text = models.TextField()
    translated_text = models.TextField()
    source_language = models.CharField(max_length=10)  # e.g., 'en', 'es', 'fr'
    target_language = models.CharField(max_length=10)
    character_count = models.PositiveIntegerField()
    translation_time = models.DurationField(help_text="Translation time in seconds")
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.source_language} → {self.target_language} ({self.character_count} chars)"

    class Meta:
        ordering = ["-created_at"]


class SocialAccount(models.Model):
    """Store social account information for OAuth users"""

    PROVIDER_CHOICES = (
        ("google", "Google"),
        ("apple", "Apple"),
        ("facebook", "Facebook"),
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="social_accounts"
    )
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_user_id = models.CharField(max_length=255)  # ID from the provider
    provider_data = models.JSONField(default=dict)  # Store additional provider data
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.provider}"

    class Meta:
        unique_together = ["provider", "provider_user_id"]
        ordering = ["-created_at"]


class DeviceRegistration(models.Model):
    """Store device information for push notifications"""

    DEVICE_TYPE_CHOICES = (
        ("ios", "iOS"),
        ("android", "Android"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="devices")
    device_id = models.CharField(max_length=255, unique=True)
    device_type = models.CharField(max_length=10, choices=DEVICE_TYPE_CHOICES)
    push_token = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.device_type} ({self.device_id[:8]}...)"

    class Meta:
        ordering = ["-created_at"]


class LocationHistory(models.Model):
    """Store user location history for tracking and privacy"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="location_history"
    )
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    accuracy = models.FloatField(
        blank=True, null=True, help_text="GPS accuracy in meters"
    )
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    source = models.CharField(
        max_length=20,
        choices=[
            ("gps", "GPS"),
            ("network", "Network"),
            ("manual", "Manual"),
            ("ip", "IP Address"),
        ],
        default="gps",
    )

    def __str__(self):
        return (
            f"{self.user.email} - {self.timestamp} ({self.latitude}, {self.longitude})"
        )

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "timestamp"], name="user_timestamp_idx"),
            models.Index(fields=["timestamp"]),
        ]


class UserInterest(models.Model):
    """Store user interests and hobbies for better matching"""

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(
        max_length=50,
        choices=[
            ("sports", "Sports"),
            ("music", "Music"),
            ("travel", "Travel"),
            ("food", "Food"),
            ("art", "Art"),
            ("technology", "Technology"),
            ("fitness", "Fitness"),
            ("reading", "Reading"),
            ("movies", "Movies"),
            ("gaming", "Gaming"),
            ("outdoor", "Outdoor Activities"),
            ("other", "Other"),
        ],
    )
    icon = models.CharField(
        max_length=50, blank=True, null=True, help_text="Icon name for UI"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class UserProfileView(models.Model):
    """Track profile views for analytics and recommendations"""

    viewer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="profile_views_made"
    )
    viewed_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="profile_views_received"
    )
    viewed_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(
        max_length=20,
        choices=[
            ("search", "Search Results"),
            ("discover", "Discover Feed"),
            ("nearby", "Nearby Users"),
            ("recommended", "Recommended"),
            ("direct", "Direct Link"),
        ],
        default="search",
    )

    def __str__(self):
        return f"{self.viewer.email} viewed {self.viewed_user.email}"

    class Meta:
        unique_together = ["viewer", "viewed_user"]
        ordering = ["-viewed_at"]


class UserInteraction(models.Model):
    """Track user interactions (likes, dislikes, super likes, etc.)"""

    INTERACTION_TYPES = [
        ("like", "Like"),
        ("dislike", "Dislike"),
        ("super_like", "Super Like"),
        ("pass", "Pass"),
        ("block", "Block"),
        ("report", "Report"),
        ("request_live", "Request Live"),
        ("share_profile", "Share Profile"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="interactions_made"
    )
    target_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="interactions_received"
    )
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, help_text="Additional interaction data")

    def __str__(self):
        return f"{self.user.email} {self.interaction_type} {self.target_user.email}"

    class Meta:
        unique_together = ["user", "target_user", "interaction_type"]
        ordering = ["-created_at"]


class SearchQuery(models.Model):
    """Store search queries for analytics and suggestions"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="search_queries"
    )
    query = models.CharField(max_length=255)
    filters = models.JSONField(default=dict, help_text="Applied filters")
    results_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email}: {self.query}"

    class Meta:
        ordering = ["-created_at"]


class RecommendationEngine(models.Model):
    """Store recommendation algorithm data"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="recommendations"
    )
    recommended_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="recommended_to"
    )
    score = models.FloatField(help_text="Recommendation score (0-100)")
    algorithm = models.CharField(
        max_length=50,
        choices=[
            ("location_based", "Location Based"),
            ("interest_based", "Interest Based"),
            ("compatibility", "Compatibility"),
            ("hybrid", "Hybrid"),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.email} -> {self.recommended_user.email} ({self.score})"

    class Meta:
        unique_together = ["user", "recommended_user"]
        ordering = ["-score"]


class LocationPermission(models.Model):
    """Store user location permission settings"""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="location_permissions"
    )
    location_enabled = models.BooleanField(default=False)
    background_location_enabled = models.BooleanField(default=False)
    precise_location_enabled = models.BooleanField(default=False)
    location_services_consent = models.BooleanField(default=False)
    location_data_sharing = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - Location Permissions"

    class Meta:
        ordering = ["-updated_at"]


class BondmakerSubscription(models.Model):
    """A user subscribed to a bondmaker"""

    bondmaker = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="subscribed_users"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="bondmaker_subscription"
    )
    start_date = models.DateTimeField(auto_now=True)
    end_date = models.DateTimeField()
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = (
            "bondmaker",
            "user",
        )  # One active subscription per user per bondmaker

    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date = self.start_date + timedelta(days=30)  # 1 month default
        super().save(*args, **kwargs)

    def is_active(self):
        if timezone.now() > self.end_date:
            self.active = False
            self.save(update_fields=["active"])
        return self.active


class Visibility(models.Model):

    VISIBILITY_CHOICES = (
            ('private', 'Private'),
            ('public', 'Public'),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="visibility_settings"
    )
    bondmaker = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="visible_to_users"
    )
    visibility = models.CharField(
        max_length=20, choices=VISIBILITY_CHOICES,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ("owner", "bondmaker")
        indexes = [
            models.Index(fields=["bondmaker", "status", "visibility"]),
            models.Index(fields=["expires_at"]),
        ]

    @property
    def is_active(self) -> bool:
        """Dynamic property to check if visibility is currently active"""
        return self.expires_at and self.expires_at > timezone.now()

    def activate(self, duration_days: int = 7):
        """Activate visibility for a given duration"""
        self.expires_at = timezone.now() + timedelta(days=duration_days)
        self.save()


class SuggestedMatch(models.Model):
    """Bondmaker suggested matches for a subscribed user"""

    bondmaker = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="suggested_matches"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="suggested_for"
    )
    suggested_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="suggested_to"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("bondmaker", "user", "suggested_user")


class UserRoleSelection(models.Model):
    """Track user role selection during onboarding"""

    ROLE_CHOICES = (
        ("looking_for_love", "Looking for Love"),
        ("bondmaker", "Bondmaker"),
    )

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="role_selection"
    )
    selected_role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default="looking_for_love"
    )
    selected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.get_selected_role_display()}"

    class Meta:
        ordering = ["-selected_at"]


class MatchRequest(models.Model):
    STATUS = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("completed", "Completed"),
    )

    requester = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_requests"
    )
    bondmaker = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="received_requests"
    )

    coins_charged = models.IntegerField()
    platform_revenue = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    bondmaker_earning = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="pending",
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["bondmaker", "status"]),  # helpful
            models.Index(fields=["status"]),  # fast filtering by status
        ]


class UserMatch(models.Model):
    """Store potential matches between users based on location and preferences"""

    MATCH_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("liked", "Liked"),
        ("disliked", "Disliked"),
        ("matched", "Matched"),
        ("blocked", "Blocked"),
    )

    match_request = models.OneToOneField(
        MatchRequest,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="user_match",
    )
    user1 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="matches_initiated"
    )
    user2 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="matches_received"
    )
    distance = models.FloatField(help_text="Distance between users in kilometers")
    match_score = models.FloatField(
        default=0.0, help_text="Compatibility score (0-100)"
    )
    status = models.CharField(
        max_length=20, choices=MATCH_STATUS_CHOICES, default="pending"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user1.email} <-> {self.user2.email} ({self.distance:.2f}km)"

    class Meta:
        # unique_together = ["user1", "user2"]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user1", "status"]),
            models.Index(fields=["user2", "status"]),
            models.Index(fields=["distance"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["user1", "user2"], name="unique_user_match")
        ]


class PasswordResetOTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    reset_token = models.UUIDField(default=uuid.uuid4, editable=False, null=True, blank=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    @classmethod
    def can_resend_for_email(cls, email):
        recent_attempts = cls.objects.filter(
            email=email,
            created_at__gte=timezone.now() - timedelta(minutes=1),
        ).count()
        return recent_attempts < 3

    @staticmethod
    def generate_otp():
        return "".join(random.choices(string.digits, k=6))


class Notification(models.Model):
    """
    Notifications for bondmakers (or any user) about match requests, etc.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def mark_as_read(self):
        self.is_read = True
        self.save()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification to {self.user.email}: {self.title}"


class Report(models.Model):
    """
    Track reports made by users on other users.
    A report may optionally be linked to a specific UserMatch or interaction.
    """

    REASON_CHOICES = (
        ("spam", "Spam"),
        ("inappropriate", "Inappropriate Content"),
        ("harassment", "Harassment"),
        ("other", "Other"),
    )

    reporter = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reports_made"
    )
    reported_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reports_received"
    )
    user_match = models.ForeignKey(
        "UserMatch", null=True, blank=True, on_delete=models.SET_NULL
    )
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [
            ("reporter", "reported_user", "user_match")
        ]  # prevent duplicate reports per match

    def __str__(self):
        return (
            f"{self.reporter.email} reported {self.reported_user.email} ({self.reason})"
        )
