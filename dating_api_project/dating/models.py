import random
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class User(AbstractUser):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    age = models.PositiveIntegerField(blank=True, null=True)
    
    # Location Fields
    location = models.CharField(max_length=100, blank=True, null=True)  # Keep for backward compatibility
    latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True, 
                                  validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True,
                                   validators=[MinValueValidator(-180), MaxValueValidator(180)])
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    
    # Location Privacy Settings
    location_privacy = models.CharField(max_length=20, choices=[
        ('public', 'Public'),
        ('friends', 'Friends Only'),
        ('private', 'Private'),
        ('hidden', 'Hidden')
    ], default='public')
    location_sharing_enabled = models.BooleanField(default=True)
    location_update_frequency = models.CharField(max_length=20, choices=[
        ('realtime', 'Real-time'),
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('manual', 'Manual Only')
    ], default='manual')
    
    # Dating App Specific Fields
    is_matchmaker = models.BooleanField(default=False)
    bio = models.TextField(blank=True)
    last_location_update = models.DateTimeField(blank=True, null=True)
    
    # Profile Pictures
    profile_picture = models.URLField(blank=True, null=True, help_text="Main profile picture URL")
    profile_gallery = models.JSONField(default=list, help_text="Array of additional profile picture URLs")
    
    # Personal Information (From Figma Designs)
    # Basic Info
    education_level = models.CharField(max_length=50, blank=True, null=True, choices=[
        ('high_school', 'High School'),
        ('undergrad', 'Undergraduate'),
        ('bachelors', 'Bachelor\'s Degree'),
        ('masters', 'Master\'s Degree'),
        ('phd', 'PhD'),
        ('other', 'Other')
    ])
    height = models.CharField(max_length=10, blank=True, null=True, help_text="Height in feet/inches or cm")
    zodiac_sign = models.CharField(max_length=20, blank=True, null=True, choices=[
        ('aries', 'Aries'), ('taurus', 'Taurus'), ('gemini', 'Gemini'), ('cancer', 'Cancer'),
        ('leo', 'Leo'), ('virgo', 'Virgo'), ('libra', 'Libra'), ('scorpio', 'Scorpio'),
        ('sagittarius', 'Sagittarius'), ('capricorn', 'Capricorn'), ('aquarius', 'Aquarius'), ('pisces', 'Pisces')
    ])
    languages = models.JSONField(default=list, help_text="Languages spoken (e.g., ['English', 'French'])")
    relationship_status = models.CharField(max_length=20, blank=True, null=True, choices=[
        ('single', 'Single'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
        ('separated', 'Separated')
    ])
    
    # Lifestyle & Preferences
    smoking_preference = models.CharField(max_length=20, blank=True, null=True, choices=[
        ('never', 'Never'),
        ('occasionally', 'Occasionally'),
        ('regularly', 'Regularly'),
        ('quit', 'Quit')
    ])
    drinking_preference = models.CharField(max_length=20, blank=True, null=True, choices=[
        ('never', 'Never'),
        ('occasionally', 'Occasionally'),
        ('regularly', 'Regularly'),
        ('quit', 'Quit')
    ])
    pet_preference = models.CharField(max_length=20, blank=True, null=True, choices=[
        ('dog', 'Dog'),
        ('cat', 'Cat'),
        ('both', 'Both'),
        ('none', 'None'),
        ('other', 'Other')
    ])
    exercise_frequency = models.CharField(max_length=20, blank=True, null=True, choices=[
        ('never', 'Never'),
        ('1x_week', '1x/week'),
        ('2x_week', '2x/week'),
        ('3x_week', '3x/week'),
        ('4x_week', '4x/week'),
        ('5x_week', '5x/week'),
        ('daily', 'Daily')
    ])
    kids_preference = models.CharField(max_length=20, blank=True, null=True, choices=[
        ('want', 'Want Kids'),
        ('dont_want', 'Don\'t Want Kids'),
        ('have_kids', 'Have Kids'),
        ('open', 'Open to Kids')
    ])
    
    # Personality & Communication
    personality_type = models.CharField(max_length=10, blank=True, null=True, choices=[
        ('INTJ', 'INTJ'), ('INTP', 'INTP'), ('ENTJ', 'ENTJ'), ('ENTP', 'ENTP'),
        ('INFJ', 'INFJ'), ('INFP', 'INFP'), ('ENFJ', 'ENFJ'), ('ENFP', 'ENFP'),
        ('ISTJ', 'ISTJ'), ('ISFJ', 'ISFJ'), ('ESTJ', 'ESTJ'), ('ESFJ', 'ESFJ'),
        ('ISTP', 'ISTP'), ('ISFP', 'ISFP'), ('ESTP', 'ESTP'), ('ESFP', 'ESFP')
    ])
    love_language = models.CharField(max_length=20, blank=True, null=True, choices=[
        ('physical_touch', 'Physical Touch'),
        ('gifts', 'Gifts'),
        ('quality_time', 'Quality Time'),
        ('words_of_affirmation', 'Words of Affirmation'),
        ('acts_of_service', 'Acts of Service')
    ])
    communication_style = models.CharField(max_length=20, blank=True, null=True, choices=[
        ('direct', 'Direct'),
        ('romantic', 'Romantic'),
        ('playful', 'Playful'),
        ('reserved', 'Reserved')
    ])
    
    # Interests & Hobbies
    hobbies = models.JSONField(default=list, help_text="List of hobbies and interests")
    interests = models.JSONField(default=list, help_text="List of general interests")
    
    # Future Plans & Values
    marriage_plans = models.CharField(max_length=20, blank=True, null=True, choices=[
        ('yes', 'Yes'),
        ('no', 'No'),
        ('maybe', 'Maybe')
    ])
    kids_plans = models.CharField(max_length=20, blank=True, null=True, choices=[
        ('yes', 'Yes'),
        ('no', 'No'),
        ('maybe', 'Maybe')
    ])
    religion_importance = models.CharField(max_length=20, blank=True, null=True, choices=[
        ('very', 'Very Important'),
        ('somewhat', 'Somewhat Important'),
        ('not_important', 'Not Important')
    ])
    religion = models.CharField(max_length=50, blank=True, null=True)
    
    # Dating Preferences
    dating_type = models.CharField(max_length=20, blank=True, null=True, choices=[
        ('casual', 'Casual Dating'),
        ('serious', 'Serious Relationship'),
        ('marriage', 'Marriage'),
        ('sugar', 'Sugar Relationship'),
        ('friends', 'Friends First')
    ])
    open_to_long_distance = models.CharField(max_length=20, blank=True, null=True, choices=[
        ('yes', 'Yes'),
        ('no', 'No'),
        ('maybe', 'Maybe')
    ])
    
    # Matching Preferences
    max_distance = models.PositiveIntegerField(default=50, help_text="Maximum distance in kilometers")
    age_range_min = models.PositiveIntegerField(default=18)
    age_range_max = models.PositiveIntegerField(default=100)
    preferred_gender = models.CharField(max_length=10, blank=True, null=True)
    
    # What I'm Looking For (From Figma Design)
    looking_for = models.TextField(blank=True, null=True, help_text="Free text describing what the user is looking for")
    
    # Notification Settings (From Figma Design)
    push_notifications_enabled = models.BooleanField(default=True, help_text="Enable push notifications")
    email_notifications_enabled = models.BooleanField(default=True, help_text="Enable email notifications")
    
    # Language Settings (From Figma Design)
    preferred_language = models.CharField(max_length=10, default='en', help_text="User's preferred app language")

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  # 'username' is still required by AbstractUser

    def __str__(self):
        return self.email
    
    @property
    def has_location(self):
        """Check if user has valid GPS coordinates"""
        return self.latitude is not None and self.longitude is not None
    
    def get_profile_completion_percentage(self):
        """Calculate profile completion percentage based on filled fields"""
        required_fields = [
            'name', 'email', 'gender', 'age', 'bio', 'profile_picture',
            'education_level', 'height', 'zodiac_sign', 'languages',
            'smoking_preference', 'drinking_preference', 'exercise_frequency',
            'personality_type', 'love_language', 'communication_style',
            'hobbies', 'interests', 'looking_for'
        ]
        
        filled_fields = 0
        total_fields = len(required_fields)
        
        for field_name in required_fields:
            field_value = getattr(self, field_name, None)
            if field_value is not None and field_value != '' and field_value != [] and field_value != {}:
                filled_fields += 1
        
        # Add bonus for profile gallery
        if self.profile_gallery and len(self.profile_gallery) > 0:
            filled_fields += 1
            total_fields += 1
        
        return min(100, int((filled_fields / total_fields) * 100))
    
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
        
        from .location_utils import calculate_distance
        return calculate_distance(
            self.location_coordinates,
            other_user.location_coordinates
        )



class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    date_subscribed = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class PuzzleVerification(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    question = models.CharField(max_length=255)
    answer = models.CharField(max_length=50)  # correct answer (hidden from user)
    user_answer = models.CharField(max_length=50, blank=True)
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Puzzle for {self.user.username} – {'Correct' if self.is_correct else 'Pending'}"

    @staticmethod
    def generate_puzzle():
        num1 = random.randint(1, 20)
        num2 = random.randint(1, 20)
        question = f"What is {num1} + {num2}?"
        answer = str(num1 + num2)
        return question, answer


class CoinTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('earn', 'Earn'),
        ('spend', 'Spend'),
    )

    user = models.ForeignKey('User', on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} {self.amount} coins"


class Waitlist(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email}"

    class Meta:
        ordering = ['-date_joined']


class EmailLog(models.Model):
    EMAIL_TYPES = (
        ('newsletter_welcome', 'Newsletter Welcome'),
        ('waitlist_confirmation', 'Waitlist Confirmation'),
        ('generic', 'Generic Email'),
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
        ordering = ['-sent_at']


class Job(models.Model):
    JOB_TYPES = (
        ('full-time', 'Full-time'),
        ('part-time', 'Part-time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
        ('freelance', 'Freelance'),
    )

    CATEGORIES = (
        ('engineering', 'Engineering'),
        ('design', 'Design'),
        ('marketing', 'Marketing'),
        ('sales', 'Sales'),
        ('product', 'Product'),
        ('operations', 'Operations'),
        ('hr', 'Human Resources'),
        ('finance', 'Finance'),
        ('other', 'Other'),
    )

    STATUS_CHOICES = (
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('draft', 'Draft'),
        ('archived', 'Archived'),
    )

    title = models.CharField(max_length=200)
    job_type = models.CharField(max_length=20, choices=JOB_TYPES)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
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
        ordering = ['-created_at']


class JobApplication(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('shortlisted', 'Shortlisted'),
        ('interviewed', 'Interviewed'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    resume_url = models.URLField(blank=True, null=True)  # Link to uploaded resume
    cover_letter = models.TextField(blank=True, null=True)
    experience_years = models.PositiveIntegerField(blank=True, null=True)
    current_company = models.CharField(max_length=100, blank=True, null=True)
    expected_salary = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.job.title}"

    class Meta:
        ordering = ['-applied_at']
        unique_together = ['job', 'email']  # Prevent duplicate applications


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
        from django.utils import timezone
        return timezone.now() > self.expires_at

    class Meta:
        ordering = ['-created_at']


class TranslationLog(models.Model):
    source_text = models.TextField()
    translated_text = models.TextField()
    source_language = models.CharField(max_length=10)  # e.g., 'en', 'es', 'fr'
    target_language = models.CharField(max_length=10)
    character_count = models.PositiveIntegerField()
    translation_time = models.FloatField(help_text="Translation time in seconds")
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.source_language} → {self.target_language} ({self.character_count} chars)"

    class Meta:
        ordering = ['-created_at']


class SocialAccount(models.Model):
    """Store social account information for OAuth users"""
    PROVIDER_CHOICES = (
        ('google', 'Google'),
        ('apple', 'Apple'),
        ('facebook', 'Facebook'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_accounts')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_user_id = models.CharField(max_length=255)  # ID from the provider
    provider_data = models.JSONField(default=dict)  # Store additional provider data
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.provider}"
    
    class Meta:
        unique_together = ['provider', 'provider_user_id']
        ordering = ['-created_at']


class DeviceRegistration(models.Model):
    """Store device information for push notifications"""
    DEVICE_TYPE_CHOICES = (
        ('ios', 'iOS'),
        ('android', 'Android'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices')
    device_id = models.CharField(max_length=255, unique=True)
    device_type = models.CharField(max_length=10, choices=DEVICE_TYPE_CHOICES)
    push_token = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.device_type} ({self.device_id[:8]}...)"
    
    class Meta:
        ordering = ['-created_at']


class LocationHistory(models.Model):
    """Store user location history for tracking and privacy"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='location_history')
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    accuracy = models.FloatField(blank=True, null=True, help_text="GPS accuracy in meters")
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=20, choices=[
        ('gps', 'GPS'),
        ('network', 'Network'),
        ('manual', 'Manual'),
        ('ip', 'IP Address')
    ], default='gps')
    
    def __str__(self):
        return f"{self.user.email} - {self.timestamp} ({self.latitude}, {self.longitude})"
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['timestamp']),
        ]


class UserMatch(models.Model):
    """Store potential matches between users based on location and preferences"""
    MATCH_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('liked', 'Liked'),
        ('disliked', 'Disliked'),
        ('matched', 'Matched'),
        ('blocked', 'Blocked'),
    )
    
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='matches_initiated')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='matches_received')
    distance = models.FloatField(help_text="Distance between users in kilometers")
    match_score = models.FloatField(default=0.0, help_text="Compatibility score (0-100)")
    status = models.CharField(max_length=20, choices=MATCH_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user1.email} <-> {self.user2.email} ({self.distance:.2f}km)"
    
    class Meta:
        unique_together = ['user1', 'user2']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user1', 'status']),
            models.Index(fields=['user2', 'status']),
            models.Index(fields=['distance']),
        ]


class UserInterest(models.Model):
    """Store user interests and hobbies for better matching"""
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=50, choices=[
        ('sports', 'Sports'),
        ('music', 'Music'),
        ('travel', 'Travel'),
        ('food', 'Food'),
        ('art', 'Art'),
        ('technology', 'Technology'),
        ('fitness', 'Fitness'),
        ('reading', 'Reading'),
        ('movies', 'Movies'),
        ('gaming', 'Gaming'),
        ('outdoor', 'Outdoor Activities'),
        ('other', 'Other')
    ])
    icon = models.CharField(max_length=50, blank=True, null=True, help_text="Icon name for UI")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


class UserProfileView(models.Model):
    """Track profile views for analytics and recommendations"""
    viewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profile_views_made')
    viewed_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profile_views_received')
    viewed_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=20, choices=[
        ('search', 'Search Results'),
        ('discover', 'Discover Feed'),
        ('nearby', 'Nearby Users'),
        ('recommended', 'Recommended'),
        ('direct', 'Direct Link')
    ], default='search')
    
    def __str__(self):
        return f"{self.viewer.email} viewed {self.viewed_user.email}"
    
    class Meta:
        unique_together = ['viewer', 'viewed_user']
        ordering = ['-viewed_at']


class UserInteraction(models.Model):
    """Track user interactions (likes, dislikes, super likes, etc.)"""
    INTERACTION_TYPES = [
        ('like', 'Like'),
        ('dislike', 'Dislike'),
        ('super_like', 'Super Like'),
        ('pass', 'Pass'),
        ('block', 'Block'),
        ('report', 'Report'),
        ('request_live', 'Request Live'),
        ('share_profile', 'Share Profile')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interactions_made')
    target_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interactions_received')
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, help_text="Additional interaction data")
    
    def __str__(self):
        return f"{self.user.email} {self.interaction_type} {self.target_user.email}"
    
    class Meta:
        unique_together = ['user', 'target_user', 'interaction_type']
        ordering = ['-created_at']


class SearchQuery(models.Model):
    """Store search queries for analytics and suggestions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='search_queries')
    query = models.CharField(max_length=255)
    filters = models.JSONField(default=dict, help_text="Applied filters")
    results_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.email}: {self.query}"
    
    class Meta:
        ordering = ['-created_at']


class RecommendationEngine(models.Model):
    """Store recommendation algorithm data"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    recommended_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommended_to')
    score = models.FloatField(help_text="Recommendation score (0-100)")
    algorithm = models.CharField(max_length=50, choices=[
        ('location_based', 'Location Based'),
        ('interest_based', 'Interest Based'),
        ('compatibility', 'Compatibility'),
        ('hybrid', 'Hybrid')
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.email} -> {self.recommended_user.email} ({self.score})"
    
    class Meta:
        unique_together = ['user', 'recommended_user']
        ordering = ['-score']


class LocationPermission(models.Model):
    """Store user location permission settings"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='location_permissions')
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
        ordering = ['-updated_at']


# =============================================================================
# CHAT AND MESSAGING MODELS (NEW)
# =============================================================================

class Chat(models.Model):
    """Represents a conversation between two or more users"""
    CHAT_TYPES = [
        ('direct', 'Direct Message'),
        ('matchmaker_intro', 'Matchmaker Introduction'),
        ('group', 'Group Chat'),
    ]
    
    chat_type = models.CharField(max_length=20, choices=CHAT_TYPES, default='direct')
    participants = models.ManyToManyField(User, related_name='chats')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_chats')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    # Chat settings
    chat_name = models.CharField(max_length=100, blank=True, null=True, help_text="Custom name for group chats")
    chat_theme = models.CharField(max_length=20, default='default', choices=[
        ('default', 'Default'), ('dark', 'Dark'), ('light', 'Light'), ('colorful', 'Colorful')
    ])
    
    def __str__(self):
        if self.chat_name:
            return f"{self.chat_name} ({self.chat_type})"
        participants = list(self.participants.all()[:2])
        if len(participants) == 2:
            return f"{participants[0].name} & {participants[1].name}"
        return f"Chat {self.id} ({self.chat_type})"
    
    def get_other_participant(self, user):
        """Get the other participant in a direct message chat"""
        if self.chat_type == 'direct':
            return self.participants.exclude(id=user.id).first()
        return None
    
    def get_unread_count(self, user):
        """Get unread message count for a specific user"""
        return self.messages.filter(is_read=False).exclude(sender=user).count()
    
    class Meta:
        ordering = ['-last_message_at']
        indexes = [
            models.Index(fields=['chat_type', 'is_active']),
            models.Index(fields=['last_message_at']),
        ]


class Message(models.Model):
    """Represents an individual message within a chat"""
    MESSAGE_TYPES = [
        ('text', 'Text Message'),
        ('voice_note', 'Voice Note'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('document', 'Document'),
        ('system', 'System Message'),
        ('matchmaker_intro', 'Matchmaker Introduction'),
        ('call_start', 'Call Started'),
        ('call_end', 'Call Ended'),
    ]
    
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_messages',
                               help_text="Null for system messages")
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='text')
    content = models.TextField(blank=True, null=True, help_text="Text content of the message")
    
    # Media attachments
    voice_note_url = models.URLField(blank=True, null=True, help_text="URL to the voice note audio file")
    voice_note_duration = models.PositiveIntegerField(blank=True, null=True, help_text="Duration in seconds")
    image_url = models.URLField(blank=True, null=True, help_text="URL to image file")
    video_url = models.URLField(blank=True, null=True, help_text="URL to video file")
    document_url = models.URLField(blank=True, null=True, help_text="URL to document file")
    document_name = models.CharField(max_length=255, blank=True, null=True, help_text="Original document name")
    
    # Message metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(blank=True, null=True)
    
    # Reply/quote functionality
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    
    # Message reactions
    reactions = models.JSONField(default=dict, help_text="User reactions: {'user_id': 'emoji'}")
    
    def __str__(self):
        sender_name = self.sender.name if self.sender else 'System'
        return f"{sender_name}: {self.content[:50]}..." if self.content else f"{sender_name}: {self.message_type}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update the last_message_at for the associated chat
        self.chat.last_message_at = self.timestamp
        self.chat.save(update_fields=['last_message_at'])
    
    def mark_as_read(self, user):
        """Mark message as read by a specific user"""
        if self.sender != user and not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['chat', 'timestamp']),
            models.Index(fields=['sender', 'timestamp']),
            models.Index(fields=['message_type']),
        ]


class VoiceNote(models.Model):
    """Store voice note metadata and processing status"""
    message = models.OneToOneField(Message, on_delete=models.CASCADE, related_name='voice_note')
    audio_url = models.URLField(help_text="URL to the audio file")
    duration = models.PositiveIntegerField(help_text="Duration in seconds")
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    transcription = models.TextField(blank=True, null=True, help_text="Speech-to-text transcription")
    transcription_confidence = models.FloatField(blank=True, null=True, help_text="Transcription confidence score")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Voice note: {self.duration}s - {self.message.chat}"
    
    class Meta:
        ordering = ['-created_at']


class Call(models.Model):
    """Store voice/video call sessions"""
    CALL_TYPES = [
        ('voice', 'Voice Call'),
        ('video', 'Video Call'),
    ]
    
    CALL_STATUS = [
        ('initiated', 'Initiated'),
        ('ringing', 'Ringing'),
        ('active', 'Active'),
        ('ended', 'Ended'),
        ('missed', 'Missed'),
        ('declined', 'Declined'),
        ('busy', 'Busy'),
    ]
    
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='calls')
    caller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='initiated_calls')
    callee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_calls')
    call_type = models.CharField(max_length=10, choices=CALL_TYPES, default='voice')
    status = models.CharField(max_length=20, choices=CALL_STATUS, default='initiated')
    
    # Call timing
    started_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(blank=True, null=True)
    ended_at = models.DateTimeField(blank=True, null=True)
    duration = models.PositiveIntegerField(blank=True, null=True, help_text="Call duration in seconds")
    
    # Call metadata
    call_id = models.CharField(max_length=100, unique=True, help_text="Unique call identifier for WebRTC")
    room_id = models.CharField(max_length=100, blank=True, null=True, help_text="WebRTC room ID")
    quality_score = models.FloatField(blank=True, null=True, help_text="Call quality score (0-100)")
    
    # Call settings
    is_recorded = models.BooleanField(default=False)
    recording_url = models.URLField(blank=True, null=True, help_text="URL to call recording")
    
    def __str__(self):
        return f"{self.caller.name} → {self.callee.name} ({self.call_type}) - {self.status}"
    
    def get_duration_display(self):
        """Get formatted duration string"""
        if self.duration:
            minutes = self.duration // 60
            seconds = self.duration % 60
            return f"{minutes:02d}:{seconds:02d}"
        return "00:00"
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['caller', 'status']),
            models.Index(fields=['callee', 'status']),
            models.Index(fields=['call_id']),
        ]


class ChatParticipant(models.Model):
    """Track chat participant status and settings"""
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='chat_participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_participations')
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    # Participant settings
    notifications_enabled = models.BooleanField(default=True)
    mute_until = models.DateTimeField(blank=True, null=True, help_text="Mute chat until this time")
    custom_nickname = models.CharField(max_length=50, blank=True, null=True)
    
    # Last seen
    last_seen_at = models.DateTimeField(blank=True, null=True)
    last_read_message = models.ForeignKey(Message, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.name} in {self.chat}"
    
    def is_muted(self):
        """Check if participant has muted the chat"""
        if self.mute_until:
            return timezone.now() < self.mute_until
        return False
    
    class Meta:
        unique_together = ['chat', 'user']
        ordering = ['-joined_at']


class ChatReport(models.Model):
    """Store chat-related reports and moderation actions"""
    REPORT_TYPES = [
        ('spam', 'Spam'),
        ('harassment', 'Harassment'),
        ('inappropriate_content', 'Inappropriate Content'),
        ('fake_profile', 'Fake Profile'),
        ('other', 'Other'),
    ]
    
    REPORT_STATUS = [
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_reports_made')
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_reports_received')
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='reports')
    message = models.ForeignKey(Message, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports')
    
    report_type = models.CharField(max_length=30, choices=REPORT_TYPES)
    description = models.TextField(help_text="Detailed description of the issue")
    status = models.CharField(max_length=20, choices=REPORT_STATUS, default='pending')
    
    # Moderation actions
    moderator_notes = models.TextField(blank=True, null=True)
    action_taken = models.CharField(max_length=100, blank=True, null=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_reports')
    resolved_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Report: {self.reporter.name} → {self.reported_user.name} ({self.report_type})"
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'report_type']),
            models.Index(fields=['reported_user', 'status']),
        ]


class LivenessVerification(models.Model):
    """Store liveness check verification data for user identity verification"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    )
    
    ACTION_CHOICES = (
        ('turn_left', 'Turn Head Left'),
        ('turn_right', 'Turn Head Right'),
        ('open_mouth', 'Open Mouth'),
        ('smile', 'Smile'),
        ('blink', 'Blink'),
        ('nod', 'Nod Head'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='liveness_checks')
    session_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Verification data
    actions_required = models.JSONField(default=list, help_text="List of actions user must perform")
    actions_completed = models.JSONField(default=list, help_text="List of actions user completed")
    confidence_score = models.FloatField(default=0.0, help_text="Confidence score (0-100)")
    face_quality_score = models.FloatField(default=0.0, help_text="Face quality score (0-100)")
    
    # Detection results
    is_live_person = models.BooleanField(default=False)
    spoof_detected = models.BooleanField(default=False)
    spoof_type = models.CharField(max_length=50, blank=True, null=True, help_text="Type of spoof detected")
    
    # Media storage
    video_url = models.URLField(blank=True, null=True, help_text="URL to verification video")
    images_data = models.JSONField(default=dict, help_text="URLs or data for verification images")
    
    # Metadata
    verification_method = models.CharField(max_length=50, default='video', help_text="video, images, or session")
    provider = models.CharField(max_length=50, default='internal', help_text="AWS, FacePlusPlus, Azure, internal")
    provider_response = models.JSONField(default=dict, help_text="Full response from verification provider")
    
    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    
    # Retry tracking
    attempts_count = models.PositiveIntegerField(default=1)
    max_attempts = models.PositiveIntegerField(default=3)
    
    def __str__(self):
        return f"{self.user.email} - Liveness Check ({self.status})"
    
    def is_expired(self):
        """Check if verification session has expired"""
        from django.utils import timezone
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def can_retry(self):
        """Check if user can retry verification"""
        return self.attempts_count < self.max_attempts
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['session_id']),
            models.Index(fields=['started_at']),
        ]


class UserVerificationStatus(models.Model):
    """Track overall user verification status"""
    VERIFICATION_LEVEL_CHOICES = (
        ('none', 'Not Verified'),
        ('email', 'Email Verified'),
        ('phone', 'Phone Verified'),
        ('liveness', 'Liveness Verified'),
        ('full', 'Fully Verified'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='verification_status')
    
    # Verification flags
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    liveness_verified = models.BooleanField(default=False)
    identity_verified = models.BooleanField(default=False)
    
    # Verification level
    verification_level = models.CharField(max_length=20, choices=VERIFICATION_LEVEL_CHOICES, default='none')
    
    # Last verification dates
    email_verified_at = models.DateTimeField(blank=True, null=True)
    phone_verified_at = models.DateTimeField(blank=True, null=True)
    liveness_verified_at = models.DateTimeField(blank=True, null=True)
    
    # Verification badges
    verified_badge = models.BooleanField(default=False, help_text="Show verified badge on profile")
    trusted_member = models.BooleanField(default=False, help_text="Trusted member status")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.verification_level}"
    
    def update_verification_level(self):
        """Update verification level based on completed verifications"""
        if self.liveness_verified and self.email_verified and self.phone_verified:
            self.verification_level = 'full'
            self.verified_badge = True
            self.identity_verified = True
        elif self.liveness_verified:
            self.verification_level = 'liveness'
            self.verified_badge = True
        elif self.phone_verified:
            self.verification_level = 'phone'
        elif self.email_verified:
            self.verification_level = 'email'
        else:
            self.verification_level = 'none'
            self.verified_badge = False
        
        self.save()
    
    class Meta:
        verbose_name = "User Verification Status"
        verbose_name_plural = "User Verification Statuses"
        ordering = ['-updated_at']


# Email and Phone Verification Models
class EmailVerification(models.Model):
    """Email OTP verification for user registration"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_verifications')
    email = models.EmailField()
    otp_code = models.CharField(max_length=4)
    is_verified = models.BooleanField(default=False)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"Email OTP for {self.email} - {self.otp_code}"
    
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def can_resend(self):
        """Check if user can request a new OTP (rate limiting)"""
        from django.utils import timezone
        from datetime import timedelta
        recent_attempts = EmailVerification.objects.filter(
            email=self.email,
            created_at__gte=timezone.now() - timedelta(minutes=1)
        ).count()
        return recent_attempts < 3
    
    @classmethod
    def generate_otp(cls):
        """Generate 4-digit OTP"""
        import random
        import string
        return ''.join(random.choices(string.digits, k=4))
    
    @classmethod
    def create_verification(cls, user, email):
        """Create new email verification"""
        from django.utils import timezone
        from datetime import timedelta
        # Deactivate previous verifications for this email
        cls.objects.filter(email=email, is_used=False).update(is_used=True)
        
        otp_code = cls.generate_otp()
        expires_at = timezone.now() + timedelta(minutes=10)
        
        return cls.objects.create(
            user=user,
            email=email,
            otp_code=otp_code,
            expires_at=expires_at
        )
    
    @classmethod
    def can_resend_for_email(cls, email):
        """Check if email can request new OTP"""
        from django.utils import timezone
        from datetime import timedelta
        recent_attempts = cls.objects.filter(
            email=email,
            created_at__gte=timezone.now() - timedelta(minutes=1)
        ).count()
        return recent_attempts < 3
    
    class Meta:
        ordering = ['-created_at']


class PhoneVerification(models.Model):
    """Phone number OTP verification for user registration"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='phone_verifications')
    phone_number = models.CharField(max_length=20)
    country_code = models.CharField(max_length=5, default='+1')
    otp_code = models.CharField(max_length=4)
    is_verified = models.BooleanField(default=False)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"Phone OTP for {self.country_code}{self.phone_number} - {self.otp_code}"
    
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def can_resend(self):
        """Check if user can request a new OTP (rate limiting)"""
        from django.utils import timezone
        from datetime import timedelta
        recent_attempts = PhoneVerification.objects.filter(
            phone_number=self.phone_number,
            country_code=self.country_code,
            created_at__gte=timezone.now() - timedelta(minutes=1)
        ).count()
        return recent_attempts < 3
    
    @classmethod
    def generate_otp(cls):
        """Generate 4-digit OTP"""
        import random
        import string
        return ''.join(random.choices(string.digits, k=4))
    
    @classmethod
    def create_verification(cls, user, phone_number, country_code='+1'):
        """Create new phone verification"""
        from django.utils import timezone
        from datetime import timedelta
        # Deactivate previous verifications for this phone number
        cls.objects.filter(
            phone_number=phone_number, 
            country_code=country_code, 
            is_used=False
        ).update(is_used=True)
        
        otp_code = cls.generate_otp()
        expires_at = timezone.now() + timedelta(minutes=10)
        
        return cls.objects.create(
            user=user,
            phone_number=phone_number,
            country_code=country_code,
            otp_code=otp_code,
            expires_at=expires_at
        )
    
    @classmethod
    def can_resend_for_phone(cls, phone_number, country_code):
        """Check if phone can request new OTP"""
        from django.utils import timezone
        from datetime import timedelta
        recent_attempts = cls.objects.filter(
            phone_number=phone_number,
            country_code=country_code,
            created_at__gte=timezone.now() - timedelta(minutes=1)
        ).count()
        return recent_attempts < 3
    
    class Meta:
        ordering = ['-created_at'        ]


# =============================================================================
# LIVE SESSION MODELS (NEW)
# =============================================================================

class LiveSession(models.Model):
    """Represents an active live session by a user."""
    SESSION_STATUS_CHOICES = [
        ('active', 'Active'),
        ('ended', 'Ended'),
        ('scheduled', 'Scheduled'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='live_sessions')
    title = models.CharField(max_length=255, blank=True, null=True, help_text="Title of the live session")
    description = models.TextField(blank=True, null=True, help_text="Description of the live session")
    start_time = models.DateTimeField(auto_now_add=True, help_text="When the live session started")
    end_time = models.DateTimeField(blank=True, null=True, help_text="When the live session ended")
    status = models.CharField(max_length=20, choices=SESSION_STATUS_CHOICES, default='active')
    
    # Duration limits (e.g., 1 hour for free users, more for premium)
    duration_limit_minutes = models.PositiveIntegerField(default=60, help_text="Maximum duration in minutes")
    
    # Metrics
    viewers_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0) # For live session likes/reactions
    
    # Stream details (placeholder for actual streaming service integration)
    stream_url = models.URLField(blank=True, null=True, help_text="URL for the live stream")
    thumbnail_url = models.URLField(blank=True, null=True, help_text="Thumbnail URL for the live session")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.name}'s Live Session ({self.status})"

    def is_active(self):
        """Check if the session is currently active."""
        return self.status == 'active' and (self.end_time is None or self.end_time > timezone.now())

    def get_current_duration(self):
        """Calculate current duration of the session."""
        if self.start_time:
            if self.end_time:
                return self.end_time - self.start_time
            return timezone.now() - self.start_time
        return timezone.timedelta(seconds=0)

    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'start_time']),
        ]


class LiveParticipant(models.Model):
    """Tracks users participating in or viewing a live session."""
    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='live_participations')
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(blank=True, null=True)
    
    # Role in session (e.g., viewer, co-host, speaker)
    ROLE_CHOICES = [
        ('viewer', 'Viewer'),
        ('co_host', 'Co-Host'),
        ('speaker', 'Speaker'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')

    def __str__(self):
        return f"{self.user.name} in {self.session.user.name}'s session"

    class Meta:
        unique_together = ['session', 'user'] # A user can only participate once per session
        ordering = ['joined_at']
        indexes = [
            models.Index(fields=['session', 'user']),
            models.Index(fields=['user', 'joined_at']),
        ]


class UserRoleSelection(models.Model):
    """Track user role selection during onboarding"""
    ROLE_CHOICES = (
        ('looking_for_love', 'Looking for Love'),
        ('bondmaker', 'Become a Bondmaker'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='role_selection')
    selected_role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    selected_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.get_selected_role_display()}"
    
    class Meta:
        ordering = ['-selected_at']


# =============================================================================
# SOCIAL FEED AND STORY MODELS (NEW)
# =============================================================================

class Post(models.Model):
    """Represents user posts in the Bond Story feed"""
    POST_TYPES = [
        ('story', 'Story'),
        ('post', 'Regular Post'),
        ('announcement', 'Announcement'),
    ]
    
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends Only'),
        ('private', 'Private'),
    ]
    
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    post_type = models.CharField(max_length=20, choices=POST_TYPES, default='post')
    content = models.TextField(help_text="Post content/text")
    
    # Media attachments
    image_urls = models.JSONField(default=list, help_text="List of image URLs")
    video_url = models.URLField(blank=True, null=True, help_text="URL to video file")
    video_thumbnail = models.URLField(blank=True, null=True, help_text="Video thumbnail URL")
    
    # Post metadata
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    location = models.CharField(max_length=255, blank=True, null=True, help_text="Post location")
    hashtags = models.JSONField(default=list, help_text="List of hashtags in the post")
    mentions = models.JSONField(default=list, help_text="List of mentioned user IDs")
    
    # Engagement metrics
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)
    bonds_count = models.PositiveIntegerField(default=0, help_text="Handshake/bond reactions")
    
    # Status and moderation
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_reported = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.author.name}: {self.content[:50]}..."
    
    def get_engagement_score(self):
        """Calculate total engagement score"""
        return self.likes_count + self.comments_count + self.shares_count + self.bonds_count
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['author', 'created_at']),
            models.Index(fields=['post_type', 'is_active']),
            models.Index(fields=['visibility', 'created_at']),
            models.Index(fields=['is_featured', 'created_at']),
        ]


class PostComment(models.Model):
    """Represents comments on posts"""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_comments')
    content = models.TextField(help_text="Comment content")
    
    # Reply functionality
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    
    # Engagement metrics
    likes_count = models.PositiveIntegerField(default=0)
    replies_count = models.PositiveIntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_edited = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.author.name}: {self.content[:30]}..."
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', 'created_at']),
            models.Index(fields=['author', 'created_at']),
            models.Index(fields=['parent_comment', 'created_at']),
        ]


class PostInteraction(models.Model):
    """Track user interactions with posts (likes, shares, bonds)"""
    INTERACTION_TYPES = [
        ('like', 'Like'),
        ('share', 'Share'),
        ('bond', 'Bond/Handshake'),
        ('save', 'Save'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_interactions')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='interactions')
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.name} {self.interaction_type} {self.post.id}"
    
    class Meta:
        unique_together = ['user', 'post', 'interaction_type']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['post', 'interaction_type']),
            models.Index(fields=['user', 'interaction_type']),
        ]


class CommentInteraction(models.Model):
    """Track user interactions with comments (likes)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comment_interactions')
    comment = models.ForeignKey(PostComment, on_delete=models.CASCADE, related_name='interactions')
    interaction_type = models.CharField(max_length=20, default='like', choices=[('like', 'Like')])
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.name} likes comment {self.comment.id}"
    
    class Meta:
        unique_together = ['user', 'comment']
        ordering = ['-created_at']


class PostReport(models.Model):
    """Store reports for posts and comments"""
    REPORT_TYPES = [
        ('spam', 'Spam or Misleading'),
        ('inappropriate', 'Inappropriate or Offensive'),
        ('harassment', 'Harassment or Bullying'),
        ('misinformation', 'Misinformation'),
        ('fake', 'Fake Profile'),
        ('other', 'Other'),
    ]
    
    REPORT_STATUS = [
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_reports_made')
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_reports_received')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    comment = models.ForeignKey(PostComment, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    
    report_type = models.CharField(max_length=30, choices=REPORT_TYPES)
    description = models.TextField(help_text="Detailed description of the issue")
    status = models.CharField(max_length=20, choices=REPORT_STATUS, default='pending')
    
    # Moderation actions
    moderator_notes = models.TextField(blank=True, null=True)
    action_taken = models.CharField(max_length=100, blank=True, null=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_post_reports')
    resolved_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        target = self.post if self.post else self.comment
        return f"Report: {self.reporter.name} → {target} ({self.report_type})"
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'report_type']),
            models.Index(fields=['reported_user', 'status']),
            models.Index(fields=['post', 'status']),
            models.Index(fields=['comment', 'status']),
        ]


class Story(models.Model):
    """Represents user stories (24-hour content)"""
    STORY_TYPES = [
        ('image', 'Image Story'),
        ('video', 'Video Story'),
        ('text', 'Text Story'),
    ]
    
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stories')
    story_type = models.CharField(max_length=20, choices=STORY_TYPES, default='image')
    
    # Content
    content = models.TextField(blank=True, null=True, help_text="Text content for text stories")
    image_url = models.URLField(blank=True, null=True, help_text="URL to image file")
    video_url = models.URLField(blank=True, null=True, help_text="URL to video file")
    video_duration = models.PositiveIntegerField(blank=True, null=True, help_text="Video duration in seconds")
    
    # Story metadata
    background_color = models.CharField(max_length=7, blank=True, null=True, help_text="Hex color for text stories")
    text_color = models.CharField(max_length=7, blank=True, null=True, help_text="Text color for text stories")
    font_size = models.PositiveIntegerField(default=16, help_text="Font size for text stories")
    
    # Engagement
    views_count = models.PositiveIntegerField(default=0)
    reactions_count = models.PositiveIntegerField(default=0)
    
    # Status and timing
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(help_text="When the story expires (24 hours from creation)")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.author.name}'s {self.story_type} story"
    
    def is_expired(self):
        """Check if story has expired"""
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['author', 'created_at']),
            models.Index(fields=['expires_at', 'is_active']),
            models.Index(fields=['story_type', 'is_active']),
        ]


class StoryView(models.Model):
    """Track story views"""
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='views')
    viewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='story_views')
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.viewer.name} viewed {self.story.author.name}'s story"
    
    class Meta:
        unique_together = ['story', 'viewer']
        ordering = ['-viewed_at']


class StoryReaction(models.Model):
    """Track story reactions"""
    REACTION_TYPES = [
        ('like', 'Like'),
        ('love', 'Love'),
        ('laugh', 'Laugh'),
        ('wow', 'Wow'),
        ('sad', 'Sad'),
        ('angry', 'Angry'),
    ]
    
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='story_reactions')
    reaction_type = models.CharField(max_length=20, choices=REACTION_TYPES, default='like')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.name} {self.reaction_type} {self.story.author.name}'s story"
    
    class Meta:
        unique_together = ['story', 'user']
        ordering = ['-created_at']


class PostShare(models.Model):
    """Track post shares to external platforms"""
    SHARE_PLATFORMS = [
        ('whatsapp', 'WhatsApp'),
        ('facebook', 'Facebook'),
        ('twitter', 'Twitter/X'),
        ('instagram', 'Instagram'),
        ('threads', 'Threads'),
        ('copy_link', 'Copy Link'),
    ]
    
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='shares')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_shares')
    platform = models.CharField(max_length=20, choices=SHARE_PLATFORMS)
    shared_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.name} shared {self.post.id} on {self.platform}"
    
    class Meta:
        ordering = ['-shared_at']
        indexes = [
            models.Index(fields=['post', 'platform']),
            models.Index(fields=['user', 'shared_at']),
        ]


class FeedSearch(models.Model):
    """Store search queries for the Bond Story feed"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feed_searches', null=True, blank=True)
    query = models.CharField(max_length=255, help_text="Search query")
    results_count = models.PositiveIntegerField(default=0, help_text="Number of results found")
    filters_applied = models.JSONField(default=dict, help_text="Applied search filters")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Search: {self.query} ({self.results_count} results)"
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['query', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]


# =============================================================================
# SOCIAL MEDIA HANDLES (NEW FROM FIGMA)
# =============================================================================

class UserSocialHandle(models.Model):
    """Represents a user's social media handle for display on their profile."""
    PLATFORM_CHOICES = [
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter/X'),
        ('facebook', 'Facebook'),
        ('linkedin', 'LinkedIn'),
        ('tiktok', 'TikTok'),
        ('snapchat', 'Snapchat'),
        ('youtube', 'YouTube'),
        ('pinterest', 'Pinterest'),
        ('website', 'Personal Website'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_handles')
    platform = models.CharField(max_length=50, choices=PLATFORM_CHOICES, help_text="Social media platform")
    handle = models.CharField(max_length=100, help_text="User's handle or username on the platform")
    url = models.URLField(blank=True, null=True, help_text="Optional direct URL to the profile")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'platform'] # A user can only have one handle per platform
        ordering = ['platform']
        indexes = [
            models.Index(fields=['user', 'platform']),
        ]

    def __str__(self):
        return f"{self.user.name}'s {self.get_platform_display()} handle: {self.handle}"


# =============================================================================
# SECURITY AND DATA RESPONSIBILITY (NEW FROM FIGMA)
# =============================================================================

class UserSecurityQuestion(models.Model):
    """Store user responses to security and data responsibility questions"""
    QUESTION_TYPES = [
        ('data_protection', 'How will you protect user data?'),
        ('scam_prevention', 'What actions will you take if you suspect a scam or fake profile?'),
        ('relationship_guidance', 'Do you also provide relationship guidance?'),
        ('matchmaking_evolution', 'How do you see matchmaking evolving in the 21st century?'),
        ('unique_skills', 'What unique skills set you apart?'),
        ('business_service', 'Do you run matchmaking as a business or community service?'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='security_questions')
    question_type = models.CharField(max_length=50, choices=QUESTION_TYPES)
    response = models.TextField(help_text="User's response to the security question")
    is_public = models.BooleanField(default=False, help_text="Whether this response is shown publicly")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'question_type'] # One response per question type per user
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'question_type']),
        ]

    def __str__(self):
        return f"{self.user.name}'s response to {self.get_question_type_display()}"


# =============================================================================
# DOCUMENT VERIFICATION (NEW FROM FIGMA)
# =============================================================================

class DocumentVerification(models.Model):
    """Store document verification data for identity verification"""
    DOCUMENT_TYPES = [
        ('passport', 'Passport (Recommended)'),
        ('national_id', 'National ID Card'),
        ('drivers_license', 'Driver\'s License'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='document_verifications')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Document images
    front_image_url = models.URLField(blank=True, null=True, help_text="URL to front image of document")
    back_image_url = models.URLField(blank=True, null=True, help_text="URL to back image of document")
    
    # Extracted data from OCR
    extracted_data = models.JSONField(default=dict, help_text="Data extracted from document via OCR")
    # Fields like: name, date_of_birth, document_number, expiry_date, etc.
    
    # Verification results
    verification_score = models.FloatField(default=0.0, help_text="Verification confidence score (0-100)")
    is_authentic = models.BooleanField(default=False, help_text="Whether document appears authentic")
    rejection_reason = models.TextField(blank=True, null=True, help_text="Reason for rejection if applicable")
    
    # External service integration
    verification_service = models.CharField(max_length=50, default='internal', help_text="OCR/verification service used")
    service_response = models.JSONField(default=dict, help_text="Raw response from verification service")
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.name}'s {self.get_document_type_display()} verification ({self.status})"

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'uploaded_at']),
        ]

    def is_verified(self):
        """Check if document is verified"""
        return self.status == 'approved' and self.is_authentic
    
    def get_extracted_name(self):
        """Get extracted name from document"""
        return self.extracted_data.get('name', '')
    
    def get_extracted_date_of_birth(self):
        """Get extracted date of birth from document"""
        return self.extracted_data.get('date_of_birth', '')
    
    def get_extracted_document_number(self):
        """Get extracted document number from document"""
        return self.extracted_data.get('document_number', '')


# =============================================================================
# USERNAME VALIDATION AND SUGGESTIONS (NEW FROM FIGMA)
# =============================================================================

import re
import random
from django.core.exceptions import ValidationError

def validate_username_format(value):
    """Validate username format: letters, numbers, and underscore only"""
    if not re.match(r'^[a-zA-Z0-9_]+$', value):
        raise ValidationError('Invalid characters, use letters/numbers and underscore only')
    if len(value) < 3:
        raise ValidationError('Username must be at least 3 characters long')
    if len(value) > 30:
        raise ValidationError('Username must be less than 30 characters long')

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
        clean_username = username.lstrip('@')
        
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
        clean_username = base_username.lstrip('@')
        
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
            letter = random.choice('abcdefghijklmnopqrstuvwxyz')
            suggestion = f"{clean_username}{letter}"
            if UsernameValidation.is_username_available(suggestion):
                suggestions.append(suggestion)
        
        return suggestions[:5]  # Return max 5 suggestions