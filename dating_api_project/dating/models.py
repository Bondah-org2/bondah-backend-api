import random
from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    age = models.PositiveIntegerField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    is_matchmaker = models.BooleanField(default=False)
    bio = models.TextField(blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  # 'username' is still required by AbstractUser

    def __str__(self):
        return self.email



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
