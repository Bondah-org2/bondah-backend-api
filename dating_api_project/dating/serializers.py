from rest_framework import serializers
from .models import User, NewsletterSubscriber, PuzzleVerification, CoinTransaction, Waitlist, Job, JobApplication, AdminUser, AdminOTP

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'id', 'name', 'email', 'password', 'gender', 'age', 'location', 'is_matchmaker', 'bio'
        ]

    def create(self, validated_data):
        # Set username to email if not provided
        if 'username' not in validated_data or not validated_data.get('username'):
            validated_data['username'] = validated_data['email']
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

class NewsletterSubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscriber
        fields = ['id', 'email', 'date_subscribed']
        read_only_fields = ['date_subscribed']

    def to_representation(self, instance):
        # Return the exact message format the frontend expects
        return {
            "message": "Subscription successful!",
            "status": "success"
        }


class PuzzleVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PuzzleVerification
        fields = ['id', 'user', 'question', 'user_answer', 'is_correct']
        read_only_fields = ['question', 'is_correct']

class CoinTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoinTransaction
        fields = ['id', 'user', 'transaction_type', 'amount', 'created_at']
        read_only_fields = ['created_at']

class WaitlistSerializer(serializers.ModelSerializer):
    firstName = serializers.CharField(source='first_name', write_only=True)
    lastName = serializers.CharField(source='last_name', write_only=True)
    
    class Meta:
        model = Waitlist
        fields = ['id', 'firstName', 'lastName', 'email', 'date_joined']
        read_only_fields = ['date_joined']

    def to_representation(self, instance):
        # Return the success message format as specified
        return {
            "message": "You've successfully joined the waitlist!",
            "status": "success"
        }

class NewsletterWelcomeEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    name = serializers.CharField(max_length=100, required=False, default="")

class WaitlistConfirmationEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    firstName = serializers.CharField(max_length=100)
    lastName = serializers.CharField(max_length=100)

class GenericEmailSerializer(serializers.Serializer):
    to_email = serializers.EmailField()
    subject = serializers.CharField(max_length=200)
    message = serializers.CharField()
    template_name = serializers.CharField(required=False, default="")

class JobListSerializer(serializers.ModelSerializer):
    jobType = serializers.CharField(source='job_type')
    salaryRange = serializers.CharField(source='salary_range')
    createdAt = serializers.DateTimeField(source='created_at')
    
    class Meta:
        model = Job
        fields = ['id', 'title', 'jobType', 'category', 'status', 'salaryRange', 'createdAt']

class JobDetailSerializer(serializers.ModelSerializer):
    jobType = serializers.CharField(source='job_type')
    salaryRange = serializers.CharField(source='salary_range')
    createdAt = serializers.DateTimeField(source='created_at')
    
    class Meta:
        model = Job
        fields = ['id', 'title', 'jobType', 'category', 'status', 'description', 'location', 'salaryRange', 'requirements', 'createdAt']

class JobApplicationSerializer(serializers.ModelSerializer):
    jobId = serializers.IntegerField(source='job.id', write_only=True)
    firstName = serializers.CharField(source='first_name')
    lastName = serializers.CharField(source='last_name')
    resumeUrl = serializers.URLField(source='resume_url', required=False, allow_blank=True)
    coverLetter = serializers.CharField(source='cover_letter', required=False, allow_blank=True)
    experienceYears = serializers.IntegerField(source='experience_years', required=False)
    currentCompany = serializers.CharField(source='current_company', required=False, allow_blank=True)
    expectedSalary = serializers.CharField(source='expected_salary', required=False, allow_blank=True)
    appliedAt = serializers.DateTimeField(source='applied_at', read_only=True)
    
    class Meta:
        model = JobApplication
        fields = [
            'id', 'jobId', 'firstName', 'lastName', 'email', 'phone',
            'resumeUrl', 'coverLetter', 'experienceYears', 'currentCompany',
            'expectedSalary', 'status', 'appliedAt'
        ]
        read_only_fields = ['id', 'status', 'appliedAt']

    def validate(self, data):
        # Check if job exists
        job_id = data.get('job', {}).get('id')
        try:
            job = Job.objects.get(id=job_id)
            if job.status != 'open':
                raise serializers.ValidationError("This job is not currently accepting applications.")
        except Job.DoesNotExist:
            raise serializers.ValidationError("Job not found.")
        
        # Check for duplicate application
        email = data.get('email')
        if JobApplication.objects.filter(job=job, email=email).exists():
            raise serializers.ValidationError("You have already applied for this job.")
        
        return data

    def to_representation(self, instance):
        # Return success message format
        return {
            "message": "Job application submitted successfully!",
            "status": "success",
            "applicationId": instance.id
        }

class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

class AdminOTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6)

class AdminJobCreateSerializer(serializers.ModelSerializer):
    jobType = serializers.CharField(source='job_type')
    salaryRange = serializers.CharField(source='salary_range')
    requirements = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'jobType', 'category', 'status', 'description',
            'location', 'salaryRange', 'requirements', 'responsibilities',
            'benefits', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Convert requirements list to JSON
        requirements = validated_data.pop('requirements', [])
        job = Job.objects.create(**validated_data, requirements=requirements)
        return job

class AdminJobUpdateSerializer(serializers.ModelSerializer):
    jobType = serializers.CharField(source='job_type')
    salaryRange = serializers.CharField(source='salary_range')
    requirements = serializers.ListField(child=serializers.CharField(), required=False)
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'jobType', 'category', 'status', 'description',
            'location', 'salaryRange', 'requirements', 'responsibilities',
            'benefits', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def update(self, instance, validated_data):
        # Handle requirements separately
        requirements = validated_data.pop('requirements', None)
        if requirements is not None:
            instance.requirements = requirements
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class AdminJobListSerializer(serializers.ModelSerializer):
    jobType = serializers.CharField(source='job_type')
    salaryRange = serializers.CharField(source='salary_range')
    applications_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'jobType', 'category', 'status', 'location',
            'salaryRange', 'applications_count', 'created_at'
        ]
    
    def get_applications_count(self, obj):
        return obj.applications.count()

class AdminJobApplicationSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='job.title', read_only=True)
    job_category = serializers.CharField(source='job.category', read_only=True)
    applicant_name = serializers.SerializerMethodField()
    
    class Meta:
        model = JobApplication
        fields = [
            'id', 'job_title', 'job_category', 'applicant_name', 'email',
            'phone', 'experience_years', 'current_company', 'expected_salary',
            'status', 'applied_at'
        ]
        read_only_fields = ['id', 'applied_at']
    
    def get_applicant_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"