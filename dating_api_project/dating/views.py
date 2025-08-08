from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum
from rest_framework import status
from rest_framework import generics
from .models import NewsletterSubscriber, PuzzleVerification, CoinTransaction, Waitlist, EmailLog, Job
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from .serializers import (
    UserSerializer, 
    NewsletterSubscriberSerializer, 
    PuzzleVerificationSerializer, 
    CoinTransactionSerializer,
    WaitlistSerializer,
    NewsletterWelcomeEmailSerializer,
    WaitlistConfirmationEmailSerializer,
    GenericEmailSerializer,
    JobListSerializer,
    JobDetailSerializer
)

User = get_user_model()


class UserCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class NewsletterSignupView(generics.CreateAPIView):
    queryset = NewsletterSubscriber.objects.all()
    serializer_class = NewsletterSubscriberSerializer

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                # Check if email already exists
                email = serializer.validated_data.get('email')
                if NewsletterSubscriber.objects.filter(email=email).exists():
                    return Response({
                        "message": "Email already subscribed to newsletter",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Save the newsletter subscription
                subscriber = serializer.save()
                
                # Return success response
                return Response({
                    "message": "Subscription successful!",
                    "status": "success"
                }, status=status.HTTP_201_CREATED)
            
            return Response({
                "message": "Invalid data provided",
                "status": "error",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                "message": f"Server error: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class JoinWaitlistView(generics.CreateAPIView):
    queryset = Waitlist.objects.all()
    serializer_class = WaitlistSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Check if email already exists
            email = serializer.validated_data.get('email')
            if Waitlist.objects.filter(email=email).exists():
                return Response({
                    "message": "Email already registered on waitlist",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Save the waitlist entry
            waitlist_entry = serializer.save()
            
            # Return success response
            return Response({
                "message": "You've successfully joined the waitlist!",
                "status": "success"
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            "message": "Invalid data provided",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


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


class SendNewsletterWelcomeEmailView(APIView):
    def post(self, request):
        serializer = NewsletterWelcomeEmailSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            name = serializer.validated_data.get('name', '')
            
            # Create personalized message
            subject = f"Welcome to Bondah Dating{f', {name}' if name else ''}! 🎉"
            message = f"""
Hi {name if name else 'there'},

Thank you for subscribing to our newsletter! 

We're excited to keep you updated on:
• Latest dating tips and advice
• Success stories from our community
• New features and updates
• Exclusive matchmaking opportunities

Stay tuned for amazing content coming your way!

Best regards,
The Bondah Team
            """.strip()
            
            # Log email attempt
            email_log = EmailLog.objects.create(
                email_type='newsletter_welcome',
                recipient_email=email,
                subject=subject,
                message=message
            )
            
            try:
                # Send email using Django's email functionality
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                
                email_log.is_sent = True
                email_log.save()
                
                return Response({
                    "message": "Welcome email sent successfully!",
                    "status": "success"
                }, status=status.HTTP_200_OK)
            except Exception as e:
                email_log.is_sent = False
                email_log.error_message = str(e)
                email_log.save()
                
                return Response({
                    "message": f"Failed to send email: {str(e)}",
                    "status": "error"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            "message": "Invalid data provided",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class SendWaitlistConfirmationEmailView(APIView):
    def post(self, request):
        serializer = WaitlistConfirmationEmailSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            first_name = serializer.validated_data['firstName']
            last_name = serializer.validated_data['lastName']
            
            # Create personalized message
            subject = f"You're on the Bondah Waitlist, {first_name}! ⏳"
            message = f"""
Hi {first_name} {last_name},

Great news! You've successfully joined the Bondah Dating waitlist.

Your spot is reserved, and we'll notify you as soon as:
• Our platform launches
• Early access becomes available
• Special features are ready

We'll keep you updated on our progress and send you exclusive early-bird offers!

Thanks for your patience,
The Bondah Team

P.S. Share this with friends who might be interested in joining too!
            """.strip()
            
            # Log email attempt
            email_log = EmailLog.objects.create(
                email_type='waitlist_confirmation',
                recipient_email=email,
                subject=subject,
                message=message
            )
            
            try:
                # Send email using Django's email functionality
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                
                email_log.is_sent = True
                email_log.save()
                
                return Response({
                    "message": "Waitlist confirmation email sent!",
                    "status": "success"
                }, status=status.HTTP_200_OK)
            except Exception as e:
                email_log.is_sent = False
                email_log.error_message = str(e)
                email_log.save()
                
                return Response({
                    "message": f"Failed to send email: {str(e)}",
                    "status": "error"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            "message": "Invalid data provided",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class SendGenericEmailView(APIView):
    def post(self, request):
        serializer = GenericEmailSerializer(data=request.data)
        if serializer.is_valid():
            to_email = serializer.validated_data['to_email']
            subject = serializer.validated_data['subject']
            message = serializer.validated_data['message']
            
            # Log email attempt
            email_log = EmailLog.objects.create(
                email_type='generic',
                recipient_email=to_email,
                subject=subject,
                message=message
            )
            
            try:
                # Send email using Django's email functionality
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[to_email],
                    fail_silently=False,
                )
                
                email_log.is_sent = True
                email_log.save()
                
                return Response({
                    "message": "Email sent successfully!",
                    "status": "success"
                }, status=status.HTTP_200_OK)
            except Exception as e:
                email_log.is_sent = False
                email_log.error_message = str(e)
                email_log.save()
                
                return Response({
                    "message": f"Failed to send email: {str(e)}",
                    "status": "error"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            "message": "Invalid data provided",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class JobListView(generics.ListAPIView):
    serializer_class = JobListSerializer
    
    def get_queryset(self):
        queryset = Job.objects.filter(status='open')  # Only show open jobs by default
        
        # Apply filters
        job_type = self.request.query_params.get('jobType', None)
        category = self.request.query_params.get('category', None)
        status = self.request.query_params.get('status', None)
        
        if job_type:
            queryset = queryset.filter(job_type=job_type)
        if category:
            queryset = queryset.filter(category=category)
        if status:
            queryset = queryset.filter(status=status)
            
        return queryset


class JobDetailView(generics.RetrieveAPIView):
    queryset = Job.objects.all()
    serializer_class = JobDetailSerializer
    lookup_field = 'id'