from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum
from rest_framework import status
from rest_framework import generics
from .models import NewsletterSubscriber, PuzzleVerification, CoinTransaction
from django.contrib.auth import get_user_model
from .serializers import (
    UserSerializer, 
    NewsletterSubscriberSerializer, 
    PuzzleVerificationSerializer, 
    CoinTransactionSerializer,
)

User = get_user_model()


class UserCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class NewsletterSignupView(generics.CreateAPIView):
    queryset = NewsletterSubscriber.objects.all()
    serializer_class = NewsletterSubscriberSerializer

class GetPuzzleView(APIView):
    def post(self, request):
        user_id = request.data.get("user_id")
        if user_id is None:
            return Response({"error": "user_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return Response({"error": "user_id must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": f"User with id {user_id} not found."}, status=status.HTTP_404_NOT_FOUND)

        question, answer = PuzzleVerification.generate_puzzle()
        puzzle = PuzzleVerification.objects.create(user=user, question=question, answer=answer)

        return Response({
            "puzzle_id": puzzle.id,
            "question": puzzle.question
        }, status=status.HTTP_201_CREATED)


class SubmitPuzzleAnswerView(APIView):
    def post(self, request):
        puzzle_id = request.data.get("puzzle_id")
        user_answer = request.data.get("user_answer")

        if not puzzle_id or not user_answer:
            return Response(
                {"error": "puzzle_id and user_answer are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            puzzle = PuzzleVerification.objects.get(id=puzzle_id)
        except PuzzleVerification.DoesNotExist:
            return Response({"error": "Puzzle not found"}, status=status.HTTP_404_NOT_FOUND)

        is_correct = puzzle.answer.strip().lower() == user_answer.strip().lower()
        puzzle.user_answer = user_answer
        puzzle.is_correct = is_correct
        puzzle.save()

        return Response({
            "correct": is_correct,
            "message": "Correct!" if is_correct else "Incorrect, try again."
        }, status=status.HTTP_200_OK)
    

def has_solved_puzzle(user):
    latest_puzzle = PuzzleVerification.objects.filter(user=user).order_by('-created_at').first()
    return latest_puzzle and latest_puzzle.is_correct


class EarnCoinsView(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        amount = int(request.data.get('amount', 0))

        if not user_id or not amount:
            return Response({"error": "User ID and amount are required."}, status=400)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=404)

        if not has_solved_puzzle(user):
            return Response({"error": "You must solve a puzzle before earning coins."}, status=403)

        transaction = CoinTransaction.objects.create(
            user=user,
            transaction_type='earn',
            amount=amount
        )

        return Response(CoinTransactionSerializer(transaction).data, status=201)


class SpendCoinsView(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        amount = int(request.data.get('amount', 0))

        if not user_id or not amount:
            return Response({"error": "User ID and amount are required."}, status=400)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=404)

        if not has_solved_puzzle(user):
            return Response({"error": "You must solve a puzzle before spending coins."}, status=403)

        total_earned = CoinTransaction.objects.filter(
            user=user, transaction_type='earn'
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        total_spent = CoinTransaction.objects.filter(
            user=user, transaction_type='spend'
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        if amount > (total_earned - total_spent):
            return Response({"error": "Insufficient coin balance."}, status=400)

        transaction = CoinTransaction.objects.create(
            user=user,
            transaction_type='spend',
            amount=amount
        )

        return Response(CoinTransactionSerializer(transaction).data, status=201)