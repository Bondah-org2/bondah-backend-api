#!/usr/bin/env python
"""
Debug Waitlist 500 Error
"""
import os
import sys
import django
import json
import requests

def debug_waitlist_500():
    """Debug the waitlist 500 error"""
    print("🔍 DEBUGGING WAITLIST 500 ERROR")
    print("=" * 50)
    
    # Test local first
    print("\n📋 Testing local waitlist endpoint...")
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
        django.setup()
        
        from dating.views import JoinWaitlistView
        from django.test import RequestFactory
        from django.http import JsonResponse
        
        # Create test request
        factory = RequestFactory()
        test_data = {
            "email": "test@example.com",
            "firstName": "Test",
            "lastName": "User"
        }
        
        request = factory.post('/api/waitlist/', 
                             data=json.dumps(test_data),
                             content_type='application/json')
        
        # Test the view directly
        view = JoinWaitlistView()
        response = view.post(request)
        
        print(f"✅ Local test response: {response.status_code}")
        if hasattr(response, 'content'):
            print(f"✅ Response content: {response.content.decode()}")
        
    except Exception as e:
        print(f"❌ Local test failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Test production URL
    print("\n📋 Testing production waitlist endpoint...")
    try:
        url = "https://bondah-backend-api-production.up.railway.app/api/waitlist/"
        test_data = {
            "email": "test@example.com",
            "firstName": "Test",
            "lastName": "User"
        }
        
        response = requests.post(url, json=test_data, headers={'Content-Type': 'application/json'})
        print(f"✅ Production response status: {response.status_code}")
        print(f"✅ Production response: {response.text}")
        
        if response.status_code == 500:
            print("❌ 500 error confirmed on production")
            print("📋 Checking if it's an email configuration issue...")
            
            # Test without email sending
            print("\n📋 Testing with email disabled...")
            # This would require modifying the view temporarily
            
    except Exception as e:
        print(f"❌ Production test failed: {str(e)}")
    
    # Check email configuration
    print("\n📋 Checking email configuration...")
    try:
        from django.conf import settings
        print(f"✅ EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'Not set')}")
        print(f"✅ EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', 'Not set')}")
        print(f"✅ EMAIL_HOST_PASSWORD: {'Set' if getattr(settings, 'EMAIL_HOST_PASSWORD', None) else 'Not set'}")
        print(f"✅ DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'Not set')}")
    except Exception as e:
        print(f"❌ Email config check failed: {str(e)}")

if __name__ == "__main__":
    debug_waitlist_500()
