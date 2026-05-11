from rest_framework import serializers


class GetPuzzleRequestSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()


class GetPuzzleResponseSerializer(serializers.Serializer):
    puzzle_id = serializers.IntegerField()
    question = serializers.CharField()


class SubmitPuzzleAnswerRequestSerializer(serializers.Serializer):
    puzzle_id = serializers.IntegerField()
    user_answer = serializers.CharField()


class SubmitPuzzleAnswerResponseSerializer(serializers.Serializer):
    correct = serializers.BooleanField()
    message = serializers.CharField()


class EarnCoinsRequestSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    amount = serializers.IntegerField(min_value=1)


class SpendCoinsRequestSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    amount = serializers.IntegerField(min_value=1)
