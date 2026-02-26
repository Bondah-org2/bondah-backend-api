#!/usr/bin/env python
"""
Bulletproof Waitlist Test
"""
import os
import sys
import django
import json
import requests

def test_waitlist_bulletproof():
    """Test the bulletproof waitlist endpoint"""
    print("🧪 BULLETPROOF WAITLIST TEST")
    print("=" * 50)
    
    # Test production URL directly
    print("\n📋 Testing production waitlist endpoint...")
    try:
        url = "https://bondah-backend-api-production.up.railway.app/api/waitlist/"
        test_data = {
            "email": f"test{int(time.time())}@example.com",  # Unique email
            "firstName": "Test",
            "lastName": "User"
        }
        
        print(f"📋 Test data: {test_data}")
        print(f"📋 URL: {url}")
        
        response = requests.post(url, json=test_data, headers={'Content-Type': 'application/json'})
        print(f"✅ Response status: {response.status_code}")
        print(f"✅ Response headers: {dict(response.headers)}")
        print(f"✅ Response content: {response.text}")
        
        if response.status_code in [200, 201]:
            print("✅ SUCCESS: Waitlist endpoint is working!")
            return True
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import time
    success = test_waitlist_bulletproof()
    sys.exit(0 if success else 1)
