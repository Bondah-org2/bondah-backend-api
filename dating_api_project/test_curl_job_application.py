#!/usr/bin/env python
"""
Test Job Application with curl simulation
"""

import os
import sys
import django
import json
import requests

def test_curl_job_application():
    """Test job application endpoint with curl simulation"""
    print("🧪 CURL JOB APPLICATION TEST")
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
        
        # 1. Find the first open job
        print("\n📋 Finding first open job...")
        open_jobs = Job.objects.filter(status='open')
        if not open_jobs.exists():
            print("❌ No open jobs available")
            return False
        
        first_job = open_jobs.first()
        print(f"✅ Using job: {first_job.title} (ID: {first_job.id})")
        print(f"✅ Job status: {first_job.status}")
        
        # 2. Test application data
        print("\n📋 Testing job application data...")
        test_data = {
            "jobId": first_job.id,
            "firstName": "John",
            "lastName": "Doe",
            "email": "john@example.com",
            "phone": "+1234567890",
            "coverLetter": "I'm excited to join the team!"
        }
        
        print(f"📋 Test data: {test_data}")
        
        # 3. Test with requests (simulating curl)
        print("\n📋 Testing with requests (curl simulation)...")
        try:
            # Use localhost for testing
            url = "http://localhost:8000/api/jobs/apply/"
            
            response = requests.post(
                url,
                json=test_data,
                headers={'Content-Type': 'application/json'}
            )
            
            print(f"✅ Response status: {response.status_code}")
            print(f"✅ Response data: {response.json()}")
            
            if response.status_code == 201:
                print("✅ Job application created successfully!")
                return True
            else:
                print(f"❌ Job application failed with status: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            print("⚠️  Local server not running, testing with production URL...")
            
            # Test with production URL
            url = "https://bondah-backend-api-production.up.railway.app/api/jobs/apply/"
            
            response = requests.post(
                url,
                json=test_data,
                headers={'Content-Type': 'application/json'}
            )
            
            print(f"✅ Response status: {response.status_code}")
            print(f"✅ Response data: {response.json()}")
            
            if response.status_code == 201:
                print("✅ Job application created successfully!")
                return True
            else:
                print(f"❌ Job application failed with status: {response.status_code}")
                return False
        
    except Exception as e:
        print(f"❌ Job application test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_curl_job_application()
    sys.exit(0 if success else 1)
