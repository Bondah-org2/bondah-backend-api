#!/usr/bin/env python
"""
Debug Job Status Issue
"""

import os
import sys
import django

def debug_job_status():
    """Debug job status issue"""
    print("🔍 DEBUGGING JOB STATUS ISSUE")
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
        from dating.models import Job, JobApplication
        from dating.serializers import JobApplicationSerializer
        
        # 1. Check all jobs and their status
        print("\n📋 Checking all jobs...")
        jobs = Job.objects.all()
        for job in jobs:
            print(f"  Job ID: {job.id}")
            print(f"  Title: {job.title}")
            print(f"  Status: '{job.status}'")
            print(f"  Status type: {type(job.status)}")
            print(f"  Status == 'open': {job.status == 'open'}")
            print(f"  Status == 'open' (case insensitive): {job.status.lower() == 'open'}")
            print("  ---")
        
        # 2. Check specific job ID 6
        print("\n📋 Checking job ID 6 specifically...")
        try:
            job_6 = Job.objects.get(id=6)
            print(f"  Job ID: {job_6.id}")
            print(f"  Title: {job_6.title}")
            print(f"  Status: '{job_6.status}'")
            print(f"  Status type: {type(job_6.status)}")
            print(f"  Status == 'open': {job_6.status == 'open'}")
            print(f"  Status == 'open' (case insensitive): {job_6.status.lower() == 'open'}")
            print(f"  Status length: {len(str(job_6.status))}")
            print(f"  Status bytes: {repr(job_6.status)}")
        except Job.DoesNotExist:
            print("  ❌ Job ID 6 does not exist")
        
        # 3. Test serializer validation
        print("\n📋 Testing serializer validation...")
        test_data = {
            "jobId": 6,
            "firstName": "John",
            "lastName": "Doe",
            "email": "john@example.com",
            "phone": "+1234567890",
            "coverLetter": "Test application"
        }
        
        serializer = JobApplicationSerializer(data=test_data)
        if serializer.is_valid():
            print("  ✅ Serializer is valid")
        else:
            print(f"  ❌ Serializer errors: {serializer.errors}")
        
        # 4. Check database directly
        print("\n📋 Checking database directly...")
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, title, status FROM dating_job WHERE id = 6")
            result = cursor.fetchone()
            if result:
                print(f"  Database - ID: {result[0]}")
                print(f"  Database - Title: {result[1]}")
                print(f"  Database - Status: '{result[2]}'")
                print(f"  Database - Status type: {type(result[2])}")
                print(f"  Database - Status == 'open': {result[2] == 'open'}")
            else:
                print("  ❌ Job ID 6 not found in database")
        
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_job_status()
    sys.exit(0 if success else 1)
