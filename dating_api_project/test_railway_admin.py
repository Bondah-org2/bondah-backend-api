#!/usr/bin/env python
"""
Test Railway Admin Login
"""

import requests
import json

def test_railway_admin():
    """Test admin login on Railway"""
    print("🔐 TESTING RAILWAY ADMIN LOGIN")
    print("=" * 50)
    
    # Test data
    url = "https://bondah-backend-api-production.up.railway.app/api/admin/login/"
    data = {
        "email": "admin@bondah.org",
        "password": "BondahAdmin2025!"
    }
    
    print(f"📋 Testing URL: {url}")
    print(f"📋 Test Data: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(url, json=data, headers={'Content-Type': 'application/json'})
        
        print(f"\n📋 Response Status: {response.status_code}")
        print(f"📋 Response Data: {response.json()}")
        
        if response.status_code == 200:
            print("\n✅ SUCCESS! Admin login is working!")
            print("📧 OTP should be sent to admin@bondah.org")
            print("\n🎉 The frontend developer can now use these credentials:")
            print("   Email: admin@bondah.org")
            print("   Password: BondahAdmin2025!")
            return True
        else:
            print(f"\n❌ Admin login failed with status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ Request failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_railway_admin()
    exit(0 if success else 1)
