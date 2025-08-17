from django.contrib import admin
from .models import User, NewsletterSubscriber, PuzzleVerification, CoinTransaction, Waitlist, EmailLog, Job, JobApplication, AdminUser, AdminOTP

# Register your models here.

admin.site.register(User)
admin.site.register(NewsletterSubscriber)
admin.site.register(PuzzleVerification)
admin.site.register(CoinTransaction)
admin.site.register(Waitlist)
admin.site.register(EmailLog)
admin.site.register(Job)
admin.site.register(JobApplication)
admin.site.register(AdminUser)
admin.site.register(AdminOTP)
