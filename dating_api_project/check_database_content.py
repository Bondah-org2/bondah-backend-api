#!/usr/bin/env python
"""
Check Database Content - See what's available in the database
"""

import os
import sys
import django

def check_database_content():
    """Check what's currently available in the database"""
    print("🔍 CHECKING DATABASE CONTENT")
    print("=" * 50)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
    
    try:
        django.setup()
        print("✅ Django setup successful")
    except Exception as e:
        print(f"❌ Django setup failed: {str(e)}")
        return False
    
    try:
        from dating.models import User, Job, JobApplication, AdminUser, Waitlist, NewsletterSubscriber, EmailLog, TranslationLog
        
        # 1. Check Users
        print("\n📋 USERS:")
        users = User.objects.all()
        print(f"   Total Users: {users.count()}")
        for user in users[:5]:  # Show first 5
            print(f"   - {user.email} (Active: {user.is_active})")
        if users.count() > 5:
            print(f"   ... and {users.count() - 5} more")
        
        # 2. Check Jobs
        print("\n📋 JOBS:")
        jobs = Job.objects.all()
        print(f"   Total Jobs: {jobs.count()}")
        for job in jobs:
            print(f"   - ID {job.id}: {job.title} ({job.status}) - {job.category}")
        
        # 3. Check Job Applications
        print("\n📋 JOB APPLICATIONS:")
        applications = JobApplication.objects.all()
        print(f"   Total Applications: {applications.count()}")
        for app in applications:
            print(f"   - ID {app.id}: {app.first_name} {app.last_name} for {app.job.title} (Status: {app.status})")
        
        # 4. Check Admin Users
        print("\n📋 ADMIN USERS:")
        admin_users = AdminUser.objects.all()
        print(f"   Total Admin Users: {admin_users.count()}")
        for admin in admin_users:
            print(f"   - {admin.email} (Active: {admin.is_active})")
        
        # 5. Check Waitlist
        print("\n📋 WAITLIST:")
        waitlist = Waitlist.objects.all()
        print(f"   Total Waitlist Entries: {waitlist.count()}")
        for entry in waitlist[:5]:  # Show first 5
            print(f"   - {entry.first_name} {entry.last_name} ({entry.email})")
        if waitlist.count() > 5:
            print(f"   ... and {waitlist.count() - 5} more")
        
        # 6. Check Newsletter Subscribers
        print("\n📋 NEWSLETTER SUBSCRIBERS:")
        subscribers = NewsletterSubscriber.objects.all()
        print(f"   Total Subscribers: {subscribers.count()}")
        for sub in subscribers[:5]:  # Show first 5
            print(f"   - {sub.email}")
        if subscribers.count() > 5:
            print(f"   ... and {subscribers.count() - 5} more")
        
        # 7. Check Email Logs
        print("\n📋 EMAIL LOGS:")
        email_logs = EmailLog.objects.all()
        print(f"   Total Email Logs: {email_logs.count()}")
        for log in email_logs[:5]:  # Show first 5
            print(f"   - {log.email_type} to {log.recipient_email} ({'Sent' if log.is_sent else 'Failed'})")
        if email_logs.count() > 5:
            print(f"   ... and {email_logs.count() - 5} more")
        
        # 8. Check Translation Logs
        print("\n📋 TRANSLATION LOGS:")
        translation_logs = TranslationLog.objects.all()
        print(f"   Total Translation Logs: {translation_logs.count()}")
        for log in translation_logs[:5]:  # Show first 5
            print(f"   - {log.source_language} → {log.target_language} ({log.character_count} chars)")
        if translation_logs.count() > 5:
            print(f"   ... and {translation_logs.count() - 5} more")
        
        # 9. Summary
        print("\n📊 DATABASE SUMMARY:")
        print(f"   Users: {User.objects.count()}")
        print(f"   Jobs: {Job.objects.count()}")
        print(f"   Applications: {JobApplication.objects.count()}")
        print(f"   Admin Users: {AdminUser.objects.count()}")
        print(f"   Waitlist: {Waitlist.objects.count()}")
        print(f"   Newsletter: {NewsletterSubscriber.objects.count()}")
        print(f"   Email Logs: {EmailLog.objects.count()}")
        print(f"   Translation Logs: {TranslationLog.objects.count()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database check failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_database_content()
    sys.exit(0 if success else 1)
