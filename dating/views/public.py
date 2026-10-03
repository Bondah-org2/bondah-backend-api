import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from django.utils import timezone
from ..models import NewsletterSubscriber, PuzzleVerification, Waitlist, EmailLog
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from ..serializers import NewsletterSubscriberSerializer, WaitlistSerializer, NewsletterWelcomeEmailSerializer, WaitlistConfirmationEmailSerializer, GenericEmailSerializer
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema
from dating.openapi.response_serializers import ErrorWithDetailsSerializer
from dating.openapi.schema_serializers import GetPuzzleRequestSerializer, GetPuzzleResponseSerializer, SubmitPuzzleAnswerRequestSerializer, SubmitPuzzleAnswerResponseSerializer
from rest_framework.generics import GenericAPIView

User = get_user_model()
logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Newsletter"],
)
class NewsletterSignupView(generics.CreateAPIView):
    queryset = NewsletterSubscriber.objects.all()
    serializer_class = NewsletterSubscriberSerializer

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                # Check if email already exists
                email = serializer.validated_data.get("email")
                name = serializer.validated_data.get("name", "")

                if NewsletterSubscriber.objects.filter(email=email).exists():
                    return Response(
                        {
                            "message": "Email already subscribed to newsletter",
                            "status": "error",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Save the newsletter subscription
                subscriber = serializer.save()


                #TODO: Ensure it runs in background
                # Send automatic welcome email
                subject = f"Welcome to Bondah Dating{f', {name}' if name else ''}! 🎉"
                message = f"""
Hi {name if name else 'there'},

Thank you for subscribing to our newsletter!

We're excited to keep you updated on:
• Latest dating tips and advice
• Success stories from our community
• New features and updates
• Exclusive matchmaking opportunities
• Early access to premium features

Stay tuned for amazing content coming your way!

Best regards,
The Bondah Team

P.S. Follow us on social media for daily dating insights!
                """.strip()

                # Log email attempt
                email_log = EmailLog.objects.create(
                    email_type="newsletter_welcome",
                    recipient_email=email,
                    subject=subject,
                    message=message,
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

                except Exception as e:
                    email_log.is_sent = False
                    email_log.error_message = str(e)
                    email_log.save()
                    # Don't fail the signup if email fails

                # Return success response
                return Response(
                    {
                        "message": "Subscription successful! Welcome email sent.",
                        "status": "success",
                    },
                    status=status.HTTP_201_CREATED,
                )

            return Response(
                {
                    "message": "Invalid data provided",
                    "status": "error",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return Response(
                {"message": f"Server error: {str(e)}", "status": "error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    tags=["Waitlist"],
)
class JoinWaitlistView(generics.CreateAPIView):
    """Join the waitlist"""

    serializer_class = WaitlistSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        data = request.data
        logger.info("📋 Received data: %s", data)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        if Waitlist.objects.filter(email=email).exists():
            logger.info("Email already exists: %s", email)
            return Response(
                {
                    "message": "Email already registered on waitlist",
                    "status": "success",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        # Determine timestamp field dynamically
        timestamp_field = (
            "date_joined" if hasattr(Waitlist, "date_joined") else "joined_at"
        )
        waitlist_data = {
            "email": email,
            "first_name": serializer.validated_data.get("first_name", ""),
            "last_name": serializer.validated_data.get("last_name", ""),
            timestamp_field: timezone.now(),
        }

        saved_entry = Waitlist.objects.create(**waitlist_data)
        logger.info("Saved waitlist entry: %s", saved_entry)

        return Response(
            {
                "message": "Successfully joined the waitlist!",
                "status": "success",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class GetPuzzleView(APIView):
   @extend_schema(
    tags=["Puzzle"],
    request=GetPuzzleRequestSerializer,
    responses={ 201: GetPuzzleResponseSerializer, 400: ErrorWithDetailsSerializer, 404: ErrorWithDetailsSerializer, 500: ErrorWithDetailsSerializer, }, )
   
   def post(self, request):
        serializer = GetPuzzleRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data["user_id"]

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"status": "error", "message": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        question, answer = PuzzleVerification.generate_puzzle()

        puzzle = PuzzleVerification.objects.create(
            user=user, question=question, answer=answer
        )

        return Response(
            {"puzzle_id": puzzle.id, "question": puzzle.question},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=["Puzzle"],
    )
class SubmitPuzzleAnswerView(APIView):
    @extend_schema(
        request=SubmitPuzzleAnswerRequestSerializer,
        responses={
            200: SubmitPuzzleAnswerResponseSerializer,
            400: ErrorWithDetailsSerializer,
            404: ErrorWithDetailsSerializer,
            500: ErrorWithDetailsSerializer,
        },
    )
    def post(self, request):
        serializer = SubmitPuzzleAnswerRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        puzzle_id = serializer.validated_data["puzzle_id"]
        user_answer = serializer.validated_data["user_answer"]

        try:
            puzzle = PuzzleVerification.objects.get(id=puzzle_id)
        except PuzzleVerification.DoesNotExist:
            return Response(
                {"status": "error", "message": "Puzzle not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        is_correct = puzzle.answer.strip().lower() == user_answer.strip().lower()

        puzzle.user_answer = user_answer
        puzzle.is_correct = is_correct
        puzzle.save(update_fields=["user_answer", "is_correct"])

        return Response(
            {
                "correct": is_correct,
                "message": "Correct!" if is_correct else "Incorrect, try again.",
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Email"],
    )
class SendGenericEmailView(GenericAPIView):
    serializer_class = GenericEmailSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        EmailLog.objects.create(
            email_type="generic",
            recipient_email=data["to_email"],
            subject=data["subject"],
            message=data["message"],
        )

        send_mail(
            data["subject"],
            data["message"],
            settings.DEFAULT_FROM_EMAIL,
            [data["to_email"]],
        )

        return Response({"message": "Email sent", "status": "success"})


@extend_schema(
    tags=["Newsletter"],
    )
class SendNewsletterWelcomeEmailView(generics.GenericAPIView):
    """
    Send a welcome email to new newsletter subscribers.
    """

    serializer_class = NewsletterWelcomeEmailSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # TODO: MAKE IT RUN IN BACKGROUND
        # Send the welcome email
        send_mail(
            subject="Welcome to Bondah",
            message="Welcome to Bondah Dating!",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[data["email"]],
        )

        return Response(
            {"message": "Welcome email sent", "status": "success"},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Waitlist"],
    )
class SendWaitlistConfirmationEmailView(GenericAPIView):
    serializer_class = WaitlistConfirmationEmailSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # TODO: MAKE IT RUN IN BG
        send_mail(
            "Waitlist confirmation",
            "You are on the waitlist!",
            settings.DEFAULT_FROM_EMAIL,
            [data["email"]],
        )

        return Response({"message": "Waitlist email sent", "status": "success"})
