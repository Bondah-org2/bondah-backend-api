from django.contrib import admin
from .models import User, NewsletterSubscriber, PuzzleVerification, CoinTransaction, Waitlist, EmailLog, Job, JobApplication, AdminUser, AdminOTP, TranslationLog

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
