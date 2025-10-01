from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from .models import User, NewsletterSubscriber, PuzzleVerification, CoinTransaction, Waitlist, Job, JobApplication, AdminUser, AdminOTP, TranslationLog, SocialAccount, DeviceRegistration, LocationHistory, UserMatch, LocationPermission

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