from django.contrib import admin
from .models import (
    User, NewsletterSubscriber, PuzzleVerification, CoinTransaction, Waitlist, 
    EmailLog, Job, JobApplication, AdminUser, AdminOTP, TranslationLog,
    SocialAccount, DeviceRegistration, LocationHistory, UserMatch, LocationPermission,
    LivenessVerification, UserVerificationStatus, EmailVerification, PhoneVerification, UserRoleSelection,
    UserInterest, UserProfileView, UserInteraction, SearchQuery, RecommendationEngine
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
