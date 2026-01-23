from django.db import models
from django.utils import timezone

from .users import User


class Post(models.Model):
    """Represents user posts in the Bond Story feed"""

    POST_TYPES = [
        ("story", "Story"),
        ("post", "Regular Post"),
        ("announcement", "Announcement"),
    ]

    VISIBILITY_CHOICES = [
        ("public", "Public"),
        ("friends", "Friends Only"),
        ("private", "Private"),
    ]

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    post_type = models.CharField(max_length=20, choices=POST_TYPES, default="post")
    content = models.TextField(help_text="Post content/text")

    # Media attachments
    image_urls = models.JSONField(default=list, help_text="List of image URLs")
    video_url = models.URLField(blank=True, null=True, help_text="URL to video file")
    video_thumbnail = models.URLField(
        blank=True, null=True, help_text="Video thumbnail URL"
    )

    # Post metadata
    visibility = models.CharField(
        max_length=20, choices=VISIBILITY_CHOICES, default="public"
    )
    location = models.CharField(
        max_length=255, blank=True, null=True, help_text="Post location"
    )
    hashtags = models.JSONField(default=list, help_text="List of hashtags in the post")
    mentions = models.JSONField(default=list, help_text="List of mentioned user IDs")

    # Engagement metrics
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)
    bonds_count = models.PositiveIntegerField(
        default=0, help_text="Handshake/bond reactions"
    )

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
        return (
            self.likes_count
            + self.comments_count
            + self.shares_count
            + self.bonds_count
        )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["author", "created_at"]),
            models.Index(fields=["post_type", "is_active"]),
            models.Index(fields=["visibility", "created_at"]),
            models.Index(fields=["is_featured", "created_at"]),
        ]


class PostComment(models.Model):
    """Represents comments on posts"""

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="post_comments"
    )
    content = models.TextField(help_text="Comment content")

    # Reply functionality
    parent_comment = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )

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
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["post", "created_at"]),
            models.Index(fields=["author", "created_at"]),
            models.Index(fields=["parent_comment", "created_at"]),
        ]


class PostInteraction(models.Model):
    """Track user interactions with posts (likes, shares, bonds)"""

    INTERACTION_TYPES = [
        ("like", "Like"),
        ("share", "Share"),
        ("bond", "Bond/Handshake"),
        ("save", "Save"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="post_interactions"
    )
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="interactions"
    )
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name} {self.interaction_type} {self.post.id}"

    class Meta:
        unique_together = ["user", "post", "interaction_type"]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["post", "interaction_type"]),
            models.Index(fields=["user", "interaction_type"]),
        ]


class CommentInteraction(models.Model):
    """Track user interactions with comments (likes)"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="comment_interactions"
    )
    comment = models.ForeignKey(
        PostComment, on_delete=models.CASCADE, related_name="interactions"
    )
    interaction_type = models.CharField(
        max_length=20, default="like", choices=[("like", "Like")]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name} likes comment {self.comment.id}"

    class Meta:
        unique_together = ["user", "comment"]
        ordering = ["-created_at"]


class PostReport(models.Model):
    """Store reports for posts and comments"""

    REPORT_TYPES = [
        ("spam", "Spam or Misleading"),
        ("inappropriate", "Inappropriate or Offensive"),
        ("harassment", "Harassment or Bullying"),
        ("misinformation", "Misinformation"),
        ("fake", "Fake Profile"),
        ("other", "Other"),
    ]

    REPORT_STATUS = [
        ("pending", "Pending"),
        ("reviewed", "Reviewed"),
        ("resolved", "Resolved"),
        ("dismissed", "Dismissed"),
    ]

    reporter = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="post_reports_made"
    )
    reported_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="post_reports_received"
    )
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, null=True, blank=True, related_name="reports"
    )
    comment = models.ForeignKey(
        PostComment,
        on_delete=models.CASCADE,
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
        related_name="resolved_post_reports",
    )
    resolved_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        target = self.post if self.post else self.comment
        return f"Report: {self.reporter.name} → {target} ({self.report_type})"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "report_type"]),
            models.Index(fields=["reported_user", "status"]),
            models.Index(fields=["post", "status"]),
            models.Index(fields=["comment", "status"]),
        ]


class Story(models.Model):
    """Represents user stories (24-hour content)"""

    STORY_TYPES = [
        ("image", "Image Story"),
        ("video", "Video Story"),
        ("text", "Text Story"),
    ]

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="stories")
    story_type = models.CharField(max_length=20, choices=STORY_TYPES, default="image")

    # Content
    content = models.TextField(
        blank=True, null=True, help_text="Text content for text stories"
    )
    image_url = models.URLField(blank=True, null=True, help_text="URL to image file")
    video_url = models.URLField(blank=True, null=True, help_text="URL to video file")
    video_duration = models.PositiveIntegerField(
        blank=True, null=True, help_text="Video duration in seconds"
    )

    # Story metadata
    background_color = models.CharField(
        max_length=7, blank=True, null=True, help_text="Hex color for text stories"
    )
    text_color = models.CharField(
        max_length=7, blank=True, null=True, help_text="Text color for text stories"
    )
    font_size = models.PositiveIntegerField(
        default=16, help_text="Font size for text stories"
    )

    # Engagement
    views_count = models.PositiveIntegerField(default=0)
    reactions_count = models.PositiveIntegerField(default=0)

    # Status and timing
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(
        help_text="When the story expires (24 hours from creation)"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.author.name}'s {self.story_type} story"

    def is_expired(self):
        """Check if story has expired"""
        return timezone.now() > self.expires_at

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["author", "created_at"]),
            models.Index(fields=["expires_at", "is_active"]),
            models.Index(fields=["story_type", "is_active"]),
        ]


class StoryView(models.Model):
    """Track story views"""

    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="views")
    viewer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="story_views"
    )
    viewed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.viewer.name} viewed {self.story.author.name}'s story"

    class Meta:
        unique_together = ["story", "viewer"]
        ordering = ["-viewed_at"]


class StoryReaction(models.Model):
    """Track story reactions"""

    REACTION_TYPES = [
        ("like", "Like"),
        ("love", "Love"),
        ("laugh", "Laugh"),
        ("wow", "Wow"),
        ("sad", "Sad"),
        ("angry", "Angry"),
    ]

    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="story_reactions"
    )
    reaction_type = models.CharField(
        max_length=20, choices=REACTION_TYPES, default="like"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name} {self.reaction_type} {self.story.author.name}'s story"

    class Meta:
        unique_together = ["story", "user"]
        ordering = ["-created_at"]


class PostShare(models.Model):
    """Track post shares to external platforms"""

    SHARE_PLATFORMS = [
        ("whatsapp", "WhatsApp"),
        ("facebook", "Facebook"),
        ("twitter", "Twitter/X"),
        ("instagram", "Instagram"),
        ("threads", "Threads"),
        ("copy_link", "Copy Link"),
    ]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="shares")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="post_shares")
    platform = models.CharField(max_length=20, choices=SHARE_PLATFORMS)
    shared_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name} shared {self.post.id} on {self.platform}"

    class Meta:
        ordering = ["-shared_at"]
        indexes = [
            models.Index(fields=["post", "platform"]),
            models.Index(fields=["user", "shared_at"]),
        ]


class FeedSearch(models.Model):
    """Store search queries for the Bond Story feed"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="feed_searches",
        null=True,
        blank=True,
    )
    query = models.CharField(max_length=255, help_text="Search query")
    results_count = models.PositiveIntegerField(
        default=0, help_text="Number of results found"
    )
    filters_applied = models.JSONField(default=dict, help_text="Applied search filters")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Search: {self.query} ({self.results_count} results)"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["query", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]


class UserSocialHandle(models.Model):
    """Represents a user's social media handle for display on their profile."""

    PLATFORM_CHOICES = [
        ("instagram", "Instagram"),
        ("twitter", "Twitter/X"),
        ("facebook", "Facebook"),
        ("linkedin", "LinkedIn"),
        ("tiktok", "TikTok"),
        ("snapchat", "Snapchat"),
        ("youtube", "YouTube"),
        ("pinterest", "Pinterest"),
        ("website", "Personal Website"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="social_handles"
    )
    platform = models.CharField(
        max_length=50, choices=PLATFORM_CHOICES, help_text="Social media platform"
    )
    handle = models.CharField(
        max_length=100, help_text="User's handle or username on the platform"
    )
    url = models.URLField(
        blank=True, null=True, help_text="Optional direct URL to the profile"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [
            "user",
            "platform",
        ]  # A user can only have one handle per platform
        ordering = ["platform"]
        indexes = [
            models.Index(fields=["user", "platform"]),
        ]

    def __str__(self):
        return f"{self.user.name}'s {self.get_platform_display()} handle: {self.handle}"


class UserSecurityQuestion(models.Model):
    """Store user responses to security and data responsibility questions"""

    QUESTION_TYPES = [
        ("data_protection", "How will you protect user data?"),
        (
            "scam_prevention",
            "What actions will you take if you suspect a scam or fake profile?",
        ),
        ("relationship_guidance", "Do you also provide relationship guidance?"),
        (
            "matchmaking_evolution",
            "How do you see matchmaking evolving in the 21st century?",
        ),
        ("unique_skills", "What unique skills set you apart?"),
        (
            "business_service",
            "Do you run matchmaking as a business or community service?",
        ),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="security_questions"
    )
    question_type = models.CharField(max_length=50, choices=QUESTION_TYPES)
    response = models.TextField(help_text="User's response to the security question")
    is_public = models.BooleanField(
        default=False, help_text="Whether this response is shown publicly"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [
            "user",
            "question_type",
        ]  # One response per question type per user
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "question_type"]),
        ]

    def __str__(self):
        return f"{self.user.name}'s response to {self.get_question_type_display()}"


class DocumentVerification(models.Model):
    """Store document verification data for identity verification"""

    DOCUMENT_TYPES = [
        ("passport", "Passport (Recommended)"),
        ("national_id", "National ID Card"),
        ("drivers_license", "Driver's License"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="document_verifications"
    )
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Document images
    front_image_url = models.URLField(
        blank=True, null=True, help_text="URL to front image of document"
    )
    back_image_url = models.URLField(
        blank=True, null=True, help_text="URL to back image of document"
    )

    # Extracted data from OCR
    extracted_data = models.JSONField(
        default=dict, help_text="Data extracted from document via OCR"
    )
    # Fields like: name, date_of_birth, document_number, expiry_date, etc.

    # Verification results
    verification_score = models.FloatField(
        default=0.0, help_text="Verification confidence score (0-100)"
    )
    is_authentic = models.BooleanField(
        default=False, help_text="Whether document appears authentic"
    )
    rejection_reason = models.TextField(
        blank=True, null=True, help_text="Reason for rejection if applicable"
    )

    # External service integration
    verification_service = models.CharField(
        max_length=50, default="internal", help_text="OCR/verification service used"
    )
    service_response = models.JSONField(
        default=dict, help_text="Raw response from verification service"
    )

    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.name}'s {self.get_document_type_display()} verification ({self.status})"

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["status", "uploaded_at"]),
        ]

    def is_verified(self):
        """Check if document is verified"""
        return self.status == "approved" and self.is_authentic

    def get_extracted_name(self):
        """Get extracted name from document"""
        return self.extracted_data.get("name", "")

    def get_extracted_date_of_birth(self):
        """Get extracted date of birth from document"""
        return self.extracted_data.get("date_of_birth", "")

    def get_extracted_document_number(self):
        """Get extracted document number from document"""
        return self.extracted_data.get("document_number", "")