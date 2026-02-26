#!/usr/bin/env python
"""
Complete Job Application Test
"""

import os
import sys
import django

def test_job_application_complete():
    """Test complete job application functionality"""
    print("🧪 TESTING JOB APPLICATION COMPLETE")
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
        from django.test import RequestFactory
        
        # 1. Check if there are any jobs available
        print("\n📋 Checking available jobs...")
        jobs = Job.objects.all()
        if not jobs.exists():
            print("❌ No jobs available in database")
            print("💡 Creating a sample job for testing...")
            
            # Create a sample job
            sample_job = Job.objects.create(
                title="Backend Developer",
                job_type="full-time",
                category="engineering",
                status="open",
                description="We are looking for a talented backend developer to join our team.",
                location="Remote",
                salary_range="$80,000 - $120,000",
                requirements=["Python", "Django", "PostgreSQL", "REST APIs"],
                responsibilities="Develop and maintain backend services, work with the team on new features.",
                benefits="Health insurance, flexible hours, remote work"
            )
            print(f"✅ Created sample job: {sample_job.title} (ID: {sample_job.id})")
        else:
            sample_job = jobs.first()
            print(f"✅ Found existing job: {sample_job.title} (ID: {sample_job.id})")
        
        # 2. Test application data
        print("\n📋 Testing job application data...")
        test_data = {
            "jobId": sample_job.id,
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
            
            # Test the view
            view = JobApplicationView()
            response = view.create(request)
            
            print(f"✅ View response status: {response.status_code}")
            print(f"✅ View response data: {response.data}")
            
            if response.status_code == 201:
                print("✅ Job application created successfully!")
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
    success = test_job_application_complete()
    sys.exit(0 if success else 1)
