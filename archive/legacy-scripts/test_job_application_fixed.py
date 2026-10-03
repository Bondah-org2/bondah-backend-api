#!/usr/bin/env python
"""
Test Job Application After Schema Fix
"""

import requests
import json

def test_job_application():
    """Test job application after schema fix"""
    print("🧪 TESTING JOB APPLICATION AFTER SCHEMA FIX")
    print("=" * 50)
    
    # Test data
    url = "https://bondah-backend-api-production.up.railway.app/api/jobs/apply/"
    data = {
        "jobId": 5,
        "firstName": "John",
        "lastName": "Doe",
        "email": "test@example.com",
        "phone": "+1234567890",
        "coverLetter": "This is a test application to verify the fix works."
    }
    
    print(f"📋 Testing URL: {url}")
    print(f"📋 Test Data: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(url, json=data, headers={'Content-Type': 'application/json'})
        
        print(f"\n📋 Response Status: {response.status_code}")
        print(f"📋 Response Data: {response.json()}")
        
        if response.status_code == 201:
            print("\n✅ SUCCESS! Job application is working!")
            print("🎉 The frontend developer can now use the job application feature")
            return True
        else:
            print(f"\n❌ Job application failed with status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ Request failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_job_application()
    exit(0 if success else 1)
