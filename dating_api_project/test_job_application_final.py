#!/usr/bin/env python
"""
Final Job Application Test - Uses First Available Open Job
"""

import os
import sys
import django

def test_job_application_final():
    """Test job application with first available open job"""
    print("🧪 FINAL JOB APPLICATION TEST")
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
        from dating.views import JobApplicationView
        from rest_framework.test import APIRequestFactory
        
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
            "resumeUrl": "https://example.com/resume.pdf",
            "coverLetter": "I'm excited to join the Bondah team and help build the future of dating technology. I have 5 years of experience in backend development and am passionate about creating scalable solutions.",
            "experienceYears": 5,
            "currentCompany": "Tech Solutions Inc",
            "expectedSalary": "$90,000"
        }
        
        print(f"📋 Test data: {test_data}")
        
        # 3. Test serializer
        print("\n📋 Testing serializer...")
        serializer = JobApplicationSerializer(data=test_data)
        if serializer.is_valid():
            print("✅ Job application serializer is valid")
            print(f"✅ Validated data: {serializer.validated_data}")
        else:
            print(f"❌ Job application serializer errors: {serializer.errors}")
            return False
        
        # 4. Test view directly
        print("\n📋 Testing view directly...")
        try:
            factory = APIRequestFactory()
            request = factory.post('/api/jobs/apply/', test_data, format='json')
            
            # Test the view properly with all required attributes
            view = JobApplicationView()
            view.request = request
            view.format_kwarg = 'format'
            view.kwargs = {}
            view.args = []
            
            response = view.create(request)
            
            print(f"✅ View response status: {response.status_code}")
            print(f"✅ View response data: {response.data}")
            
            if response.status_code == 201:
                print("✅ Job application created successfully!")
                print(f"✅ Application ID: {response.data.get('applicationId')}")
                return True
            else:
                print(f"❌ Job application failed with status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ View test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"❌ Job application test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_job_application_final()
    sys.exit(0 if success else 1)
