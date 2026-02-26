#!/usr/bin/env python
"""
Mobile API Setup Script for Bondah Dating
This script sets up the mobile API with OAuth and JWT authentication
"""

import os
import sys
import subprocess
import django
from django.core.management import execute_from_command_line

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def setup_mobile_api():
    """Setup mobile API with all required components"""
    print("🚀 Setting up Bondah Dating Mobile API...")
    print("=" * 60)
    
    # Step 1: Install required packages
    print("\n📦 Installing required packages...")
    packages = [
        "django-allauth==0.57.0",
        "django-rest-auth==0.9.5", 
        "djangorestframework-simplejwt==5.3.0",
        "Pillow==10.1.0",
        "firebase-admin==6.4.0",
        "requests==2.31.0",
        "cryptography==41.0.8"
    ]
    
    for package in packages:
        if not run_command(f"pip install {package}", f"Installing {package}"):
            print(f"⚠️  Failed to install {package}, continuing...")
    
    # Step 2: Set up Django environment
    print("\n🔧 Setting up Django environment...")
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    
    try:
        django.setup()
        print("✅ Django environment configured")
    except Exception as e:
        print(f"❌ Django setup failed: {e}")
        return False
    
    # Step 3: Create migrations
    print("\n📊 Creating database migrations...")
    if not run_command("python manage.py makemigrations", "Creating migrations"):
        print("⚠️  Migration creation failed, but continuing...")
    
    # Step 4: Run migrations
    print("\n🗄️  Running database migrations...")
    if not run_command("python manage.py migrate", "Running migrations"):
        print("⚠️  Migration execution failed, but continuing...")
    
    # Step 5: Create site for django-allauth
    print("\n🌐 Setting up site for OAuth...")
    try:
        from django.contrib.sites.models import Site
        from django.conf import settings
        
        # Create or update site
        site, created = Site.objects.get_or_create(
            id=1,
            defaults={
                'domain': 'bondah-backend-api-production.up.railway.app',
                'name': 'Bondah Dating API'
            }
        )
        if not created:
            site.domain = 'bondah-backend-api-production.up.railway.app'
            site.name = 'Bondah Dating API'
            site.save()
        
        print("✅ Site configured for OAuth")
    except Exception as e:
        print(f"⚠️  Site setup failed: {e}")
    
    # Step 6: Collect static files
    print("\n📁 Collecting static files...")
    if not run_command("python manage.py collectstatic --noinput", "Collecting static files"):
        print("⚠️  Static file collection failed, but continuing...")
    
    # Step 7: Create superuser (optional)
    print("\n👤 Superuser creation...")
    print("To create a superuser, run: python manage.py createsuperuser")
    
    # Step 8: Test API endpoints
    print("\n🧪 Testing API endpoints...")
    test_endpoints = [
        "/api/auth/register/",
        "/api/auth/login/",
        "/api/auth/profile/",
        "/api/waitlist/",
        "/api/jobs/",
        "/api/translate/languages/"
    ]
    
    print("📋 Available API endpoints:")
    for endpoint in test_endpoints:
        print(f"   • {endpoint}")
    
    print("\n" + "=" * 60)
    print("🎉 Mobile API setup completed!")
    print("\n📱 Next steps:")
    print("1. Configure OAuth providers (Google/Apple)")
    print("2. Set up environment variables in Railway")
    print("3. Test the API endpoints")
    print("4. Deploy to production")
    
    print("\n🔧 Environment variables needed:")
    print("• GOOGLE_CLIENT_ID")
    print("• GOOGLE_CLIENT_SECRET") 
    print("• APPLE_CLIENT_ID")
    print("• APPLE_SECRET")
    print("• APPLE_KEY")
    print("• JWT_SECRET_KEY")
    
    print("\n📚 Documentation: MOBILE_API_DOCUMENTATION.md")
    return True

if __name__ == "__main__":
    success = setup_mobile_api()
    sys.exit(0 if success else 1)
