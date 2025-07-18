from rest_framework import serializers
from .models import User, NewsletterSubscriber, PuzzleVerification, CoinTransaction

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'name', 'email', 'gender', 'age', 'location', 'is_matchmaker', 'bio'
        ]

class NewsletterSubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscriber
        fields = ['id', 'email', 'date_subscribed']
        read_only_fields = ['date_subscribed']


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