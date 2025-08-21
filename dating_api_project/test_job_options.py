#!/usr/bin/env python
"""
Test Job Options Endpoint
"""

import os
import sys
import django

def test_job_options():
    """Test job options endpoint"""
    print("🧪 TESTING JOB OPTIONS ENDPOINT")
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
        from dating.models import Job
        from dating.views import JobOptionsView
        from rest_framework.test import APIRequestFactory
        
        # Create a test request
        factory = APIRequestFactory()
        request = factory.get('/api/jobs/options/')
        
        # Test the view
        view = JobOptionsView()
        response = view.get(request)
        
        print(f"✅ Response status: {response.status_code}")
        print(f"✅ Response data: {response.data}")
        
        # Check if we have the expected data
        if 'categories' in response.data and 'job_types' in response.data:
            print(f"✅ Categories count: {len(response.data['categories'])}")
            print(f"✅ Job types count: {len(response.data['job_types'])}")
            
            # Show some examples
            print("\n📋 Sample Categories:")
            for cat in response.data['categories'][:3]:
                print(f"  - {cat['value']}: {cat['label']}")
            
            print("\n📋 Sample Job Types:")
            for job_type in response.data['job_types'][:3]:
                print(f"  - {job_type['value']}: {job_type['label']}")
            
            return True
        else:
            print("❌ Missing expected data in response")
            return False
        
    except Exception as e:
        print(f"❌ Job options test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_job_options()
    sys.exit(0 if success else 1)
