from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from .models import User, NewsletterSubscriber, PuzzleVerification, CoinTransaction, Waitlist, Job, JobApplication, AdminUser, AdminOTP, TranslationLog, SocialAccount, DeviceRegistration, LocationHistory, UserMatch, LocationPermission, LivenessVerification, UserVerificationStatus, EmailVerification, PhoneVerification, UserRoleSelection, UserInterest, UserProfileView, UserInteraction, SearchQuery, RecommendationEngine, Chat, Message, VoiceNote, Call, ChatParticipant, ChatReport, Post, PostComment, PostInteraction, CommentInteraction, PostReport, Story, StoryView, StoryReaction, PostShare, FeedSearch, LiveSession, LiveParticipant, UserSocialHandle, UserSecurityQuestion, DocumentVerification, UsernameValidation, SubscriptionPlan, UserSubscription, BondcoinPackage, BondcoinTransaction, GiftCategory, VirtualGift, GiftTransaction, LiveGift, LiveJoinRequest, PaymentMethod, PaymentTransaction, PaymentWebhook

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'id', 'name', 'email', 'password', 'gender', 'age', 'location', 'is_matchmaker', 'bio',
            'profile_picture', 'profile_gallery', 'education_level', 'height', 'zodiac_sign',
            'languages', 'relationship_status', 'smoking_preference', 'drinking_preference',
            'pet_preference', 'exercise_frequency', 'kids_preference', 'personality_type',
            'love_language', 'communication_style', 'hobbies', 'interests', 'marriage_plans',
            'kids_plans', 'religion_importance', 'religion', 'dating_type', 'open_to_long_distance',
            'looking_for', 'push_notifications_enabled', 'email_notifications_enabled', 'preferred_language',
            'bondcoin_balance'
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


class UserProfileDetailSerializer(serializers.ModelSerializer):
    """Enhanced user profile serializer with profile completion percentage"""
    profile_completion_percentage = serializers.IntegerField(source='get_profile_completion_percentage', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'name', 'email', 'gender', 'age', 'location', 'bio', 'is_matchmaker',
            'profile_picture', 'profile_gallery', 'education_level', 'height', 'zodiac_sign',
            'languages', 'relationship_status', 'smoking_preference', 'drinking_preference',
            'pet_preference', 'exercise_frequency', 'kids_preference', 'personality_type',
            'love_language', 'communication_style', 'hobbies', 'interests', 'marriage_plans',
            'kids_plans', 'religion_importance', 'religion', 'dating_type', 'open_to_long_distance',
            'looking_for', 'push_notifications_enabled', 'email_notifications_enabled', 
            'preferred_language', 'profile_completion_percentage'
        ]
        read_only_fields = ['id', 'email', 'profile_completion_percentage']


class NotificationSettingsSerializer(serializers.ModelSerializer):
    """Serializer for notification settings"""
    
    class Meta:
        model = User
        fields = ['push_notifications_enabled', 'email_notifications_enabled']
    
    def update(self, instance, validated_data):
        """Update notification settings"""
        instance.push_notifications_enabled = validated_data.get('push_notifications_enabled', instance.push_notifications_enabled)
        instance.email_notifications_enabled = validated_data.get('email_notifications_enabled', instance.email_notifications_enabled)
        instance.save()
        return instance


class LanguageSettingsSerializer(serializers.ModelSerializer):
    """Serializer for language settings"""
    
    class Meta:
        model = User
        fields = ['preferred_language']
    
    def update(self, instance, validated_data):
        """Update language settings"""
        instance.preferred_language = validated_data.get('preferred_language', instance.preferred_language)
        instance.save()
        return instance


# =============================================================================
# LIVE SESSION SERIALIZERS (NEW)
# =============================================================================

class LiveSessionSerializer(serializers.ModelSerializer):
    """Serializer for live sessions"""
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_profile_picture = serializers.URLField(source='user.profile_picture', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    current_duration = serializers.DurationField(source='get_current_duration', read_only=True)
    
    class Meta:
        model = LiveSession
        fields = [
            'id', 'user', 'user_name', 'user_profile_picture', 'title', 'description',
            'subject_matter', 'start_time', 'end_time', 'status', 'duration_limit_minutes', 'viewers_count',
            'likes_count', 'stream_url', 'thumbnail_url', 'is_active', 'current_duration',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'user_name', 'user_profile_picture', 'start_time', 'end_time',
            'viewers_count', 'likes_count', 'is_active', 'current_duration', 'created_at', 'updated_at'
        ]


class LiveSessionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating live sessions"""
    
    class Meta:
        model = LiveSession
        fields = ['title', 'description', 'duration_limit_minutes']
    
    def create(self, validated_data):
        """Create live session with current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


class LiveParticipantSerializer(serializers.ModelSerializer):
    """Serializer for live session participants"""
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_profile_picture = serializers.URLField(source='user.profile_picture', read_only=True)
    
    class Meta:
        model = LiveParticipant
        fields = [
            'id', 'session', 'user', 'user_name', 'user_profile_picture', 'role',
            'joined_at', 'left_at'
        ]
        read_only_fields = ['id', 'session', 'user', 'user_name', 'user_profile_picture', 'joined_at', 'left_at']


# =============================================================================
# SOCIAL MEDIA HANDLES SERIALIZERS (NEW FROM FIGMA)
# =============================================================================

class UserSocialHandleSerializer(serializers.ModelSerializer):
    """Serializer for user social media handles"""
    
    class Meta:
        model = UserSocialHandle
        fields = [
            'id', 'platform', 'handle', 'url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserSocialHandleCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating user social media handles"""
    
    class Meta:
        model = UserSocialHandle
        fields = ['platform', 'handle', 'url']
    
    def create(self, validated_data):
        """Create social handle with current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


# =============================================================================
# SECURITY QUESTIONS SERIALIZERS (NEW FROM FIGMA)
# =============================================================================

class UserSecurityQuestionSerializer(serializers.ModelSerializer):
    """Serializer for user security questions"""
    
    class Meta:
        model = UserSecurityQuestion
        fields = [
            'id', 'question_type', 'response', 'is_public', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserSecurityQuestionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating user security question responses"""
    
    class Meta:
        model = UserSecurityQuestion
        fields = ['question_type', 'response', 'is_public']
    
    def create(self, validated_data):
        """Create security question response with current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


# =============================================================================
# DOCUMENT VERIFICATION SERIALIZERS (NEW FROM FIGMA)
# =============================================================================

class DocumentVerificationSerializer(serializers.ModelSerializer):
    """Serializer for document verification"""
    user_name = serializers.CharField(source='user.name', read_only=True)
    is_verified = serializers.BooleanField(read_only=True)
    extracted_name = serializers.CharField(source='get_extracted_name', read_only=True)
    extracted_date_of_birth = serializers.CharField(source='get_extracted_date_of_birth', read_only=True)
    extracted_document_number = serializers.CharField(source='get_extracted_document_number', read_only=True)
    
    class Meta:
        model = DocumentVerification
        fields = [
            'id', 'user', 'user_name', 'document_type', 'status', 'front_image_url',
            'back_image_url', 'extracted_data', 'verification_score', 'is_authentic',
            'rejection_reason', 'verification_service', 'service_response',
            'uploaded_at', 'processed_at', 'verified_at', 'updated_at',
            'is_verified', 'extracted_name', 'extracted_date_of_birth', 'extracted_document_number'
        ]
        read_only_fields = [
            'id', 'user', 'user_name', 'status', 'extracted_data', 'verification_score',
            'is_authentic', 'rejection_reason', 'service_response', 'uploaded_at',
            'processed_at', 'verified_at', 'updated_at', 'is_verified',
            'extracted_name', 'extracted_date_of_birth', 'extracted_document_number'
        ]


class DocumentVerificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating document verification requests"""
    
    class Meta:
        model = DocumentVerification
        fields = ['document_type', 'front_image_url', 'back_image_url']
    
    def create(self, validated_data):
        """Create document verification with current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


# =============================================================================
# USERNAME VALIDATION SERIALIZERS (NEW FROM FIGMA)
# =============================================================================

class UsernameValidationSerializer(serializers.Serializer):
    """Serializer for username validation"""
    username = serializers.CharField(max_length=30)
    is_valid = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    suggestions = serializers.ListField(child=serializers.CharField(), read_only=True)
    
    def validate(self, data):
        """Validate username and return results"""
        username = data.get('username')
        is_valid, message, suggestions = UsernameValidation.validate_username(username)
        
        data['is_valid'] = is_valid
        data['message'] = message
        data['suggestions'] = suggestions
        
        return data


class UsernameUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user username"""
    
    class Meta:
        model = User
        fields = ['username']
    
    def validate_username(self, value):
        """Validate username format and availability"""
        # Remove @ symbol if present
        clean_username = value.lstrip('@')
        
        # Check if username is available (excluding current user)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if User.objects.filter(username=clean_username).exclude(id=request.user.id).exists():
                raise serializers.ValidationError("Username already taken.")
        else:
            if User.objects.filter(username=clean_username).exists():
                raise serializers.ValidationError("Username already taken.")
        
        # Validate format
        from .models import validate_username_format
        try:
            validate_username_format(clean_username)
        except Exception as e:
            raise serializers.ValidationError(str(e))
        
        return clean_username


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

class AdminJobApplicationDetailSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='job.title', read_only=True)
    job_category = serializers.CharField(source='job.category', read_only=True)
    job_type = serializers.CharField(source='job.job_type', read_only=True)
    job_location = serializers.CharField(source='job.location', read_only=True)
    job_salary_range = serializers.CharField(source='job.salary_range', read_only=True)
    applicant_name = serializers.SerializerMethodField()
    cover_letter = serializers.CharField(source='cover_letter', read_only=True)
    resume_url = serializers.URLField(source='resume_url', read_only=True)
    
    class Meta:
        model = JobApplication
        fields = [
            'id', 'job_title', 'job_category', 'job_type', 'job_location', 'job_salary_range',
            'applicant_name', 'email', 'phone', 'cover_letter', 'resume_url',
            'experience_years', 'current_company', 'expected_salary',
            'status', 'applied_at', 'updated_at'
        ]
        read_only_fields = ['id', 'applied_at', 'updated_at']
    
    def get_applicant_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

class TranslationRequestSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=5000)  # Limit text length
    source_language = serializers.CharField(max_length=10, required=False, default='auto')
    target_language = serializers.CharField(max_length=10)
    
    def validate_target_language(self, value):
        # Supported languages
        supported_languages = {
            'en': 'English',
            'en-US': 'English (US)',
            'en-GB': 'English (UK)',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'nl': 'Dutch',
            'ar': 'Arabic',
            'zh': 'Chinese (Simplified)',
            'zh-TW': 'Chinese (Traditional)',
            'ja': 'Japanese',
            'ko': 'Korean',
            'pt': 'Portuguese',
            'it': 'Italian',
            'ru': 'Russian',
            'hi': 'Hindi',
            'bn': 'Bengali',
            'tr': 'Turkish',
            'pl': 'Polish',
            'vi': 'Vietnamese',
            'th': 'Thai',
            'id': 'Indonesian',
            'ms': 'Malay',
            'fa': 'Persian',
            'he': 'Hebrew',
            'sv': 'Swedish',
            'da': 'Danish',
            'no': 'Norwegian',
            'fi': 'Finnish',
            'cs': 'Czech',
            'sk': 'Slovak',
            'hu': 'Hungarian',
            'ro': 'Romanian',
            'bg': 'Bulgarian',
            'hr': 'Croatian',
            'sl': 'Slovenian',
            'et': 'Estonian',
            'lv': 'Latvian',
            'lt': 'Lithuanian',
            'mt': 'Maltese',
            'el': 'Greek',
            'uk': 'Ukrainian',
            'be': 'Belarusian',
            'mk': 'Macedonian',
            'sq': 'Albanian',
            'bs': 'Bosnian',
            'sr': 'Serbian',
            'me': 'Montenegrin',
            'ka': 'Georgian',
            'hy': 'Armenian',
            'az': 'Azerbaijani',
            'kk': 'Kazakh',
            'ky': 'Kyrgyz',
            'uz': 'Uzbek',
            'tg': 'Tajik',
            'mn': 'Mongolian',
            'ne': 'Nepali',
            'si': 'Sinhala',
            'my': 'Burmese',
            'km': 'Khmer',
            'lo': 'Lao',
            'gl': 'Galician',
            'eu': 'Basque',
            'ca': 'Catalan',
            'cy': 'Welsh',
            'ga': 'Irish',
            'is': 'Icelandic',
            'fo': 'Faroese',
            'kl': 'Greenlandic',
            'sm': 'Samoan',
            'to': 'Tongan',
            'fj': 'Fijian',
            'haw': 'Hawaiian',
            'mi': 'Maori',
            'sw': 'Swahili',
            'yo': 'Yoruba',
            'ig': 'Igbo',
            'ha': 'Hausa',
            'zu': 'Zulu',
            'xh': 'Xhosa',
            'af': 'Afrikaans',
            'am': 'Amharic',
            'ti': 'Tigrinya',
            'so': 'Somali',
            'om': 'Oromo',
            'rw': 'Kinyarwanda',
            'lg': 'Ganda',
            'ak': 'Akan',
            'tw': 'Twi',
            'ee': 'Ewe',
            'fon': 'Fon',
            'sn': 'Shona',
            'ny': 'Chichewa',
            'st': 'Southern Sotho',
            'tn': 'Tswana',
            'ts': 'Tsonga',
            've': 'Venda',
            'ss': 'Swati',
            'nr': 'Southern Ndebele',
            'nd': 'Northern Ndebele',
        }
        
        if value not in supported_languages:
            raise serializers.ValidationError(f"Unsupported language: {value}. Supported languages: {', '.join(supported_languages.keys())}")
        
        return value

class TranslationResponseSerializer(serializers.ModelSerializer):
    source_language_name = serializers.SerializerMethodField()
    target_language_name = serializers.SerializerMethodField()
    
    class Meta:
        model = TranslationLog
        fields = [
            'id', 'source_text', 'translated_text', 'source_language', 
            'target_language', 'source_language_name', 'target_language_name',
            'character_count', 'translation_time', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_source_language_name(self, obj):
        language_names = {
            'en': 'English', 'en-US': 'English (US)', 'en-GB': 'English (UK)',
            'es': 'Spanish', 'fr': 'French', 'de': 'German', 'nl': 'Dutch',
            'ar': 'Arabic', 'zh': 'Chinese (Simplified)', 'zh-TW': 'Chinese (Traditional)',
            'ja': 'Japanese', 'ko': 'Korean', 'pt': 'Portuguese', 'it': 'Italian',
            'ru': 'Russian', 'hi': 'Hindi', 'bn': 'Bengali', 'tr': 'Turkish',
            'pl': 'Polish', 'vi': 'Vietnamese', 'th': 'Thai', 'id': 'Indonesian',
            'ms': 'Malay', 'fa': 'Persian', 'he': 'Hebrew', 'sv': 'Swedish',
            'da': 'Danish', 'no': 'Norwegian', 'fi': 'Finnish', 'cs': 'Czech',
            'sk': 'Slovak', 'hu': 'Hungarian', 'ro': 'Romanian', 'bg': 'Bulgarian',
            'hr': 'Croatian', 'sl': 'Slovenian', 'et': 'Estonian', 'lv': 'Latvian',
            'lt': 'Lithuanian', 'mt': 'Maltese', 'el': 'Greek', 'uk': 'Ukrainian',
            'be': 'Belarusian', 'mk': 'Macedonian', 'sq': 'Albanian', 'bs': 'Bosnian',
            'sr': 'Serbian', 'me': 'Montenegrin', 'ka': 'Georgian', 'hy': 'Armenian',
            'az': 'Azerbaijani', 'kk': 'Kazakh', 'ky': 'Kyrgyz', 'uz': 'Uzbek',
            'tg': 'Tajik', 'mn': 'Mongolian', 'ne': 'Nepali', 'si': 'Sinhala',
            'my': 'Burmese', 'km': 'Khmer', 'lo': 'Lao', 'gl': 'Galician',
            'eu': 'Basque', 'ca': 'Catalan', 'cy': 'Welsh', 'ga': 'Irish',
            'is': 'Icelandic', 'fo': 'Faroese', 'kl': 'Greenlandic', 'sm': 'Samoan',
            'to': 'Tongan', 'fj': 'Fijian', 'haw': 'Hawaiian', 'mi': 'Maori',
            'sw': 'Swahili', 'yo': 'Yoruba', 'ig': 'Igbo', 'ha': 'Hausa',
            'zu': 'Zulu', 'xh': 'Xhosa', 'af': 'Afrikaans', 'am': 'Amharic',
            'ti': 'Tigrinya', 'so': 'Somali', 'om': 'Oromo', 'rw': 'Kinyarwanda',
            'lg': 'Ganda', 'ak': 'Akan', 'tw': 'Twi', 'ee': 'Ewe', 'fon': 'Fon',
            'sn': 'Shona', 'ny': 'Chichewa', 'st': 'Southern Sotho', 'tn': 'Tswana',
            'ts': 'Tsonga', 've': 'Venda', 'ss': 'Swati', 'nr': 'Southern Ndebele',
            'nd': 'Northern Ndebele', 'auto': 'Auto-detect'
        }
        return language_names.get(obj.source_language, obj.source_language)
    
    def get_target_language_name(self, obj):
        language_names = {
            'en': 'English', 'en-US': 'English (US)', 'en-GB': 'English (UK)',
            'es': 'Spanish', 'fr': 'French', 'de': 'German', 'nl': 'Dutch',
            'ar': 'Arabic', 'zh': 'Chinese (Simplified)', 'zh-TW': 'Chinese (Traditional)',
            'ja': 'Japanese', 'ko': 'Korean', 'pt': 'Portuguese', 'it': 'Italian',
            'ru': 'Russian', 'hi': 'Hindi', 'bn': 'Bengali', 'tr': 'Turkish',
            'pl': 'Polish', 'vi': 'Vietnamese', 'th': 'Thai', 'id': 'Indonesian',
            'ms': 'Malay', 'fa': 'Persian', 'he': 'Hebrew', 'sv': 'Swedish',
            'da': 'Danish', 'no': 'Norwegian', 'fi': 'Finnish', 'cs': 'Czech',
            'sk': 'Slovak', 'hu': 'Hungarian', 'ro': 'Romanian', 'bg': 'Bulgarian',
            'hr': 'Croatian', 'sl': 'Slovenian', 'et': 'Estonian', 'lv': 'Latvian',
            'lt': 'Lithuanian', 'mt': 'Maltese', 'el': 'Greek', 'uk': 'Ukrainian',
            'be': 'Belarusian', 'mk': 'Macedonian', 'sq': 'Albanian', 'bs': 'Bosnian',
            'sr': 'Serbian', 'me': 'Montenegrin', 'ka': 'Georgian', 'hy': 'Armenian',
            'az': 'Azerbaijani', 'kk': 'Kazakh', 'ky': 'Kyrgyz', 'uz': 'Uzbek',
            'tg': 'Tajik', 'mn': 'Mongolian', 'ne': 'Nepali', 'si': 'Sinhala',
            'my': 'Burmese', 'km': 'Khmer', 'lo': 'Lao', 'gl': 'Galician',
            'eu': 'Basque', 'ca': 'Catalan', 'cy': 'Welsh', 'ga': 'Irish',
            'is': 'Icelandic', 'fo': 'Faroese', 'kl': 'Greenlandic', 'sm': 'Samoan',
            'to': 'Tongan', 'fj': 'Fijian', 'haw': 'Hawaiian', 'mi': 'Maori',
            'sw': 'Swahili', 'yo': 'Yoruba', 'ig': 'Igbo', 'ha': 'Hausa',
            'zu': 'Zulu', 'xh': 'Xhosa', 'af': 'Afrikaans', 'am': 'Amharic',
            'ti': 'Tigrinya', 'so': 'Somali', 'om': 'Oromo', 'rw': 'Kinyarwanda',
            'lg': 'Ganda', 'ak': 'Akan', 'tw': 'Twi', 'ee': 'Ewe', 'fon': 'Fon',
            'sn': 'Shona', 'ny': 'Chichewa', 'st': 'Southern Sotho', 'tn': 'Tswana',
            'ts': 'Tsonga', 've': 'Venda', 'ss': 'Swati', 'nr': 'Southern Ndebele',
            'nd': 'Northern Ndebele'
        }
        return language_names.get(obj.target_language, obj.target_language)

class SupportedLanguagesSerializer(serializers.Serializer):
    languages = serializers.DictField()

# Custom Authentication Serializers for Mobile App
class CustomRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('email', 'name', 'password', 'password_confirm', 'gender', 'age', 'location')
        extra_kwargs = {
            'email': {'required': True},
            'name': {'required': True},
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user

class CustomLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(email=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials.')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include email and password.')

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        try:
            User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError('No user found with this email address.')
        return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])
    new_password_confirm = serializers.CharField()
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        
        try:
            uid = force_str(urlsafe_base64_decode(attrs['uid']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError('Invalid token.')
        
        if not default_token_generator.check_token(user, attrs['token']):
            raise serializers.ValidationError('Invalid token.')
        
        attrs['user'] = user
        return attrs

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'name', 'gender', 'age', 'location', 'bio', 'is_matchmaker')
        read_only_fields = ('id', 'email')

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('name', 'gender', 'age', 'location', 'bio', 'is_matchmaker')
    
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class SocialLoginSerializer(serializers.Serializer):
    provider = serializers.CharField()
    access_token = serializers.CharField()
    
    def validate_provider(self, value):
        if value not in ['google', 'apple']:
            raise serializers.ValidationError('Provider must be google or apple.')
        return value

class DeviceRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceRegistration
        fields = ['device_id', 'device_type', 'push_token']
    
    def validate_device_type(self, value):
        if value not in ['ios', 'android']:
            raise serializers.ValidationError('Device type must be ios or android.')
        return value

# OAuth Serializers
class GoogleOAuthSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    id_token = serializers.CharField(required=False)
    
    def validate_access_token(self, value):
        if not value or len(value) < 10:
            raise serializers.ValidationError('Invalid access token format.')
        return value

class AppleOAuthSerializer(serializers.Serializer):
    identity_token = serializers.CharField()
    authorization_code = serializers.CharField(required=False)
    user = serializers.JSONField(required=False)  # Apple user info
    
    def validate_identity_token(self, value):
        if not value or len(value) < 10:
            raise serializers.ValidationError('Invalid identity token format.')
        return value

class OAuthLoginSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=['google', 'apple'])
    google_data = GoogleOAuthSerializer(required=False)
    apple_data = AppleOAuthSerializer(required=False)
    
    def validate(self, attrs):
        provider = attrs.get('provider')
        
        if provider == 'google':
            google_data = attrs.get('google_data')
            if not google_data:
                raise serializers.ValidationError('Google data is required for Google OAuth.')
            if not google_data.get('access_token'):
                raise serializers.ValidationError('Google access token is required.')
        elif provider == 'apple':
            apple_data = attrs.get('apple_data')
            if not apple_data:
                raise serializers.ValidationError('Apple data is required for Apple OAuth.')
            if not apple_data.get('identity_token'):
                raise serializers.ValidationError('Apple identity token is required.')
        
        return attrs

class SocialAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialAccount
        fields = ['id', 'provider', 'provider_user_id', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

class UserProfileWithSocialSerializer(serializers.ModelSerializer):
    social_accounts = SocialAccountSerializer(many=True, read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'gender', 'age', 'location', 'bio', 'is_matchmaker', 'social_accounts']
        read_only_fields = ['id', 'email']

class OAuthLinkSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=['google', 'apple'])
    access_token = serializers.CharField(required=False)
    identity_token = serializers.CharField(required=False)
    
    def validate(self, attrs):
        provider = attrs.get('provider')
        
        if provider == 'google' and not attrs.get('access_token'):
            raise serializers.ValidationError('Access token is required for Google OAuth.')
        elif provider == 'apple' and not attrs.get('identity_token'):
            raise serializers.ValidationError('Identity token is required for Apple OAuth.')
        
        return attrs

# Location Serializers
class LocationUpdateSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=10, decimal_places=8, required=True)
    longitude = serializers.DecimalField(max_digits=11, decimal_places=8, required=True)
    accuracy = serializers.FloatField(required=False, allow_null=True)
    source = serializers.ChoiceField(choices=['gps', 'network', 'manual', 'ip'], default='gps')
    
    def validate_latitude(self, value):
        if not (-90 <= value <= 90):
            raise serializers.ValidationError('Latitude must be between -90 and 90.')
        return value
    
    def validate_longitude(self, value):
        if not (-180 <= value <= 180):
            raise serializers.ValidationError('Longitude must be between -180 and 180.')
        return value

class AddressGeocodeSerializer(serializers.Serializer):
    address = serializers.CharField(max_length=500, required=True)
    
    def validate_address(self, value):
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError('Address must be at least 3 characters long.')
        return value.strip()

class LocationPrivacyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['location_privacy', 'location_sharing_enabled', 'location_update_frequency', 'max_distance']

class LocationPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationPermission
        fields = ['location_enabled', 'background_location_enabled', 'precise_location_enabled', 
                 'location_services_consent', 'location_data_sharing']

class LocationHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationHistory
        fields = ['latitude', 'longitude', 'accuracy', 'address', 'city', 'state', 
                 'country', 'timestamp', 'source']
        read_only_fields = ['timestamp']

class UserMatchSerializer(serializers.ModelSerializer):
    user1_name = serializers.CharField(source='user1.name', read_only=True)
    user1_age = serializers.IntegerField(source='user1.age', read_only=True)
    user1_city = serializers.CharField(source='user1.city', read_only=True)
    user2_name = serializers.CharField(source='user2.name', read_only=True)
    user2_age = serializers.IntegerField(source='user2.age', read_only=True)
    user2_city = serializers.CharField(source='user2.city', read_only=True)
    
    class Meta:
        model = UserMatch
        fields = ['id', 'user1', 'user2', 'user1_name', 'user1_age', 'user1_city',
                 'user2_name', 'user2_age', 'user2_city', 'distance', 'match_score', 
                 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class UserProfileWithLocationSerializer(serializers.ModelSerializer):
    social_accounts = SocialAccountSerializer(many=True, read_only=True)
    location_permissions = LocationPermissionSerializer(read_only=True)
    has_location = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'gender', 'age', 'location', 'latitude', 'longitude',
                 'address', 'city', 'state', 'country', 'postal_code', 'location_privacy',
                 'location_sharing_enabled', 'location_update_frequency', 'max_distance',
                 'age_range_min', 'age_range_max', 'preferred_gender', 'bio', 'is_matchmaker',
                 'social_accounts', 'location_permissions', 'has_location', 'last_location_update']
        read_only_fields = ['id', 'email', 'has_location', 'last_location_update']

class NearbyUserSerializer(serializers.ModelSerializer):
    distance = serializers.FloatField()
    coordinates = serializers.ListField(child=serializers.FloatField())
    
    class Meta:
        model = User
        fields = ['id', 'name', 'age', 'gender', 'city', 'bio', 'distance', 'coordinates']

class MatchPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['max_distance', 'age_range_min', 'age_range_max', 'preferred_gender']
    
    def validate(self, attrs):
        age_min = attrs.get('age_range_min')
        age_max = attrs.get('age_range_max')
        
        if age_min and age_max and age_min > age_max:
            raise serializers.ValidationError('Minimum age cannot be greater than maximum age.')
        
        return attrs


class LivenessVerificationSerializer(serializers.ModelSerializer):
    """Serializer for Liveness Verification records"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    is_expired = serializers.SerializerMethodField()
    can_retry = serializers.SerializerMethodField()
    
    class Meta:
        model = LivenessVerification
        fields = [
            'id', 'user', 'user_email', 'session_id', 'status',
            'actions_required', 'actions_completed',
            'confidence_score', 'face_quality_score',
            'is_live_person', 'spoof_detected', 'spoof_type',
            'verification_method', 'provider',
            'started_at', 'completed_at', 'expires_at',
            'attempts_count', 'max_attempts',
            'is_expired', 'can_retry'
        ]
        read_only_fields = [
            'user', 'started_at', 'completed_at',
            'confidence_score', 'face_quality_score',
            'is_live_person', 'spoof_detected', 'provider'
        ]
    
    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def get_can_retry(self, obj):
        return obj.can_retry()


class UserVerificationStatusSerializer(serializers.ModelSerializer):
    """Serializer for User Verification Status"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    verification_badges = serializers.SerializerMethodField()
    
    class Meta:
        model = UserVerificationStatus
        fields = [
            'id', 'user', 'user_email',
            'email_verified', 'phone_verified', 'liveness_verified', 'identity_verified',
            'verification_level', 'verified_badge', 'trusted_member',
            'email_verified_at', 'phone_verified_at', 'liveness_verified_at',
            'created_at', 'updated_at',
            'verification_badges'
        ]
        read_only_fields = [
            'user', 'verification_level', 'verified_badge',
            'created_at', 'updated_at'
        ]
    
    def get_verification_badges(self, obj):
        """Return user's verification badges for display"""
        badges = []
        if obj.email_verified:
            badges.append({'type': 'email', 'name': 'Email Verified', 'icon': '📧'})
        if obj.phone_verified:
            badges.append({'type': 'phone', 'name': 'Phone Verified', 'icon': '📱'})
        if obj.liveness_verified:
            badges.append({'type': 'liveness', 'name': 'Identity Verified', 'icon': '✅'})
        if obj.identity_verified:
            badges.append({'type': 'full', 'name': 'Fully Verified', 'icon': '🏆'})
        if obj.trusted_member:
            badges.append({'type': 'trusted', 'name': 'Trusted Member', 'icon': '⭐'})
        return badges


# Email and Phone Verification Serializers
class EmailOTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError("Email is required")
        return value.lower()

class EmailOTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=4, min_length=4)
    
    def validate_otp_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP code must contain only digits")
        if len(value) != 4:
            raise serializers.ValidationError("OTP code must be 4 digits")
        return value

class PhoneOTPRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    country_code = serializers.CharField(max_length=5, default='+1')
    user_id = serializers.IntegerField(required=False)
    
    def validate_phone_number(self, value):
        import re
        # Remove all non-digit characters
        cleaned = re.sub(r'\D', '', value)
        if len(cleaned) < 10:
            raise serializers.ValidationError("Phone number must be at least 10 digits")
        return cleaned
    
    def validate_country_code(self, value):
        if not value.startswith('+'):
            value = '+' + value
        return value

class PhoneOTPVerifySerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    country_code = serializers.CharField(max_length=5, default='+1')
    otp_code = serializers.CharField(max_length=4, min_length=4)
    
    def validate_otp_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP code must contain only digits")
        if len(value) != 4:
            raise serializers.ValidationError("OTP code must be 4 digits")
        return value

class UserRoleSelectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRoleSelection
        fields = ['selected_role']
    
    def validate_selected_role(self, value):
        valid_roles = ['looking_for_love', 'bondmaker']
        if value not in valid_roles:
            raise serializers.ValidationError(
                f"Invalid role. Must be one of: {', '.join(valid_roles)}"
            )
        return value

class EmailVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailVerification
        fields = ['id', 'email', 'is_verified', 'created_at', 'expires_at']
        read_only_fields = ['id', 'created_at', 'expires_at']

class PhoneVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhoneVerification
        fields = ['id', 'phone_number', 'country_code', 'is_verified', 'created_at', 'expires_at']
        read_only_fields = ['id', 'created_at', 'expires_at']

class ResendOTPSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['email', 'phone'])
    identifier = serializers.CharField()  # email or phone number
    
    def validate_type(self, value):
        if value not in ['email', 'phone']:
            raise serializers.ValidationError("Type must be 'email' or 'phone'")
        return value


# =============================================================================
# ADVANCED USER PROFILE SERIALIZERS
# =============================================================================

class UserProfileDetailSerializer(serializers.ModelSerializer):
    """Detailed user profile serializer for viewing other users"""
    profile_views_count = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    compatibility_score = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'name', 'age', 'gender', 'bio', 'profile_picture', 'profile_gallery',
            'education_level', 'height', 'zodiac_sign', 'languages', 'relationship_status',
            'smoking_preference', 'drinking_preference', 'pet_preference', 'exercise_frequency',
            'kids_preference', 'personality_type', 'love_language', 'communication_style',
            'hobbies', 'interests', 'marriage_plans', 'kids_plans', 'religion_importance',
            'religion', 'dating_type', 'open_to_long_distance', 'city', 'state', 'country',
            'profile_views_count', 'is_online', 'distance', 'compatibility_score'
        ]
        read_only_fields = ['id', 'profile_views_count', 'is_online', 'distance', 'compatibility_score']
    
    def get_profile_views_count(self, obj):
        return UserProfileView.objects.filter(viewed_user=obj).count()
    
    def get_is_online(self, obj):
        # Simple online status - can be enhanced with last_seen tracking
        return False
    
    def get_distance(self, obj):
        request = self.context.get('request')
        if request and request.user.has_location and obj.has_location:
            return request.user.get_distance_to(obj)
        return None
    
    def get_compatibility_score(self, obj):
        request = self.context.get('request')
        if request and request.user != obj:
            from .location_utils import calculate_match_score
            return calculate_match_score(request.user, obj)
        return None


class UserSearchSerializer(serializers.ModelSerializer):
    """Serializer for user search results"""
    distance = serializers.SerializerMethodField()
    match_score = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'name', 'age', 'gender', 'bio', 'profile_picture', 'city', 'state', 'country',
            'education_level', 'height', 'zodiac_sign', 'relationship_status', 'dating_type',
            'distance', 'match_score'
        ]
    
    def get_distance(self, obj):
        request = self.context.get('request')
        if request and request.user.has_location and obj.has_location:
            return request.user.get_distance_to(obj)
        return None
    
    def get_match_score(self, obj):
        request = self.context.get('request')
        if request and request.user != obj:
            from .location_utils import calculate_match_score
            return calculate_match_score(request.user, obj)
        return None


class UserInterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserInterest
        fields = ['id', 'name', 'category', 'icon']


class UserInteractionSerializer(serializers.ModelSerializer):
    target_user_name = serializers.CharField(source='target_user.name', read_only=True)
    target_user_photo = serializers.URLField(source='target_user.profile_picture', read_only=True)
    
    class Meta:
        model = UserInteraction
        fields = [
            'id', 'target_user', 'target_user_name', 'target_user_photo',
            'interaction_type', 'created_at', 'metadata'
        ]
        read_only_fields = ['id', 'created_at']


class SearchQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchQuery
        fields = ['id', 'query', 'filters', 'results_count', 'created_at']
        read_only_fields = ['id', 'created_at']


class RecommendationSerializer(serializers.ModelSerializer):
    recommended_user = UserSearchSerializer(read_only=True)
    
    class Meta:
        model = RecommendationEngine
        fields = ['id', 'recommended_user', 'score', 'algorithm', 'created_at']
        read_only_fields = ['id', 'created_at']


# =============================================================================
# SEARCH AND FILTER SERIALIZERS
# =============================================================================

class UserSearchFilterSerializer(serializers.Serializer):
    """Serializer for advanced user search filters"""
    query = serializers.CharField(required=False, allow_blank=True)
    gender = serializers.CharField(required=False)
    age_min = serializers.IntegerField(required=False, min_value=18, max_value=100)
    age_max = serializers.IntegerField(required=False, min_value=18, max_value=100)
    max_distance = serializers.IntegerField(required=False, min_value=1, max_value=500)
    education_level = serializers.CharField(required=False)
    relationship_status = serializers.CharField(required=False)
    smoking_preference = serializers.CharField(required=False)
    drinking_preference = serializers.CharField(required=False)
    pet_preference = serializers.CharField(required=False)
    exercise_frequency = serializers.CharField(required=False)
    kids_preference = serializers.CharField(required=False)
    personality_type = serializers.CharField(required=False)
    love_language = serializers.CharField(required=False)
    dating_type = serializers.CharField(required=False)
    religion = serializers.CharField(required=False)
    interests = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    hobbies = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    is_matchmaker = serializers.BooleanField(required=False)
    has_photos = serializers.BooleanField(required=False)
    online_only = serializers.BooleanField(required=False)
    
    def validate(self, attrs):
        age_min = attrs.get('age_min')
        age_max = attrs.get('age_max')
        
        if age_min and age_max and age_min > age_max:
            raise serializers.ValidationError('age_min cannot be greater than age_max')
        
        return attrs


class CategoryFilterSerializer(serializers.Serializer):
    """Serializer for category-based filtering"""
    category = serializers.ChoiceField(choices=[
        ('all', 'All'),
        ('casual_dating', 'Casual Dating'),
        ('lgbtq', 'LGBTQ+'),
        ('sugar', 'Sugar Relationship'),
        ('serious', 'Serious Relationship'),
        ('friends', 'Friends First'),
        ('matchmakers', 'Matchmakers Only')
    ])
    subcategory = serializers.CharField(required=False, allow_blank=True)


# =============================================================================
# CHAT AND MESSAGING SERIALIZERS (NEW)
# =============================================================================

class ChatParticipantSerializer(serializers.ModelSerializer):
    """Serializer for chat participants (simplified user info)"""
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    name = serializers.CharField(source='user.name', read_only=True)
    profile_picture = serializers.URLField(source='user.profile_picture', read_only=True)
    is_online = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatParticipant
        fields = [
            'user_id', 'name', 'profile_picture', 'is_online',
            'joined_at', 'last_seen_at', 'is_active', 'custom_nickname',
            'notifications_enabled', 'is_muted'
        ]
        read_only_fields = ['user_id', 'name', 'profile_picture', 'is_online', 'joined_at', 'last_seen_at']
    
    def get_is_online(self, obj):
        """Check if user is online (placeholder - implement with real-time status)"""
        # This would typically check last activity or WebSocket connection
        return False


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for individual messages"""
    sender_id = serializers.IntegerField(source='sender.id', read_only=True)
    sender_name = serializers.CharField(source='sender.name', read_only=True)
    sender_profile_picture = serializers.URLField(source='sender.profile_picture', read_only=True)
    is_from_current_user = serializers.SerializerMethodField()
    reply_to_message = serializers.SerializerMethodField()
    formatted_timestamp = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'chat', 'sender_id', 'sender_name', 'sender_profile_picture',
            'message_type', 'content', 'voice_note_url', 'voice_note_duration',
            'image_url', 'video_url', 'document_url', 'document_name',
            'tip_amount', 'tip_gift', 'timestamp', 'formatted_timestamp', 'is_read', 'read_at',
            'is_edited', 'edited_at', 'reply_to', 'reply_to_message',
            'reactions', 'is_from_current_user'
        ]
        read_only_fields = [
            'id', 'chat', 'sender_id', 'sender_name', 'sender_profile_picture',
            'timestamp', 'formatted_timestamp', 'is_read', 'read_at',
            'is_edited', 'edited_at', 'reactions', 'is_from_current_user'
        ]
    
    def get_is_from_current_user(self, obj):
        """Check if message is from the current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.sender == request.user
        return False
    
    def get_reply_to_message(self, obj):
        """Get the message being replied to"""
        if obj.reply_to:
            return {
                'id': obj.reply_to.id,
                'content': obj.reply_to.content[:100] + '...' if len(obj.reply_to.content or '') > 100 else obj.reply_to.content,
                'sender_name': obj.reply_to.sender.name if obj.reply_to.sender else 'System',
                'message_type': obj.reply_to.message_type,
                'timestamp': obj.reply_to.timestamp
            }
        return None
    
    def get_formatted_timestamp(self, obj):
        """Get formatted timestamp for display"""
        from django.utils import timezone
        now = timezone.now()
        diff = now - obj.timestamp
        
        if diff.days == 0:
            return obj.timestamp.strftime('%H:%M')
        elif diff.days == 1:
            return 'Yesterday'
        elif diff.days < 7:
            return obj.timestamp.strftime('%A')
        else:
            return obj.timestamp.strftime('%m/%d/%Y')


class ChatSerializer(serializers.ModelSerializer):
    """Serializer for chat list view"""
    participants = ChatParticipantSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()
    
    class Meta:
        model = Chat
        fields = [
            'id', 'chat_type', 'participants', 'other_participant',
            'created_at', 'updated_at', 'last_message_at', 'last_message',
            'unread_count', 'is_active', 'chat_name', 'chat_theme'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'last_message_at',
            'last_message', 'unread_count', 'other_participant'
        ]
    
    def get_last_message(self, obj):
        """Get the last message in the chat"""
        last_msg = obj.messages.order_by('-timestamp').first()
        if last_msg:
            return {
                'id': last_msg.id,
                'content': last_msg.content[:100] + '...' if len(last_msg.content or '') > 100 else last_msg.content,
                'message_type': last_msg.message_type,
                'sender_name': last_msg.sender.name if last_msg.sender else 'System',
                'timestamp': last_msg.timestamp,
                'is_read': last_msg.is_read
            }
        return None
    
    def get_unread_count(self, obj):
        """Get unread message count for current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_unread_count(request.user)
        return 0
    
    def get_other_participant(self, obj):
        """Get the other participant in direct message chats"""
        request = self.context.get('request')
        if request and request.user.is_authenticated and obj.chat_type == 'direct':
            other_user = obj.get_other_participant(request.user)
            if other_user:
                return {
                    'id': other_user.id,
                    'name': other_user.name,
                    'profile_picture': other_user.profile_picture,
                    'is_online': False  # Placeholder
                }
        return None


class ChatDetailSerializer(serializers.ModelSerializer):
    """Serializer for a single chat with all its messages"""
    participants = ChatParticipantSerializer(many=True, read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    other_participant = serializers.SerializerMethodField()
    
    class Meta:
        model = Chat
        fields = [
            'id', 'chat_type', 'participants', 'other_participant',
            'created_at', 'updated_at', 'last_message_at', 'messages',
            'is_active', 'chat_name', 'chat_theme'
        ]
        read_only_fields = [
            'id', 'participants', 'other_participant', 'created_at',
            'updated_at', 'last_message_at', 'messages'
        ]
    
    def get_other_participant(self, obj):
        """Get the other participant in direct message chats"""
        request = self.context.get('request')
        if request and request.user.is_authenticated and obj.chat_type == 'direct':
            other_user = obj.get_other_participant(request.user)
            if other_user:
                return {
                    'id': other_user.id,
                    'name': other_user.name,
                    'profile_picture': other_user.profile_picture,
                    'is_online': False  # Placeholder
                }
        return None


class ChatCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new chats"""
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        help_text="List of user IDs to include in the chat"
    )
    
    class Meta:
        model = Chat
        fields = ['chat_type', 'participant_ids', 'chat_name']
    
    def validate_participant_ids(self, value):
        """Validate participant IDs"""
        if len(value) < 1:
            raise serializers.ValidationError("At least one participant is required")
        
        # Ensure users exist
        existing_users = User.objects.filter(id__in=value).values_list('id', flat=True)
        missing_ids = set(value) - set(existing_users)
        if missing_ids:
            raise serializers.ValidationError(f"Users not found: {list(missing_ids)}")
        
        return value
    
    def create(self, validated_data):
        """Create chat with participants"""
        participant_ids = validated_data.pop('participant_ids')
        chat = Chat.objects.create(**validated_data)
        chat.participants.set(participant_ids)
        return chat


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new messages"""
    
    class Meta:
        model = Message
        fields = [
            'message_type', 'content', 'voice_note_url', 'voice_note_duration',
            'image_url', 'video_url', 'document_url', 'document_name', 'reply_to',
            'tip_amount', 'tip_gift'
        ]
    
    def validate(self, attrs):
        """Validate message content"""
        message_type = attrs.get('message_type', 'text')
        content = attrs.get('content')
        
        # For text messages, content is required
        if message_type == 'text' and not content:
            raise serializers.ValidationError("Content is required for text messages")
        
        # For media messages, at least one media URL is required
        if message_type in ['voice_note', 'image', 'video', 'document']:
            media_fields = ['voice_note_url', 'image_url', 'video_url', 'document_url']
            if not any(attrs.get(field) for field in media_fields):
                raise serializers.ValidationError(f"Media URL is required for {message_type} messages")
        
        # For tip messages, tip_amount is required
        if message_type == 'tip':
            tip_amount = attrs.get('tip_amount')
            if not tip_amount or tip_amount <= 0:
                raise serializers.ValidationError("Tip amount is required and must be greater than 0")
        
        return attrs


class VoiceNoteSerializer(serializers.ModelSerializer):
    """Serializer for voice notes"""
    message_id = serializers.IntegerField(source='message.id', read_only=True)
    
    class Meta:
        model = VoiceNote
        fields = [
            'id', 'message_id', 'audio_url', 'duration', 'file_size',
            'transcription', 'transcription_confidence', 'created_at'
        ]
        read_only_fields = ['id', 'message_id', 'created_at']


class CallSerializer(serializers.ModelSerializer):
    """Serializer for voice/video calls"""
    caller_name = serializers.CharField(source='caller.name', read_only=True)
    caller_profile_picture = serializers.URLField(source='caller.profile_picture', read_only=True)
    callee_name = serializers.CharField(source='callee.name', read_only=True)
    callee_profile_picture = serializers.URLField(source='callee.profile_picture', read_only=True)
    duration_display = serializers.CharField(source='get_duration_display', read_only=True)
    
    class Meta:
        model = Call
        fields = [
            'id', 'chat', 'caller', 'caller_name', 'caller_profile_picture',
            'callee', 'callee_name', 'callee_profile_picture',
            'call_type', 'status', 'started_at', 'answered_at', 'ended_at',
            'duration', 'duration_display', 'call_id', 'room_id',
            'quality_score', 'is_recorded', 'recording_url'
        ]
        read_only_fields = [
            'id', 'chat', 'caller', 'caller_name', 'caller_profile_picture',
            'callee', 'callee_name', 'callee_profile_picture',
            'started_at', 'answered_at', 'ended_at', 'duration',
            'duration_display', 'quality_score'
        ]


class CallInitiateSerializer(serializers.Serializer):
    """Serializer for initiating calls"""
    callee_id = serializers.IntegerField()
    call_type = serializers.ChoiceField(choices=[('voice', 'Voice Call'), ('video', 'Video Call')])
    
    def validate_callee_id(self, value):
        """Validate callee exists"""
        if not User.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("User not found or inactive")
        return value


class ChatReportSerializer(serializers.ModelSerializer):
    """Serializer for chat reports"""
    reporter_name = serializers.CharField(source='reporter.name', read_only=True)
    reported_user_name = serializers.CharField(source='reported_user.name', read_only=True)
    
    class Meta:
        model = ChatReport
        fields = [
            'id', 'reporter', 'reporter_name', 'reported_user', 'reported_user_name',
            'chat', 'message', 'report_type', 'description', 'status',
            'moderator_notes', 'action_taken', 'resolved_by', 'resolved_at',
            'created_at'
        ]
        read_only_fields = [
            'id', 'reporter', 'reporter_name', 'reported_user_name',
            'status', 'moderator_notes', 'action_taken', 'resolved_by',
            'resolved_at', 'created_at'
        ]
    
    def create(self, validated_data):
        """Create report with current user as reporter"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['reporter'] = request.user
        return super().create(validated_data)


class ChatSettingsSerializer(serializers.ModelSerializer):
    """Serializer for chat settings"""
    
    class Meta:
        model = Chat
        fields = ['chat_name', 'chat_theme']
    
    def update(self, instance, validated_data):
        """Update chat settings"""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


# =============================================================================
# SOCIAL FEED AND STORY SERIALIZERS (NEW)
# =============================================================================

class PostCommentSerializer(serializers.ModelSerializer):
    """Serializer for post comments"""
    author_id = serializers.IntegerField(source='author.id', read_only=True)
    author_name = serializers.CharField(source='author.name', read_only=True)
    author_profile_picture = serializers.URLField(source='author.profile_picture', read_only=True)
    author_location = serializers.CharField(source='author.location', read_only=True)
    is_from_current_user = serializers.SerializerMethodField()
    formatted_timestamp = serializers.SerializerMethodField()
    
    class Meta:
        model = PostComment
        fields = [
            'id', 'post', 'author_id', 'author_name', 'author_profile_picture', 'author_location',
            'content', 'parent_comment', 'likes_count', 'replies_count', 'is_active', 'is_edited',
            'created_at', 'updated_at', 'formatted_timestamp', 'is_from_current_user'
        ]
        read_only_fields = [
            'id', 'author_id', 'author_name', 'author_profile_picture', 'author_location',
            'likes_count', 'replies_count', 'is_active', 'is_edited', 'created_at', 'updated_at',
            'formatted_timestamp', 'is_from_current_user'
        ]
    
    def get_is_from_current_user(self, obj):
        """Check if comment is from the current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.author == request.user
        return False
    
    def get_formatted_timestamp(self, obj):
        """Get formatted timestamp for display"""
        from django.utils import timezone
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.days == 0:
            return obj.created_at.strftime('%H:%M')
        elif diff.days == 1:
            return 'Yesterday'
        elif diff.days < 7:
            return obj.created_at.strftime('%A')
        else:
            return obj.created_at.strftime('%m/%d/%Y')


class PostSerializer(serializers.ModelSerializer):
    """Serializer for posts in the Bond Story feed"""
    author_id = serializers.IntegerField(source='author.id', read_only=True)
    author_name = serializers.CharField(source='author.name', read_only=True)
    author_profile_picture = serializers.URLField(source='author.profile_picture', read_only=True)
    author_location = serializers.CharField(source='author.location', read_only=True)
    is_from_current_user = serializers.SerializerMethodField()
    formatted_timestamp = serializers.SerializerMethodField()
    engagement_score = serializers.IntegerField(source='get_engagement_score', read_only=True)
    comments = PostCommentSerializer(many=True, read_only=True)
    user_interactions = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'author_id', 'author_name', 'author_profile_picture', 'author_location',
            'post_type', 'content', 'image_urls', 'video_url', 'video_thumbnail',
            'visibility', 'location', 'hashtags', 'mentions', 'likes_count', 'comments_count',
            'shares_count', 'bonds_count', 'engagement_score', 'is_active', 'is_featured',
            'created_at', 'updated_at', 'formatted_timestamp', 'is_from_current_user',
            'comments', 'user_interactions'
        ]
        read_only_fields = [
            'id', 'author_id', 'author_name', 'author_profile_picture', 'author_location',
            'likes_count', 'comments_count', 'shares_count', 'bonds_count', 'engagement_score',
            'is_active', 'is_featured', 'created_at', 'updated_at', 'formatted_timestamp',
            'is_from_current_user', 'comments', 'user_interactions'
        ]
    
    def get_is_from_current_user(self, obj):
        """Check if post is from the current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.author == request.user
        return False
    
    def get_formatted_timestamp(self, obj):
        """Get formatted timestamp for display"""
        from django.utils import timezone
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.days == 0:
            if diff.seconds < 3600:  # Less than 1 hour
                minutes = diff.seconds // 60
                return f"{minutes}m" if minutes > 0 else "now"
            else:
                return obj.created_at.strftime('%H:%M')
        elif diff.days == 1:
            return 'Yesterday'
        elif diff.days < 7:
            return obj.created_at.strftime('%A')
        else:
            return obj.created_at.strftime('%m/%d/%Y')
    
    def get_user_interactions(self, obj):
        """Get current user's interactions with this post"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            interactions = obj.interactions.filter(user=request.user).values_list('interaction_type', flat=True)
            return list(interactions)
        return []


class PostCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new posts"""
    
    class Meta:
        model = Post
        fields = [
            'post_type', 'content', 'image_urls', 'video_url', 'video_thumbnail',
            'visibility', 'location', 'hashtags', 'mentions'
        ]
    
    def validate_content(self, value):
        """Validate post content"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Post content cannot be empty")
        if len(value) > 2000:
            raise serializers.ValidationError("Post content cannot exceed 2000 characters")
        return value
    
    def validate_image_urls(self, value):
        """Validate image URLs"""
        if value and len(value) > 10:
            raise serializers.ValidationError("Cannot attach more than 10 images")
        return value
    
    def create(self, validated_data):
        """Create post with current user as author"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['author'] = request.user
        return super().create(validated_data)


class StorySerializer(serializers.ModelSerializer):
    """Serializer for user stories"""
    author_id = serializers.IntegerField(source='author.id', read_only=True)
    author_name = serializers.CharField(source='author.name', read_only=True)
    author_profile_picture = serializers.URLField(source='author.profile_picture', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    user_has_viewed = serializers.SerializerMethodField()
    user_reaction = serializers.SerializerMethodField()
    
    class Meta:
        model = Story
        fields = [
            'id', 'author_id', 'author_name', 'author_profile_picture', 'story_type',
            'content', 'image_url', 'video_url', 'video_duration', 'background_color',
            'text_color', 'font_size', 'views_count', 'reactions_count', 'is_active',
            'expires_at', 'created_at', 'is_expired', 'user_has_viewed', 'user_reaction'
        ]
        read_only_fields = [
            'id', 'author_id', 'author_name', 'author_profile_picture', 'views_count',
            'reactions_count', 'is_active', 'expires_at', 'created_at', 'is_expired',
            'user_has_viewed', 'user_reaction'
        ]
    
    def get_user_has_viewed(self, obj):
        """Check if current user has viewed this story"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.views.filter(viewer=request.user).exists()
        return False
    
    def get_user_reaction(self, obj):
        """Get current user's reaction to this story"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            reaction = obj.reactions.filter(user=request.user).first()
            return reaction.reaction_type if reaction else None
        return None


class StoryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new stories"""
    
    class Meta:
        model = Story
        fields = [
            'story_type', 'content', 'image_url', 'video_url', 'video_duration',
            'background_color', 'text_color', 'font_size'
        ]
    
    def validate(self, attrs):
        """Validate story content"""
        story_type = attrs.get('story_type')
        content = attrs.get('content')
        image_url = attrs.get('image_url')
        video_url = attrs.get('video_url')
        
        # For text stories, content is required
        if story_type == 'text' and not content:
            raise serializers.ValidationError("Content is required for text stories")
        
        # For image stories, image_url is required
        if story_type == 'image' and not image_url:
            raise serializers.ValidationError("Image URL is required for image stories")
        
        # For video stories, video_url is required
        if story_type == 'video' and not video_url:
            raise serializers.ValidationError("Video URL is required for video stories")
        
        return attrs
    
    def create(self, validated_data):
        """Create story with current user as author and set expiration"""
        from django.utils import timezone
        from datetime import timedelta
        
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['author'] = request.user
        
        # Set expiration to 24 hours from now
        validated_data['expires_at'] = timezone.now() + timedelta(hours=24)
        
        return super().create(validated_data)


class PostInteractionSerializer(serializers.ModelSerializer):
    """Serializer for post interactions"""
    
    class Meta:
        model = PostInteraction
        fields = ['interaction_type']
    
    def create(self, validated_data):
        """Create interaction with current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


class CommentInteractionSerializer(serializers.ModelSerializer):
    """Serializer for comment interactions"""
    
    class Meta:
        model = CommentInteraction
        fields = ['interaction_type']
    
    def create(self, validated_data):
        """Create interaction with current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


class PostReportSerializer(serializers.ModelSerializer):
    """Serializer for post/comment reports"""
    reporter_name = serializers.CharField(source='reporter.name', read_only=True)
    reported_user_name = serializers.CharField(source='reported_user.name', read_only=True)
    
    class Meta:
        model = PostReport
        fields = [
            'id', 'reporter', 'reporter_name', 'reported_user', 'reported_user_name',
            'post', 'comment', 'report_type', 'description', 'status',
            'moderator_notes', 'action_taken', 'resolved_by', 'resolved_at',
            'created_at'
        ]
        read_only_fields = [
            'id', 'reporter', 'reporter_name', 'reported_user_name',
            'status', 'moderator_notes', 'action_taken', 'resolved_by',
            'resolved_at', 'created_at'
        ]
    
    def create(self, validated_data):
        """Create report with current user as reporter"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['reporter'] = request.user
        return super().create(validated_data)


class PostShareSerializer(serializers.ModelSerializer):
    """Serializer for post shares"""
    
    class Meta:
        model = PostShare
        fields = ['platform']
    
    def create(self, validated_data):
        """Create share with current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


class FeedSearchSerializer(serializers.ModelSerializer):
    """Serializer for feed search queries"""
    
    class Meta:
        model = FeedSearch
        fields = ['query', 'filters_applied']
    
    def create(self, validated_data):
        """Create search with current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


# =============================================================================
# SUBSCRIPTION PLANS SERIALIZERS (NEW FROM FIGMA)
# =============================================================================

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for subscription plans"""
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'display_name', 'description', 'duration', 
            'price_bondcoins', 'price_usd', 'unlimited_swipes', 'undo_swipes',
            'unlimited_unwind', 'global_access', 'read_receipt', 'live_hours_days',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for user subscriptions"""
    plan_name = serializers.CharField(source='plan.display_name', read_only=True)
    plan_details = SubscriptionPlanSerializer(source='plan', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = UserSubscription
        fields = [
            'id', 'plan', 'plan_name', 'plan_details', 'status', 'start_date', 
            'end_date', 'payment_method', 'transaction_id', 'auto_renew',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'start_date', 'created_at', 'updated_at']


class UserSubscriptionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating user subscriptions"""
    
    class Meta:
        model = UserSubscription
        fields = ['plan', 'payment_method', 'auto_renew']
    
    def create(self, validated_data):
        """Create subscription with current user and set end date"""
        from django.utils import timezone
        from datetime import timedelta
        
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        
        plan = validated_data['plan']
        
        # Calculate end date based on plan duration
        duration_map = {
            '1_week': timedelta(weeks=1),
            '1_month': timedelta(days=30),
            '3_months': timedelta(days=90),
            '6_months': timedelta(days=180),
            '1_year': timedelta(days=365),
        }
        
        duration = duration_map.get(plan.duration, timedelta(days=30))
        validated_data['end_date'] = timezone.now() + duration
        
        return super().create(validated_data)


# =============================================================================
# BONDCOIN WALLET SERIALIZERS (NEW FROM FIGMA)
# =============================================================================

class BondcoinPackageSerializer(serializers.ModelSerializer):
    """Serializer for Bondcoin packages"""
    
    class Meta:
        model = BondcoinPackage
        fields = [
            'id', 'name', 'bondcoin_amount', 'price_usd', 'is_popular', 
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BondcoinTransactionSerializer(serializers.ModelSerializer):
    """Serializer for Bondcoin transactions"""
    user_name = serializers.CharField(source='user.name', read_only=True)
    package_name = serializers.CharField(source='package.name', read_only=True)
    
    class Meta:
        model = BondcoinTransaction
        fields = [
            'id', 'user', 'user_name', 'transaction_type', 'amount', 'status',
            'package', 'package_name', 'subscription', 'gift', 'payment_method',
            'payment_reference', 'description', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'user_name', 'created_at', 'updated_at']


class BondcoinTransactionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Bondcoin transactions"""
    
    class Meta:
        model = BondcoinTransaction
        fields = [
            'transaction_type', 'amount', 'package', 'subscription', 'gift',
            'payment_method', 'payment_reference', 'description'
        ]
    
    def create(self, validated_data):
        """Create transaction with current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


# =============================================================================
# VIRTUAL GIFTING SERIALIZERS (NEW FROM FIGMA)
# =============================================================================

class GiftCategorySerializer(serializers.ModelSerializer):
    """Serializer for gift categories"""
    
    class Meta:
        model = GiftCategory
        fields = [
            'id', 'name', 'display_name', 'description', 'icon_url', 
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class VirtualGiftSerializer(serializers.ModelSerializer):
    """Serializer for virtual gifts"""
    category_name = serializers.CharField(source='category.display_name', read_only=True)
    
    class Meta:
        model = VirtualGift
        fields = [
            'id', 'name', 'category', 'category_name', 'description', 'icon_url',
            'cost_bondcoins', 'is_popular', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class GiftTransactionSerializer(serializers.ModelSerializer):
    """Serializer for gift transactions"""
    sender_name = serializers.CharField(source='sender.name', read_only=True)
    recipient_name = serializers.CharField(source='recipient.name', read_only=True)
    gift_name = serializers.CharField(source='gift.name', read_only=True)
    gift_icon = serializers.URLField(source='gift.icon_url', read_only=True)
    
    class Meta:
        model = GiftTransaction
        fields = [
            'id', 'sender', 'sender_name', 'recipient', 'recipient_name',
            'gift', 'gift_name', 'gift_icon', 'quantity', 'total_cost',
            'context_type', 'context_id', 'status', 'message', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'sender', 'sender_name', 'recipient_name', 'gift_name', 
            'gift_icon', 'total_cost', 'created_at', 'updated_at'
        ]


class GiftTransactionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating gift transactions"""
    
    class Meta:
        model = GiftTransaction
        fields = [
            'recipient', 'gift', 'quantity', 'context_type', 'context_id', 'message'
        ]
    
    def create(self, validated_data):
        """Create gift transaction with current user as sender"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['sender'] = request.user
        
        # Calculate total cost
        gift = validated_data['gift']
        quantity = validated_data.get('quantity', 1)
        validated_data['total_cost'] = gift.cost_bondcoins * quantity
        
        # Create Bondcoin transaction for the gift
        bondcoin_transaction = BondcoinTransaction.objects.create(
            user=validated_data['sender'],
            transaction_type='gift_sent',
            amount=-validated_data['total_cost'],
            gift=gift,
            description=f"Gift sent: {gift.name}",
            status='completed'
        )
        validated_data['bondcoin_transaction'] = bondcoin_transaction
        
        return super().create(validated_data)


# =============================================================================
# LIVE STREAMING ENHANCEMENT SERIALIZERS (NEW FROM FIGMA)
# =============================================================================

class LiveGiftSerializer(serializers.ModelSerializer):
    """Serializer for live session gifts"""
    sender_name = serializers.CharField(source='sender.name', read_only=True)
    gift_name = serializers.CharField(source='gift.name', read_only=True)
    gift_icon = serializers.URLField(source='gift.icon_url', read_only=True)
    
    class Meta:
        model = LiveGift
        fields = [
            'id', 'session', 'sender', 'sender_name', 'gift', 'gift_name', 
            'gift_icon', 'quantity', 'total_cost', 'chat_message', 'created_at'
        ]
        read_only_fields = ['id', 'sender', 'sender_name', 'gift_name', 'gift_icon', 'created_at']


class LiveGiftCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating live session gifts"""
    
    class Meta:
        model = LiveGift
        fields = ['session', 'gift', 'quantity']
    
    def create(self, validated_data):
        """Create live gift with current user as sender"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['sender'] = request.user
        
        # Calculate total cost
        gift = validated_data['gift']
        quantity = validated_data.get('quantity', 1)
        validated_data['total_cost'] = gift.cost_bondcoins * quantity
        
        # Create chat message
        validated_data['chat_message'] = f"{request.user.name} sent {gift.name}"
        
        # Create Bondcoin transaction
        bondcoin_transaction = BondcoinTransaction.objects.create(
            user=validated_data['sender'],
            transaction_type='gift_sent',
            amount=-validated_data['total_cost'],
            gift=gift,
            description=f"Live gift sent: {gift.name}",
            status='completed'
        )
        validated_data['bondcoin_transaction'] = bondcoin_transaction
        
        return super().create(validated_data)


class LiveJoinRequestSerializer(serializers.ModelSerializer):
    """Serializer for live session join requests"""
    requester_name = serializers.CharField(source='requester.name', read_only=True)
    requester_profile_picture = serializers.URLField(source='requester.profile_picture', read_only=True)
    session_title = serializers.CharField(source='session.title', read_only=True)
    host_name = serializers.CharField(source='session.user.name', read_only=True)
    
    class Meta:
        model = LiveJoinRequest
        fields = [
            'id', 'session', 'session_title', 'host_name', 'requester', 'requester_name',
            'requester_profile_picture', 'requested_role', 'status', 'message',
            'responded_by', 'response_message', 'responded_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'requester', 'requester_name', 'requester_profile_picture',
            'session_title', 'host_name', 'responded_by', 'responded_at', 'created_at', 'updated_at'
        ]


class LiveJoinRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating live session join requests"""
    
    class Meta:
        model = LiveJoinRequest
        fields = ['session', 'requested_role', 'message']
    
    def create(self, validated_data):
        """Create join request with current user as requester"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['requester'] = request.user
        return super().create(validated_data)


class LiveJoinRequestManageSerializer(serializers.ModelSerializer):
    """Serializer for managing live session join requests (host response)"""
    
    class Meta:
        model = LiveJoinRequest
        fields = ['status', 'response_message']
    
    def update(self, instance, validated_data):
        """Update join request with response from host"""
        from django.utils import timezone
        
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['responded_by'] = request.user
            validated_data['responded_at'] = timezone.now()
        
        return super().update(instance, validated_data)


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for payment methods"""
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'name', 'display_name', 'description', 'icon_url',
            'is_active', 'processing_fee_percentage', 'min_amount', 'max_amount',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PaymentTransactionSerializer(serializers.ModelSerializer):
    """Serializer for payment transactions"""
    payment_method_display = serializers.CharField(source='payment_method.display_name', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    
    class Meta:
        model = PaymentTransaction
        fields = [
            'id', 'user', 'user_name', 'transaction_type', 'payment_method', 'payment_method_display',
            'amount_usd', 'processing_fee', 'total_amount', 'currency', 'status',
            'provider', 'provider_transaction_id', 'subscription', 'bondcoin_transaction',
            'description', 'metadata', 'created_at', 'updated_at', 'processed_at'
        ]
        read_only_fields = [
            'id', 'user', 'user_name', 'payment_method_display', 'provider_transaction_id',
            'created_at', 'updated_at', 'processed_at'
        ]


class PaymentTransactionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating payment transactions"""
    
    class Meta:
        model = PaymentTransaction
        fields = [
            'transaction_type', 'payment_method', 'amount_usd', 'currency',
            'subscription', 'bondcoin_transaction', 'description', 'metadata'
        ]
    
    def validate(self, attrs):
        """Validate payment transaction"""
        payment_method = attrs.get('payment_method')
        amount_usd = attrs.get('amount_usd')
        
        if payment_method and amount_usd:
            # Check amount limits
            if amount_usd < payment_method.min_amount:
                raise serializers.ValidationError(f"Amount must be at least ${payment_method.min_amount}")
            
            if amount_usd > payment_method.max_amount:
                raise serializers.ValidationError(f"Amount cannot exceed ${payment_method.max_amount}")
            
            # Calculate processing fee and total
            processing_fee = amount_usd * (payment_method.processing_fee_percentage / 100)
            attrs['processing_fee'] = processing_fee
            attrs['total_amount'] = amount_usd + processing_fee
        
        return attrs


class PaymentWebhookSerializer(serializers.ModelSerializer):
    """Serializer for payment webhooks"""
    transaction_details = PaymentTransactionSerializer(source='transaction', read_only=True)
    
    class Meta:
        model = PaymentWebhook
        fields = [
            'id', 'provider', 'event_type', 'event_id', 'transaction', 'transaction_details',
            'payload', 'processed', 'processing_error', 'created_at', 'processed_at'
        ]
        read_only_fields = ['id', 'created_at', 'processed_at']


class PaymentWebhookCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating payment webhooks"""
    
    class Meta:
        model = PaymentWebhook
        fields = ['provider', 'event_type', 'event_id', 'transaction', 'payload']