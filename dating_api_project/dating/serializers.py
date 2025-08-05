from rest_framework import serializers
from .models import User, NewsletterSubscriber, PuzzleVerification, CoinTransaction, Waitlist

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