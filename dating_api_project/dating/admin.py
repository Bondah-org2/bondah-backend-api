from django.contrib import admin
from .models import (
    User, NewsletterSubscriber, PuzzleVerification, CoinTransaction, Waitlist, 
    EmailLog, Job, JobApplication, AdminUser, AdminOTP, TranslationLog,
    SocialAccount, DeviceRegistration, LocationHistory, UserMatch, LocationPermission,
    LivenessVerification, UserVerificationStatus
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
    list_display = ('user', 'provider', 'provider_id', 'created_at')
    list_filter = ('provider', 'created_at')
    search_fields = ('user__email', 'provider_id')

# Device and Location Models
@admin.register(DeviceRegistration)
class DeviceRegistrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_id', 'device_type', 'is_active', 'last_seen')
    list_filter = ('device_type', 'is_active', 'last_seen')
    search_fields = ('user__email', 'device_id')

@admin.register(LocationHistory)
class LocationHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'latitude', 'longitude', 'address', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'address')

@admin.register(UserMatch)
class UserMatchAdmin(admin.ModelAdmin):
    list_display = ('user1', 'user2', 'match_type', 'created_at')
    list_filter = ('match_type', 'created_at')
    search_fields = ('user1__email', 'user2__email')

@admin.register(LocationPermission)
class LocationPermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'permission_type', 'is_granted', 'created_at')
    list_filter = ('permission_type', 'is_granted', 'created_at')
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
