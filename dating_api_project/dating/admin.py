from django.contrib import admin
from .models import (
    User, NewsletterSubscriber, PuzzleVerification, CoinTransaction, Waitlist, 
    EmailLog, Job, JobApplication, AdminUser, AdminOTP, TranslationLog,
    SocialAccount, DeviceRegistration, LocationHistory, UserMatch, LocationPermission,
    LivenessVerification, UserVerificationStatus, EmailVerification, PhoneVerification, UserRoleSelection,
    UserInterest, UserProfileView, UserInteraction, SearchQuery, RecommendationEngine,
    # Chat and Messaging Models (NEW)
    Chat, Message, VoiceNote, Call, ChatParticipant, ChatReport,
    # Social Feed and Story Models (NEW)
    Post, PostComment, PostInteraction, CommentInteraction, PostReport,
    Story, StoryView, StoryReaction, PostShare, FeedSearch,
    # Live Session Models (NEW)
    LiveSession, LiveParticipant,
    # New Figma Features
    UserSocialHandle, UserSecurityQuestion, DocumentVerification,
    # Subscription and Monetization Features (NEW FROM FIGMA)
    SubscriptionPlan, UserSubscription, BondcoinPackage, BondcoinTransaction,
    GiftCategory, VirtualGift, GiftTransaction, LiveGift, LiveJoinRequest,
    # Payment Processing Models
    PaymentMethod, PaymentTransaction, PaymentWebhook
)

# Register your models here.

@admin.register(Waitlist)
class WaitlistAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'date_joined')
    list_filter = ('date_joined',)
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined',)
    
    def get_queryset(self, request):
        """Ensure we get all waitlist entries"""
        return super().get_queryset(request).order_by('-date_joined')

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'is_matchmaker', 'date_joined')
    search_fields = ('email', 'name')
    list_filter = ('is_matchmaker', 'date_joined')

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'date_subscribed')
    search_fields = ('email',)
    ordering = ('-date_subscribed',)

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'job_type', 'status', 'created_at')
    list_filter = ('status', 'category', 'job_type')
    search_fields = ('title', 'description')

@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'job', 'status', 'applied_at')
    list_filter = ('status', 'applied_at')
    search_fields = ('email', 'first_name', 'last_name')

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('email_type', 'recipient_email', 'is_sent', 'sent_at')
    list_filter = ('email_type', 'is_sent', 'sent_at')
    search_fields = ('recipient_email',)

@admin.register(AdminUser)
class AdminUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'created_at')
    search_fields = ('email',)

@admin.register(AdminOTP)
class AdminOTPAdmin(admin.ModelAdmin):
    list_display = ('admin_user', 'otp_code', 'is_used', 'created_at', 'expires_at')
    list_filter = ('is_used', 'created_at')

@admin.register(TranslationLog)
class TranslationLogAdmin(admin.ModelAdmin):
    list_display = ('source_text', 'target_language', 'translated_text', 'created_at')
    list_filter = ('target_language', 'created_at')
    search_fields = ('source_text', 'translated_text')

# Register other models
admin.site.register(PuzzleVerification)
admin.site.register(CoinTransaction)

# OAuth and Social Authentication Models
@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'provider_user_id', 'is_active', 'created_at')
    list_filter = ('provider', 'is_active', 'created_at')
    search_fields = ('user__email', 'provider_user_id')

# Device and Location Models
@admin.register(DeviceRegistration)
class DeviceRegistrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_id', 'device_type', 'is_active', 'created_at')
    list_filter = ('device_type', 'is_active', 'created_at')
    search_fields = ('user__email', 'device_id')

@admin.register(LocationHistory)
class LocationHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'latitude', 'longitude', 'address', 'timestamp')
    list_filter = ('timestamp', 'source')
    search_fields = ('user__email', 'address')

@admin.register(UserMatch)
class UserMatchAdmin(admin.ModelAdmin):
    list_display = ('user1', 'user2', 'status', 'distance', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user1__email', 'user2__email')

@admin.register(LocationPermission)
class LocationPermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'location_enabled', 'precise_location_enabled', 'location_data_sharing', 'created_at')
    list_filter = ('location_enabled', 'precise_location_enabled', 'location_data_sharing', 'created_at')
    search_fields = ('user__email',)

# Liveness Verification Models
@admin.register(LivenessVerification)
class LivenessVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_id', 'status', 'is_live_person', 'confidence_score', 'started_at')
    list_filter = ('status', 'is_live_person', 'spoof_detected', 'started_at')
    search_fields = ('user__email', 'session_id')
    readonly_fields = ('session_id', 'started_at', 'completed_at', 'confidence_score', 'face_quality_score')
    
    fieldsets = (
        ('Session Info', {
            'fields': ('user', 'session_id', 'status', 'attempts_count', 'max_attempts')
        }),
        ('Verification Results', {
            'fields': ('is_live_person', 'spoof_detected', 'spoof_type', 'confidence_score', 'face_quality_score')
        }),
        ('Actions', {
            'fields': ('actions_required', 'actions_completed')
        }),
        ('Timestamps', {
            'fields': ('started_at', 'completed_at', 'expires_at')
        }),
        ('Technical Details', {
            'fields': ('verification_method', 'provider', 'provider_response', 'video_url', 'images_data'),
            'classes': ('collapse',)
        })
    )

@admin.register(UserVerificationStatus)
class UserVerificationStatusAdmin(admin.ModelAdmin):
    list_display = ('user', 'verification_level', 'email_verified', 'phone_verified', 'liveness_verified', 'verified_badge')
    list_filter = ('verification_level', 'email_verified', 'phone_verified', 'liveness_verified', 'verified_badge', 'trusted_member')
    search_fields = ('user__email',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Verification Status', {
            'fields': ('email_verified', 'phone_verified', 'liveness_verified', 'identity_verified')
        }),
        ('Verification Level', {
            'fields': ('verification_level', 'verified_badge', 'trusted_member')
        }),
        ('Verification Dates', {
            'fields': ('email_verified_at', 'phone_verified_at', 'liveness_verified_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )

# Email and Phone Verification Models
@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'email', 'otp_code', 'is_verified', 'is_used', 'created_at', 'expires_at')
    list_filter = ('is_verified', 'is_used', 'created_at')
    search_fields = ('user__email', 'email', 'otp_code')
    readonly_fields = ('otp_code', 'created_at', 'expires_at', 'verified_at')
    
    fieldsets = (
        ('Verification Info', {
            'fields': ('user', 'email', 'otp_code')
        }),
        ('Status', {
            'fields': ('is_verified', 'is_used')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'expires_at', 'verified_at')
        })
    )

@admin.register(PhoneVerification)
class PhoneVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'country_code', 'otp_code', 'is_verified', 'is_used', 'created_at', 'expires_at')
    list_filter = ('is_verified', 'is_used', 'country_code', 'created_at')
    search_fields = ('user__email', 'phone_number', 'otp_code')
    readonly_fields = ('otp_code', 'created_at', 'expires_at', 'verified_at')
    
    fieldsets = (
        ('Verification Info', {
            'fields': ('user', 'phone_number', 'country_code', 'otp_code')
        }),
        ('Status', {
            'fields': ('is_verified', 'is_used')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'expires_at', 'verified_at')
        })
    )

@admin.register(UserRoleSelection)
class UserRoleSelectionAdmin(admin.ModelAdmin):
    list_display = ('user', 'selected_role', 'selected_at')
    list_filter = ('selected_role', 'selected_at')
    search_fields = ('user__email',)
    readonly_fields = ('selected_at',)
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Role Selection', {
            'fields': ('selected_role', 'selected_at')
        })
    )


# Advanced Search and Discovery Models
@admin.register(UserInterest)
class UserInterestAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(UserProfileView)
class UserProfileViewAdmin(admin.ModelAdmin):
    list_display = ('viewer', 'viewed_user', 'source', 'viewed_at')
    list_filter = ('source', 'viewed_at')
    search_fields = ('viewer__email', 'viewed_user__email')
    ordering = ('-viewed_at',)

@admin.register(UserInteraction)
class UserInteractionAdmin(admin.ModelAdmin):
    list_display = ('user', 'target_user', 'interaction_type', 'created_at')
    list_filter = ('interaction_type', 'created_at')
    search_fields = ('user__email', 'target_user__email')
    ordering = ('-created_at',)

@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ('user', 'query', 'results_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'query')
    ordering = ('-created_at',)

@admin.register(RecommendationEngine)
class RecommendationEngineAdmin(admin.ModelAdmin):
    list_display = ('user', 'recommended_user', 'score', 'algorithm', 'is_active', 'created_at')
    list_filter = ('algorithm', 'is_active', 'created_at')
    search_fields = ('user__email', 'recommended_user__email')
    ordering = ('-score',)


# =============================================================================
# CHAT AND MESSAGING ADMIN (NEW)
# =============================================================================

@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('id', 'chat_type', 'chat_name', 'created_by', 'is_active', 'created_at', 'last_message_at')
    list_filter = ('chat_type', 'is_active', 'created_at')
    search_fields = ('chat_name', 'created_by__email')
    ordering = ('-last_message_at',)
    readonly_fields = ('created_at', 'updated_at', 'last_message_at')
    
    fieldsets = (
        ('Chat Info', {
            'fields': ('chat_type', 'chat_name', 'created_by', 'is_active')
        }),
        ('Participants', {
            'fields': ('participants',)
        }),
        ('Settings', {
            'fields': ('chat_theme',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_message_at')
        })
    )
    
    filter_horizontal = ('participants',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'chat', 'sender', 'message_type', 'content_preview', 'is_read', 'timestamp')
    list_filter = ('message_type', 'is_read', 'is_edited', 'timestamp')
    search_fields = ('content', 'sender__email', 'chat__chat_name')
    ordering = ('-timestamp',)
    readonly_fields = ('timestamp', 'read_at', 'edited_at')
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if obj.content and len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'
    
    fieldsets = (
        ('Message Info', {
            'fields': ('chat', 'sender', 'message_type', 'content')
        }),
        ('Media Attachments', {
            'fields': ('voice_note_url', 'voice_note_duration', 'image_url', 'video_url', 'document_url', 'document_name'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_read', 'read_at', 'is_edited', 'edited_at')
        }),
        ('Reply', {
            'fields': ('reply_to',)
        }),
        ('Reactions', {
            'fields': ('reactions',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('timestamp',)
        })
    )


@admin.register(VoiceNote)
class VoiceNoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'duration', 'file_size', 'has_transcription', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('message__content', 'transcription')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    
    def has_transcription(self, obj):
        return bool(obj.transcription)
    has_transcription.boolean = True
    has_transcription.short_description = 'Has Transcription'
    
    fieldsets = (
        ('Voice Note Info', {
            'fields': ('message', 'audio_url', 'duration', 'file_size')
        }),
        ('Transcription', {
            'fields': ('transcription', 'transcription_confidence')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        })
    )


@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ('id', 'caller', 'callee', 'call_type', 'status', 'duration_display', 'started_at', 'ended_at')
    list_filter = ('call_type', 'status', 'started_at')
    search_fields = ('caller__email', 'callee__email', 'call_id')
    ordering = ('-started_at',)
    readonly_fields = ('started_at', 'answered_at', 'ended_at', 'duration', 'duration_display')
    
    def duration_display(self, obj):
        return obj.get_duration_display()
    duration_display.short_description = 'Duration'
    
    fieldsets = (
        ('Call Info', {
            'fields': ('chat', 'caller', 'callee', 'call_type', 'status')
        }),
        ('Call Details', {
            'fields': ('call_id', 'room_id', 'quality_score')
        }),
        ('Timing', {
            'fields': ('started_at', 'answered_at', 'ended_at', 'duration', 'duration_display')
        }),
        ('Recording', {
            'fields': ('is_recorded', 'recording_url'),
            'classes': ('collapse',)
        })
    )


@admin.register(ChatParticipant)
class ChatParticipantAdmin(admin.ModelAdmin):
    list_display = ('id', 'chat', 'user', 'is_active', 'notifications_enabled', 'joined_at', 'last_seen_at')
    list_filter = ('is_active', 'notifications_enabled', 'joined_at')
    search_fields = ('user__email', 'chat__chat_name')
    ordering = ('-joined_at',)
    readonly_fields = ('joined_at', 'left_at', 'last_seen_at')
    
    fieldsets = (
        ('Participant Info', {
            'fields': ('chat', 'user', 'is_active')
        }),
        ('Settings', {
            'fields': ('notifications_enabled', 'mute_until', 'custom_nickname')
        }),
        ('Activity', {
            'fields': ('last_seen_at', 'last_read_message')
        }),
        ('Timestamps', {
            'fields': ('joined_at', 'left_at')
        })
    )


@admin.register(ChatReport)
class ChatReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'reporter', 'reported_user', 'report_type', 'status', 'created_at')
    list_filter = ('report_type', 'status', 'created_at')
    search_fields = ('reporter__email', 'reported_user__email', 'description')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'resolved_at')
    
    fieldsets = (
        ('Report Info', {
            'fields': ('reporter', 'reported_user', 'chat', 'message')
        }),
        ('Report Details', {
            'fields': ('report_type', 'description', 'status')
        }),
        ('Moderation', {
            'fields': ('moderator_notes', 'action_taken', 'resolved_by', 'resolved_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        })
    )


# =============================================================================
# SOCIAL FEED AND STORY ADMIN (NEW)
# =============================================================================

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'post_type', 'content_preview', 'likes_count', 'comments_count', 'is_active', 'created_at')
    list_filter = ('post_type', 'visibility', 'is_active', 'is_featured', 'created_at')
    search_fields = ('content', 'author__email', 'location', 'hashtags')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'likes_count', 'comments_count', 'shares_count', 'bonds_count')
    
    def content_preview(self, obj):
        return obj.content[:100] + '...' if obj.content and len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content Preview'
    
    fieldsets = (
        ('Post Info', {
            'fields': ('author', 'post_type', 'content', 'visibility', 'location')
        }),
        ('Media', {
            'fields': ('image_urls', 'video_url', 'video_thumbnail'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('hashtags', 'mentions'),
            'classes': ('collapse',)
        }),
        ('Engagement', {
            'fields': ('likes_count', 'comments_count', 'shares_count', 'bonds_count')
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured', 'is_reported')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )


@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'author', 'content_preview', 'likes_count', 'replies_count', 'is_active', 'created_at')
    list_filter = ('is_active', 'is_edited', 'created_at')
    search_fields = ('content', 'author__email', 'post__content')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'likes_count', 'replies_count')
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if obj.content and len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'
    
    fieldsets = (
        ('Comment Info', {
            'fields': ('post', 'author', 'content', 'parent_comment')
        }),
        ('Engagement', {
            'fields': ('likes_count', 'replies_count')
        }),
        ('Status', {
            'fields': ('is_active', 'is_edited')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )


@admin.register(PostInteraction)
class PostInteractionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'post', 'interaction_type', 'created_at')
    list_filter = ('interaction_type', 'created_at')
    search_fields = ('user__email', 'post__content')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(CommentInteraction)
class CommentInteractionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'comment', 'interaction_type', 'created_at')
    list_filter = ('interaction_type', 'created_at')
    search_fields = ('user__email', 'comment__content')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(PostReport)
class PostReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'reporter', 'reported_user', 'report_type', 'status', 'created_at')
    list_filter = ('report_type', 'status', 'created_at')
    search_fields = ('reporter__email', 'reported_user__email', 'description')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'resolved_at')
    
    fieldsets = (
        ('Report Info', {
            'fields': ('reporter', 'reported_user', 'post', 'comment')
        }),
        ('Report Details', {
            'fields': ('report_type', 'description', 'status')
        }),
        ('Moderation', {
            'fields': ('moderator_notes', 'action_taken', 'resolved_by', 'resolved_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        })
    )


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'story_type', 'content_preview', 'views_count', 'reactions_count', 'is_active', 'expires_at')
    list_filter = ('story_type', 'is_active', 'created_at', 'expires_at')
    search_fields = ('content', 'author__email')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'views_count', 'reactions_count', 'expires_at')
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if obj.content and len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'
    
    fieldsets = (
        ('Story Info', {
            'fields': ('author', 'story_type', 'content')
        }),
        ('Media', {
            'fields': ('image_url', 'video_url', 'video_duration'),
            'classes': ('collapse',)
        }),
        ('Text Story Settings', {
            'fields': ('background_color', 'text_color', 'font_size'),
            'classes': ('collapse',)
        }),
        ('Engagement', {
            'fields': ('views_count', 'reactions_count')
        }),
        ('Status', {
            'fields': ('is_active', 'expires_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        })
    )


@admin.register(StoryView)
class StoryViewAdmin(admin.ModelAdmin):
    list_display = ('id', 'story', 'viewer', 'viewed_at')
    list_filter = ('viewed_at',)
    search_fields = ('story__author__email', 'viewer__email')
    ordering = ('-viewed_at',)
    readonly_fields = ('viewed_at',)


@admin.register(StoryReaction)
class StoryReactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'story', 'user', 'reaction_type', 'created_at')
    list_filter = ('reaction_type', 'created_at')
    search_fields = ('story__author__email', 'user__email')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(PostShare)
class PostShareAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'user', 'platform', 'shared_at')
    list_filter = ('platform', 'shared_at')
    search_fields = ('post__content', 'user__email')
    ordering = ('-shared_at',)
    readonly_fields = ('shared_at',)


@admin.register(FeedSearch)
class FeedSearchAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'query', 'results_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('query', 'user__email')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Search Info', {
            'fields': ('user', 'query', 'results_count')
        }),
        ('Filters', {
            'fields': ('filters_applied',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        })
    )


# =============================================================================
# LIVE SESSION ADMIN (NEW)
# =============================================================================

@admin.register(LiveSession)
class LiveSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'status', 'viewers_count', 'start_time', 'end_time')
    list_filter = ('status', 'start_time', 'end_time')
    search_fields = ('title', 'description', 'user__email')
    ordering = ('-start_time',)
    readonly_fields = ('created_at', 'updated_at', 'viewers_count', 'likes_count')
    
    fieldsets = (
        ('Session Info', {
            'fields': ('user', 'title', 'description', 'status')
        }),
        ('Timing', {
            'fields': ('start_time', 'end_time', 'duration_limit_minutes')
        }),
        ('Metrics', {
            'fields': ('viewers_count', 'likes_count')
        }),
        ('Stream Details', {
            'fields': ('stream_url', 'thumbnail_url'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )


@admin.register(LiveParticipant)
class LiveParticipantAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'user', 'role', 'joined_at', 'left_at')
    list_filter = ('role', 'joined_at', 'left_at')
    search_fields = ('session__title', 'user__email')
    ordering = ('-joined_at',)
    readonly_fields = ('joined_at', 'left_at')
    
    fieldsets = (
        ('Participation Info', {
            'fields': ('session', 'user', 'role')
        }),
        ('Timing', {
            'fields': ('joined_at', 'left_at')
        })
    )


# =============================================================================
# NEW FIGMA FEATURES ADMIN (NEW)
# =============================================================================

@admin.register(UserSocialHandle)
class UserSocialHandleAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'platform', 'handle', 'created_at')
    list_filter = ('platform', 'created_at')
    search_fields = ('user__email', 'handle', 'platform')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Social Handle Info', {
            'fields': ('user', 'platform', 'handle', 'url')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )


@admin.register(UserSecurityQuestion)
class UserSecurityQuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'question_type', 'is_public', 'created_at')
    list_filter = ('question_type', 'is_public', 'created_at')
    search_fields = ('user__email', 'response')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Question Response', {
            'fields': ('user', 'question_type', 'response', 'is_public')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )


@admin.register(DocumentVerification)
class DocumentVerificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'document_type', 'status', 'verification_score', 'uploaded_at')
    list_filter = ('document_type', 'status', 'uploaded_at', 'is_authentic')
    search_fields = ('user__email', 'extracted_data')
    ordering = ('-uploaded_at',)
    readonly_fields = ('uploaded_at', 'processed_at', 'verified_at', 'updated_at', 'extracted_data', 'service_response')
    
    fieldsets = (
        ('Verification Info', {
            'fields': ('user', 'document_type', 'status')
        }),
        ('Document Images', {
            'fields': ('front_image_url', 'back_image_url')
        }),
        ('Extracted Data', {
            'fields': ('extracted_data',),
            'classes': ('collapse',)
        }),
        ('Verification Results', {
            'fields': ('verification_score', 'is_authentic', 'rejection_reason')
        }),
        ('Service Integration', {
            'fields': ('verification_service', 'service_response'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('uploaded_at', 'processed_at', 'verified_at', 'updated_at')
        })
    )


# =============================================================================
# SUBSCRIPTION PLANS ADMIN (NEW FROM FIGMA)
# =============================================================================

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'display_name', 'duration', 'price_bondcoins', 'price_usd', 'is_active')
    list_filter = ('name', 'duration', 'is_active', 'unlimited_swipes', 'undo_swipes', 'global_access')
    search_fields = ('name', 'display_name', 'description')
    ordering = ('price_bondcoins',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Plan Info', {
            'fields': ('name', 'display_name', 'description', 'duration')
        }),
        ('Pricing', {
            'fields': ('price_bondcoins', 'price_usd')
        }),
        ('Features', {
            'fields': ('unlimited_swipes', 'undo_swipes', 'unlimited_unwind', 'global_access', 'read_receipt', 'live_hours_days')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'plan', 'status', 'start_date', 'end_date', 'is_active')
    list_filter = ('status', 'payment_method', 'auto_renew', 'plan__name', 'start_date')
    search_fields = ('user__email', 'user__name', 'transaction_id')
    ordering = ('-created_at',)
    readonly_fields = ('start_date', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Subscription Info', {
            'fields': ('user', 'plan', 'status')
        }),
        ('Period', {
            'fields': ('start_date', 'end_date')
        }),
        ('Payment', {
            'fields': ('payment_method', 'transaction_id', 'auto_renew')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )


# =============================================================================
# BONDCOIN WALLET ADMIN (NEW FROM FIGMA)
# =============================================================================

@admin.register(BondcoinPackage)
class BondcoinPackageAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'bondcoin_amount', 'price_usd', 'is_popular', 'is_active')
    list_filter = ('is_popular', 'is_active', 'created_at')
    search_fields = ('name',)
    ordering = ('bondcoin_amount',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Package Info', {
            'fields': ('name', 'bondcoin_amount', 'price_usd')
        }),
        ('Status', {
            'fields': ('is_popular', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )


@admin.register(BondcoinTransaction)
class BondcoinTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'transaction_type', 'amount', 'status', 'description', 'created_at')
    list_filter = ('transaction_type', 'status', 'payment_method', 'created_at')
    search_fields = ('user__email', 'user__name', 'description', 'payment_reference')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Transaction Info', {
            'fields': ('user', 'transaction_type', 'amount', 'status', 'description')
        }),
        ('Related Objects', {
            'fields': ('package', 'subscription', 'gift')
        }),
        ('Payment Info', {
            'fields': ('payment_method', 'payment_reference')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )


# =============================================================================
# VIRTUAL GIFTING ADMIN (NEW FROM FIGMA)
# =============================================================================

@admin.register(GiftCategory)
class GiftCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'display_name', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'display_name', 'description')
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Category Info', {
            'fields': ('name', 'display_name', 'description', 'icon_url')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )


@admin.register(VirtualGift)
class VirtualGiftAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'cost_bondcoins', 'is_popular', 'is_active')
    list_filter = ('category', 'is_popular', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('category', 'cost_bondcoins')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Gift Info', {
            'fields': ('name', 'category', 'description', 'icon_url')
        }),
        ('Pricing', {
            'fields': ('cost_bondcoins',)
        }),
        ('Status', {
            'fields': ('is_popular', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )


@admin.register(GiftTransaction)
class GiftTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'recipient', 'gift', 'quantity', 'total_cost', 'status', 'created_at')
    list_filter = ('status', 'context_type', 'created_at')
    search_fields = ('sender__email', 'sender__name', 'recipient__email', 'recipient__name', 'gift__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Transaction Info', {
            'fields': ('sender', 'recipient', 'gift', 'quantity', 'total_cost', 'status')
        }),
        ('Context', {
            'fields': ('context_type', 'context_id', 'message')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )


# =============================================================================
# LIVE STREAMING ENHANCEMENT ADMIN (NEW FROM FIGMA)
# =============================================================================

@admin.register(LiveGift)
class LiveGiftAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'sender', 'gift', 'quantity', 'total_cost', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('session__user__name', 'sender__name', 'gift__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Gift Info', {
            'fields': ('session', 'sender', 'gift', 'quantity', 'total_cost')
        }),
        ('Chat Message', {
            'fields': ('chat_message',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        })
    )


@admin.register(LiveJoinRequest)
class LiveJoinRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'requester', 'requested_role', 'status', 'created_at')
    list_filter = ('requested_role', 'status', 'created_at')
    search_fields = ('session__user__name', 'requester__name', 'message')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Request Info', {
            'fields': ('session', 'requester', 'requested_role', 'status', 'message')
        }),
        ('Response', {
            'fields': ('responded_by', 'response_message', 'responded_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'is_active', 'processing_fee_percentage', 'min_amount', 'max_amount', 'created_at']
    list_filter = ['is_active', 'name', 'created_at']
    search_fields = ['name', 'display_name', 'description']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'display_name', 'description', 'icon_url')
        }),
        ('Settings', {
            'fields': ('is_active', 'processing_fee_percentage', 'min_amount', 'max_amount')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_type', 'payment_method', 'amount_usd', 'total_amount', 'status', 'provider', 'created_at']
    list_filter = ['status', 'transaction_type', 'payment_method', 'provider', 'currency', 'created_at']
    search_fields = ['user__name', 'user__email', 'description', 'provider_transaction_id']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'processed_at']
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('user', 'transaction_type', 'payment_method', 'amount_usd', 'processing_fee', 'total_amount', 'currency')
        }),
        ('Status', {
            'fields': ('status', 'processed_at')
        }),
        ('Payment Provider', {
            'fields': ('provider', 'provider_transaction_id', 'provider_response')
        }),
        ('Related Objects', {
            'fields': ('subscription', 'bondcoin_transaction')
        }),
        ('Metadata', {
            'fields': ('description', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )


@admin.register(PaymentWebhook)
class PaymentWebhookAdmin(admin.ModelAdmin):
    list_display = ['provider', 'event_type', 'event_id', 'processed', 'created_at']
    list_filter = ['provider', 'event_type', 'processed', 'created_at']
    search_fields = ['provider', 'event_type', 'event_id', 'processing_error']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'processed_at']
    
    fieldsets = (
        ('Webhook Details', {
            'fields': ('provider', 'event_type', 'event_id', 'transaction')
        }),
        ('Processing Status', {
            'fields': ('processed', 'processing_error', 'processed_at')
        }),
        ('Payload', {
            'fields': ('payload',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        })
    )
