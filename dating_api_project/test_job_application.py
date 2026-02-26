#!/usr/bin/env python
"""
Test Job Application Functionality
"""

import os
import sys
import django

def test_job_application():
    """Test job application functionality"""
    print("🧪 TESTING JOB APPLICATION")
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
        
        # Check if there are any jobs available
        jobs = Job.objects.filter(status='open')
        if not jobs.exists():
            print("❌ No open jobs available for testing")
            print("💡 Create a job first using admin panel")
            return False
        
        job = jobs.first()
        print(f"✅ Found job for testing: {job.title} (ID: {job.id})")
        
        # Test application data
        test_data = {
            "jobId": job.id,
            "firstName": "Test",
            "lastName": "User",
            "email": "test@example.com",
            "phone": "+1234567890",
            "resumeUrl": "https://example.com/resume.pdf",
            "coverLetter": "I'm excited to join the Bondah team...",
            "experienceYears": 3,
            "currentCompany": "Test Company",
            "expectedSalary": "$70,000"
        }
        
        print(f"📋 Testing with data: {test_data}")
        
        # Test serializer
        serializer = JobApplicationSerializer(data=test_data)
        if serializer.is_valid():
            print("✅ Job application serializer is valid")
            print(f"✅ Validated data: {serializer.validated_data}")
            
            # Check if application already exists
            existing_app = JobApplication.objects.filter(
                job=job, 
                email=test_data["email"]
            ).exists()
            
            if existing_app:
                print(f"⚠️  Application already exists for {test_data['email']}")
            else:
                print("✅ No existing application found")
            
            return True
        else:
            print(f"❌ Job application serializer errors: {serializer.errors}")
            return False
        
    except Exception as e:
        print(f"❌ Job application test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_job_application()
    sys.exit(0 if success else 1)
