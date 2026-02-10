from django.db import models
from django.utils import timezone
import random
import string

from .users import User
from datetime import timedelta
import uuid


class Chat(models.Model):
    """Represents a conversation between two or more users"""

    CHAT_TYPES = [
        ("direct", "Direct Message"),
        ("matchmaker_intro", "Matchmaker Introduction"),
        ("group", "Group Chat"),
    ]

    chat_type = models.CharField(max_length=20, choices=CHAT_TYPES, default="direct")
    participants = models.ManyToManyField(User, related_name="chats")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_chats",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    # Chat settings
    chat_name = models.CharField(
        max_length=100, blank=True, null=True, help_text="Custom name for group chats"
    )
    chat_theme = models.CharField(
        max_length=20,
        default="default",
        choices=[
            ("default", "Default"),
            ("dark", "Dark"),
            ("light", "Light"),
            ("colorful", "Colorful"),
        ],
    )

    def __str__(self):
        if self.chat_name:
            return f"{self.chat_name} ({self.chat_type})"
        participants = list(self.participants.all()[:2])
        if len(participants) == 2:
            return f"{participants[0].name} & {participants[1].name}"
        return f"Chat {self.id} ({self.chat_type})"

    def get_other_participant(self, user):
        """Get the other participant in a direct message chat"""
        if self.chat_type == "direct":
            return self.participants.exclude(id=user.id).first()
        return None

    def get_unread_count(self, user):
        """Get unread message count for a specific user"""
        return self.messages.filter(is_read=False).exclude(sender=user).count()

    class Meta:
        ordering = ["-last_message_at"]
        indexes = [
            models.Index(fields=["chat_type", "is_active"]),
            models.Index(fields=["last_message_at"]),
        ]


class Message(models.Model):
    """Represents an individual message within a chat"""

    MESSAGE_TYPES = [
        ("text", "Text Message"),
        ("voice_note", "Voice Note"),
        ("image", "Image"),
        ("video", "Video"),
        ("document", "Document"),
        ("system", "System Message"),
        ("matchmaker_intro", "Matchmaker Introduction"),
        ("call_start", "Call Started"),
        ("call_end", "Call Ended"),
        ("tip", "Tip Message"),
    ]

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_messages",
        help_text="Null for system messages",
    )
    message_type = models.CharField(
        max_length=20, choices=MESSAGE_TYPES, default="text"
    )
    content = models.TextField(
        blank=True, null=True, help_text="Text content of the message"
    )

    # Media attachments
    voice_note_url = models.URLField(
        blank=True, null=True, help_text="URL to the voice note audio file"
    )
    voice_note_duration = models.PositiveIntegerField(
        blank=True, null=True, help_text="Duration in seconds"
    )
    image_url = models.URLField(blank=True, null=True, help_text="URL to image file")
    video_url = models.URLField(blank=True, null=True, help_text="URL to video file")
    document_url = models.URLField(
        blank=True, null=True, help_text="URL to document file"
    )
    document_name = models.CharField(
        max_length=255, blank=True, null=True, help_text="Original document name"
    )

    # Chat tipping (NEW FROM FIGMA)
    tip_amount = models.PositiveIntegerField(
        default=0, help_text="Tip amount in Bondcoins"
    )
    tip_gift = models.ForeignKey(
        "VirtualGift",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="Gift sent with this message",
    )

    # Message metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(blank=True, null=True)

    # Reply/quote functionality
    reply_to = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="replies"
    )

    # Message reactions
    reactions = models.JSONField(
        default=dict, help_text="User reactions: {'user_id': 'emoji'}"
    )

    def __str__(self):
        sender_name = self.sender.name if self.sender else "System"
        return (
            f"{sender_name}: {self.content[:50]}..."
            if self.content
            else f"{sender_name}: {self.message_type}"
        )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update the last_message_at for the associated chat
        self.chat.last_message_at = self.timestamp
        self.chat.save(update_fields=["last_message_at"])

    def mark_as_read(self, user):
        """Mark message as read by a specific user"""
        if self.sender != user and not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])

    class Meta:
        ordering = ["timestamp"]
        indexes = [
            models.Index(fields=["chat", "timestamp"]),
            models.Index(fields=["sender", "timestamp"]),
            models.Index(fields=["message_type"]),
        ]


class VoiceNote(models.Model):
    """Store voice note metadata and processing status"""

    message = models.OneToOneField(
        Message, on_delete=models.CASCADE, related_name="voice_note"
    )
    audio_url = models.URLField(help_text="URL to the audio file")
    duration = models.PositiveIntegerField(help_text="Duration in seconds")
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    transcription = models.TextField(
        blank=True, null=True, help_text="Speech-to-text transcription"
    )
    transcription_confidence = models.FloatField(
        blank=True, null=True, help_text="Transcription confidence score"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Voice note: {self.duration}s - {self.message.chat}"

    class Meta:
        ordering = ["-created_at"]


class Call(models.Model):
    """Store voice/video call sessions"""

    CALL_TYPES = [
        ("voice", "Voice Call"),
        ("video", "Video Call"),
    ]

    CALL_STATUS = [
        ("initiated", "Initiated"),
        ("ringing", "Ringing"),
        ("active", "Active"),
        ("ended", "Ended"),
        ("missed", "Missed"),
        ("declined", "Declined"),
        ("busy", "Busy"),
    ]

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="calls")
    caller = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="initiated_calls"
    )
    callee = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="received_calls"
    )
    call_type = models.CharField(max_length=10, choices=CALL_TYPES, default="voice")
    status = models.CharField(max_length=20, choices=CALL_STATUS, default="initiated")

    # Call timing
    started_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(blank=True, null=True)
    ended_at = models.DateTimeField(blank=True, null=True)
    duration = models.PositiveIntegerField(
        blank=True, null=True, help_text="Call duration in seconds"
    )

    # Call metadata
    call_id = models.CharField(
        max_length=100, unique=True, help_text="Unique call identifier for WebRTC"
    )
    room_id = models.CharField(
        max_length=100, blank=True, null=True, help_text="WebRTC room ID"
    )
    quality_score = models.FloatField(
        blank=True, null=True, help_text="Call quality score (0-100)"
    )

    # Call settings
    is_recorded = models.BooleanField(default=False)
    recording_url = models.URLField(
        blank=True, null=True, help_text="URL to call recording"
    )

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
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["caller", "status"]),
            models.Index(fields=["callee", "status"]),
            models.Index(fields=["call_id"]),
        ]


class ChatParticipant(models.Model):
    """Track chat participant status and settings"""

    chat = models.ForeignKey(
        Chat, on_delete=models.CASCADE, related_name="chat_participants"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="chat_participations"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    # Participant settings
    notifications_enabled = models.BooleanField(default=True)
    mute_until = models.DateTimeField(
        blank=True, null=True, help_text="Mute chat until this time"
    )
    custom_nickname = models.CharField(max_length=50, blank=True, null=True)

    # Last seen
    last_seen_at = models.DateTimeField(blank=True, null=True)
    last_read_message = models.ForeignKey(
        Message, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return f"{self.user.name} in {self.chat}"

    def is_muted(self):
        """Check if participant has muted the chat"""
        if self.mute_until:
            return timezone.now() < self.mute_until
        return False

    class Meta:
        unique_together = ["chat", "user"]
        ordering = ["-joined_at"]


class ChatReport(models.Model):
    """Store chat-related reports and moderation actions"""

    REPORT_TYPES = [
        ("spam", "Spam"),
        ("harassment", "Harassment"),
        ("inappropriate_content", "Inappropriate Content"),
        ("fake_profile", "Fake Profile"),
        ("other", "Other"),
    ]

    REPORT_STATUS = [
        ("pending", "Pending"),
        ("reviewed", "Reviewed"),
        ("resolved", "Resolved"),
        ("dismissed", "Dismissed"),
    ]

    reporter = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="chat_reports_made"
    )
    reported_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="chat_reports_received"
    )
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="reports")
    message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
    )

    report_type = models.CharField(max_length=30, choices=REPORT_TYPES)
    description = models.TextField(help_text="Detailed description of the issue")
    status = models.CharField(max_length=20, choices=REPORT_STATUS, default="pending")

    # Moderation actions
    moderator_notes = models.TextField(blank=True, null=True)
    action_taken = models.CharField(max_length=100, blank=True, null=True)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_reports",
    )
    resolved_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report: {self.reporter.name} → {self.reported_user.name} ({self.report_type})"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "report_type"]),
            models.Index(fields=["reported_user", "status"]),
        ]


class LivenessVerification(models.Model):
    """Store liveness check verification data for user identity verification"""

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("passed", "Passed"),
        ("failed", "Failed"),
        ("expired", "Expired"),
    )

    ACTION_CHOICES = (
        ("turn_left", "Turn Head Left"),
        ("turn_right", "Turn Head Right"),
        ("open_mouth", "Open Mouth"),
        ("smile", "Smile"),
        ("blink", "Blink"),
        ("nod", "Nod Head"),
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="liveness_checks"
    )
    session_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Verification data
    actions_required = models.JSONField(
        default=list, help_text="List of actions user must perform"
    )
    actions_completed = models.JSONField(
        default=list, help_text="List of actions user completed"
    )
    confidence_score = models.FloatField(
        default=0.0, help_text="Confidence score (0-100)"
    )
    face_quality_score = models.FloatField(
        default=0.0, help_text="Face quality score (0-100)"
    )

    # Detection results
    is_live_person = models.BooleanField(default=False)
    spoof_detected = models.BooleanField(default=False)
    spoof_type = models.CharField(
        max_length=50, blank=True, null=True, help_text="Type of spoof detected"
    )

    # Media storage
    video_url = models.URLField(
        blank=True, null=True, help_text="URL to verification video"
    )
    images_data = models.JSONField(
        default=dict, help_text="URLs or data for verification images"
    )

    # Metadata
    verification_method = models.CharField(
        max_length=50, default="video", help_text="video, images, or session"
    )
    provider = models.CharField(
        max_length=50,
        default="internal",
        help_text="AWS, FacePlusPlus, Azure, internal",
    )
    provider_response = models.JSONField(
        default=dict, help_text="Full response from verification provider"
    )

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
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["session_id"]),
            models.Index(fields=["started_at"]),
        ]


class UserVerificationStatus(models.Model):
    """Track overall user verification status"""

    VERIFICATION_LEVEL_CHOICES = (
        ("none", "Not Verified"),
        ("email", "Email Verified"),
        ("phone", "Phone Verified"),
        ("liveness", "Liveness Verified"),
        ("full", "Fully Verified"),
    )

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="verification_status"
    )

    # Verification flags
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    liveness_verified = models.BooleanField(default=False)
    identity_verified = models.BooleanField(default=False)

    # Verification level
    verification_level = models.CharField(
        max_length=20, choices=VERIFICATION_LEVEL_CHOICES, default="none"
    )

    # Last verification dates
    email_verified_at = models.DateTimeField(blank=True, null=True)
    phone_verified_at = models.DateTimeField(blank=True, null=True)
    liveness_verified_at = models.DateTimeField(blank=True, null=True)

    # Verification badges
    verified_badge = models.BooleanField(
        default=False, help_text="Show verified badge on profile"
    )
    trusted_member = models.BooleanField(
        default=False, help_text="Trusted member status"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.verification_level}"

    def update_verification_level(self):
        """Update verification level based on completed verifications"""
        if self.liveness_verified and self.email_verified and self.phone_verified:
            self.verification_level = "full"
            self.verified_badge = True
            self.identity_verified = True
        elif self.liveness_verified:
            self.verification_level = "liveness"
            self.verified_badge = True
        elif self.phone_verified:
            self.verification_level = "phone"
        elif self.email_verified:
            self.verification_level = "email"
        else:
            self.verification_level = "none"
            self.verified_badge = False

        self.save()

    class Meta:
        verbose_name = "User Verification Status"
        verbose_name_plural = "User Verification Statuses"
        ordering = ["-updated_at"]


# Email and Phone Verification Models
class EmailVerification(models.Model):
    """Email OTP verification for user registration"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="email_verifications",
        null=True,
        blank=True,
    )
    email = models.EmailField()
    otp_code = models.CharField(max_length=4)
    is_verified = models.BooleanField(default=False)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(blank=True, null=True)
    temp_password = models.CharField(max_length=128, null=True, blank=True)
    registration_token = models.UUIDField(
        default=uuid.uuid4, editable=False,
    )

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
            email=self.email, created_at__gte=timezone.now() - timedelta(minutes=1)
        ).count()
        return recent_attempts < 3

    @classmethod
    def generate_otp(cls):
        """Generate 4-digit OTP"""

        return "".join(random.choices(string.digits, k=4))

    @classmethod
    def create_verification(cls, user, email):
        """Create new email verification"""
        # Deactivate previous verifications for this email
        cls.objects.filter(email=email, is_used=False).update(is_used=True)

        otp_code = cls.generate_otp()
        expires_at = timezone.now() + timedelta(minutes=10)

        return cls.objects.create(
            user=user, email=email, otp_code=otp_code, expires_at=expires_at
        )

    @classmethod
    def can_resend_for_email(cls, email):
        """Check if email can request new OTP"""
        recent_attempts = cls.objects.filter(
            email=email, created_at__gte=timezone.now() - timedelta(minutes=1)
        ).count()
        return recent_attempts < 3

    class Meta:
        ordering = ["-created_at"]


class PhoneVerification(models.Model):
    """Phone number OTP verification for user registration"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="phone_verifications"
    )
    phone_number = models.CharField(max_length=20)
    country_code = models.CharField(max_length=5, default="+1")
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
            created_at__gte=timezone.now() - timedelta(minutes=1),
        ).count()
        return recent_attempts < 3

    @classmethod
    def generate_otp(cls):
        """Generate 4-digit OTP"""

        return "".join(random.choices(string.digits, k=4))

    @classmethod
    def create_verification(cls, user, phone_number, country_code="+1"):
        """Create new phone verification"""
        from django.utils import timezone
        from datetime import timedelta

        # Deactivate previous verifications for this phone number
        cls.objects.filter(
            phone_number=phone_number, country_code=country_code, is_used=False
        ).update(is_used=True)

        otp_code = cls.generate_otp()
        expires_at = timezone.now() + timedelta(minutes=10)

        return cls.objects.create(
            user=user,
            phone_number=phone_number,
            country_code=country_code,
            otp_code=otp_code,
            expires_at=expires_at,
        )

    @classmethod
    def can_resend_for_phone(cls, phone_number, country_code):
        """Check if phone can request new OTP"""
        from django.utils import timezone
        from datetime import timedelta

        recent_attempts = cls.objects.filter(
            phone_number=phone_number,
            country_code=country_code,
            created_at__gte=timezone.now() - timedelta(minutes=1),
        ).count()
        return recent_attempts < 3

    class Meta:
        ordering = ["-created_at"]
