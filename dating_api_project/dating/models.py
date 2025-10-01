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