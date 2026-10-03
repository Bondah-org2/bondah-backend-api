#!/usr/bin/env python
"""
Test Waitlist Functionality
"""

import os
import sys
import django

def test_waitlist():
    """Test waitlist functionality"""
    print("🧪 TESTING WAITLIST")
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
        from dating.models import Waitlist, EmailLog
        from dating.serializers import WaitlistSerializer
        from django.conf import settings
        
        print(f"📧 Email backend: {settings.EMAIL_BACKEND}")
        print(f"📧 Email host: {settings.EMAIL_HOST}")
        print(f"📧 Email port: {settings.EMAIL_PORT}")
        print(f"📧 Email user: {settings.EMAIL_HOST_USER}")
        print(f"📧 Default from: {settings.DEFAULT_FROM_EMAIL}")
        
        # Test waitlist creation without email
        test_data = {
            "email": "test@example.com",
            "firstName": "Test",
            "lastName": "User"
        }
        
        serializer = WaitlistSerializer(data=test_data)
        if serializer.is_valid():
            print("✅ Waitlist serializer is valid")
            
            # Check if email already exists
            email = test_data["email"]
            if Waitlist.objects.filter(email=email).exists():
                print(f"⚠️  Email already exists: {email}")
            else:
                print("✅ Email doesn't exist, can create waitlist entry")
        else:
            print(f"❌ Waitlist serializer errors: {serializer.errors}")
            return False
        
        # Test email configuration
        try:
            from django.core.mail import send_mail
            print("✅ Email module imported successfully")
        except Exception as e:
            print(f"❌ Email module error: {str(e)}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Waitlist test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_waitlist()
    sys.exit(0 if success else 1)
