#!/usr/bin/env python
"""
Debug Waitlist Creation Issue
"""
import os
import sys
import django
import requests
import json

def debug_waitlist_creation():
    """Debug why new waitlist entries aren't being saved"""
    print("🔍 DEBUGGING WAITLIST CREATION ISSUE")
    print("=" * 50)
    
    # Test production endpoint directly
    print("\n📋 Testing production waitlist endpoint...")
    try:
        url = "https://bondah-backend-api-production.up.railway.app/api/waitlist/"
        test_data = {
            "email": f"debug_test_{int(time.time())}@example.com",
            "firstName": "Debug",
            "lastName": "Test"
        }
        
        print(f"📋 Test data: {test_data}")
        print(f"📋 URL: {url}")
        
        response = requests.post(url, json=test_data, headers={'Content-Type': 'application/json'})
        print(f"✅ Response status: {response.status_code}")
        print(f"✅ Response content: {response.text}")
        
        if response.status_code in [200, 201]:
            print("✅ API returned success")
            
            # Check if entry was actually created
            print("\n📋 Checking if entry was created in database...")
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
            django.setup()
            
            from dating.models import Waitlist
            
            # Check for the test entry
            test_entry = Waitlist.objects.filter(email=test_data['email']).first()
            if test_entry:
                print(f"✅ Entry found in database: {test_entry}")
                
                # Clean up
                test_entry.delete()
                print("✅ Test entry cleaned up")
            else:
                print("❌ Entry NOT found in database despite API success!")
                
                # Check all recent entries
                recent_entries = Waitlist.objects.all().order_by('-date_joined')[:5]
                print(f"\n📋 Recent entries in database:")
                for entry in recent_entries:
                    print(f"  - {entry}")
                    
        else:
            print(f"❌ API returned error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Check database connection
    print("\n📋 Checking database connection...")
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM dating_waitlist")
            count = cursor.fetchone()[0]
            print(f"✅ Database connection working, total entries: {count}")
            
            # Check recent entries
            cursor.execute("""
                SELECT id, email, first_name, last_name, date_joined 
                FROM dating_waitlist 
                ORDER BY date_joined DESC 
                LIMIT 5
            """)
            entries = cursor.fetchall()
            print(f"\n📋 Recent database entries:")
            for entry in entries:
                print(f"  - ID: {entry[0]}, Email: {entry[1]}, Name: {entry[2]} {entry[3]}, Date: {entry[4]}")
                
    except Exception as e:
        print(f"❌ Database check failed: {str(e)}")

if __name__ == "__main__":
    import time
    debug_waitlist_creation()
