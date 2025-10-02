import random
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator


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

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  # 'username' is still required by AbstractUser

    def __str__(self):
        return self.email
    
    @property
    def has_location(self):
        """Check if user has valid GPS coordinates"""
        return self.latitude is not None and self.longitude is not None
    
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
        ordering = ['-created_at']


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