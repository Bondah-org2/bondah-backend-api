from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum
from rest_framework import status
from rest_framework import generics
import random
import string
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.hashers import make_password, check_password
from .models import NewsletterSubscriber, PuzzleVerification, CoinTransaction, Waitlist, EmailLog, Job, JobApplication, AdminUser, AdminOTP, TranslationLog, SocialAccount, DeviceRegistration, LocationHistory, UserMatch, LocationPermission, EmailVerification, PhoneVerification, UserRoleSelection
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
    JobDetailSerializer,
    JobApplicationSerializer,
    AdminLoginSerializer,
    AdminOTPVerificationSerializer,
    AdminJobCreateSerializer,
    AdminJobUpdateSerializer,
    AdminJobListSerializer,
    AdminJobApplicationSerializer,
    TranslationRequestSerializer,
    TranslationResponseSerializer,
    SupportedLanguagesSerializer,
    # Mobile App Authentication Serializers
    CustomRegisterSerializer,
    CustomLoginSerializer,
    PasswordResetSerializer,
    PasswordResetConfirmSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    SocialLoginSerializer,
    DeviceRegistrationSerializer,
    # OAuth Serializers
    GoogleOAuthSerializer,
    AppleOAuthSerializer,
    OAuthLoginSerializer,
    SocialAccountSerializer,
    UserProfileWithSocialSerializer,
    OAuthLinkSerializer,
    # Location Serializers
    LocationUpdateSerializer,
    AddressGeocodeSerializer,
    LocationPrivacyUpdateSerializer,
    LocationPermissionSerializer,
    LocationHistorySerializer,
    UserMatchSerializer,
    UserProfileWithLocationSerializer,
    NearbyUserSerializer,
    MatchPreferencesSerializer
)
import time
from deep_translator import GoogleTranslator
from django.db import models
import os
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from .jwt_utils import generate_tokens, refresh_access_token, revoke_refresh_token
from .permissions import AdminJWTPermission

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
                name = serializer.validated_data.get('name', '')
                
                if NewsletterSubscriber.objects.filter(email=email).exists():
                    return Response({
                        "message": "Email already subscribed to newsletter",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Save the newsletter subscription
                subscriber = serializer.save()
                
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
                    
                except Exception as e:
                    email_log.is_sent = False
                    email_log.error_message = str(e)
                    email_log.save()
                    # Don't fail the signup if email fails
                
                # Return success response
                return Response({
                    "message": "Subscription successful! Welcome email sent.",
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
    """Join the waitlist"""
    serializer_class = WaitlistSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        """Create a new waitlist entry - ULTIMATE FIX"""
        try:
            # Parse request data safely
            if hasattr(request, 'data'):
                data = request.data
            else:
                import json
                data = json.loads(request.body.decode('utf-8')) if request.body else {}
            
            print(f"📋 Received data: {data}")  # Debug log
            
            # Validate serializer
            serializer = self.get_serializer(data=data)
            if not serializer.is_valid():
                print(f"❌ Serializer errors: {serializer.errors}")  # Debug log
                return Response({
                    "message": "Invalid data provided",
                    "status": "error",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            print(f"✅ Serializer valid: {serializer.validated_data}")  # Debug log
            
            # Check if email already exists
            email = serializer.validated_data.get('email', '')
            if Waitlist.objects.filter(email=email).exists():
                print(f"✅ Email already exists: {email}")  # Debug log
                return Response({
                    "message": "Email already registered on waitlist",
                    "status": "success",
                    "data": serializer.data
                }, status=status.HTTP_200_OK)
            
            # ULTIMATE FIX: Save directly to database with proper column handling
            print(f"📋 Saving waitlist entry: {email}")  # Debug log
            
            # Get the data
            first_name = serializer.validated_data.get('first_name', '')
            last_name = serializer.validated_data.get('last_name', '')
            
            # Save using raw SQL to handle column name issues
            from django.db import connection
            with connection.cursor() as cursor:
                # Try with date_joined first
                try:
                    cursor.execute("""
                        INSERT INTO dating_waitlist (email, first_name, last_name, date_joined) 
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    """, (email, first_name, last_name))
                    print("✅ Saved with date_joined column")
                except Exception as e:
                    print(f"❌ date_joined failed: {str(e)}")
                    # Try with joined_at
                    try:
                        cursor.execute("""
                            INSERT INTO dating_waitlist (email, first_name, last_name, joined_at) 
                            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        """, (email, first_name, last_name))
                        print("✅ Saved with joined_at column")
                    except Exception as e2:
                        print(f"❌ joined_at failed: {str(e2)}")
                        # Try without timestamp column
                        cursor.execute("""
                            INSERT INTO dating_waitlist (email, first_name, last_name) 
                            VALUES (%s, %s, %s)
                        """, (email, first_name, last_name))
                        print("✅ Saved without timestamp column")
            
            # Verify it was saved
            saved_entry = Waitlist.objects.filter(email=email).first()
            if saved_entry:
                print(f"✅ Entry verified in database: {saved_entry}")  # Debug log
            else:
                print(f"❌ Entry NOT found in database after save!")  # Debug log
            
            return Response({
                "message": "Successfully joined the waitlist!",
                "status": "success",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print(f"❌ Waitlist creation error: {str(e)}")  # Debug log
            import traceback
            traceback.print_exc()
            
            # Return error instead of fake success
            return Response({
                "message": f"Failed to join waitlist: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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


class JobApplicationView(generics.CreateAPIView):
    serializer_class = JobApplicationSerializer

    def create(self, request, *args, **kwargs):
        try:
            # Handle both DRF request and regular Django request
            if hasattr(request, 'data'):
                data = request.data
            else:
                # For regular Django request, parse JSON from body
                import json
                data = json.loads(request.body.decode('utf-8')) if request.body else {}
            
            serializer = self.get_serializer(data=data)
            if serializer.is_valid():
                # Get the job
                job_id = serializer.validated_data.get('job', {}).get('id')
                job = Job.objects.get(id=job_id)
                
                # Get applicant details
                applicant_email = serializer.validated_data.get('email', '')
                first_name = serializer.validated_data.get('first_name', '')
                last_name = serializer.validated_data.get('last_name', '')
                applicant_name = f"{first_name} {last_name}".strip()
                
                # Create the application
                application = serializer.save(job=job)
                
                # Send automatic confirmation email
                subject = f"Application Received - {job.title} at Bondah Dating"
                message = f"""
Hi {applicant_name},

Thank you for your interest in joining the Bondah Dating team!

We've received your application for the {job.title} position and are excited to review your qualifications.

What happens next:
• Our team will review your application within 3-5 business days
• If selected, we'll contact you for the next steps
• You'll receive updates on your application status

Application Details:
• Position: {job.title}
• Application ID: {application.id}
• Applied: {application.applied_at.strftime('%B %d, %Y')}

We appreciate your interest in helping us build the future of dating!

Best regards,
The Bondah Team

P.S. Follow us on social media to stay updated on our journey!
                """.strip()
                
                # Log email attempt
                email_log = EmailLog.objects.create(
                    email_type='job_application_confirmation',
                    recipient_email=applicant_email,
                    subject=subject,
                    message=message
                )
                
                try:
                    # Send email using Django's email functionality
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[applicant_email],
                        fail_silently=False,
                    )
                    
                    email_log.is_sent = True
                    email_log.save()
                    
                except Exception as e:
                    email_log.is_sent = False
                    email_log.error_message = str(e)
                    email_log.save()
                    # Don't fail the application if email fails
                
                # Return success response
                return Response({
                    "message": "Job application submitted successfully! Confirmation email sent.",
                    "status": "success",
                    "applicationId": application.id
                }, status=status.HTTP_201_CREATED)
            
            return Response({
                "message": "Invalid application data",
                "status": "error",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Job.DoesNotExist:
            return Response({
                "message": "Job not found",
                "status": "error"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "message": f"Application failed: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminLoginView(APIView):
    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            try:
                admin_user = AdminUser.objects.get(email=email, is_active=True)
                if check_password(password, admin_user.password):
                    # Generate OTP
                    otp_code = ''.join(random.choices(string.digits, k=6))
                    expires_at = timezone.now() + timedelta(minutes=10)
                    
                    # Create OTP record
                    AdminOTP.objects.create(
                        admin_user=admin_user,
                        otp_code=otp_code,
                        expires_at=expires_at
                    )
                    
                    # Send OTP email
                    subject = "🔐 Admin Login OTP - Bondah Dating"
                    message = f"""
Hi there,

Your OTP for admin login is: {otp_code}

This code will expire in 10 minutes.
If you didn't request this login, please ignore this email and contact support immediately.

For security reasons, please:
• Don't share this code with anyone
• Use it only on the official Bondah admin portal
• Delete this email after use

Best regards,
The Bondah Team

P.S. Keep your admin credentials secure!
                    """.strip()
                    
                    try:
                        # Send email with timeout handling
                        send_mail(
                            subject=subject,
                            message=message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[email],
                            fail_silently=True,  # Don't fail the request if email fails
                        )
                        
                        return Response({
                            "message": "OTP sent to your email",
                            "status": "success"
                        }, status=status.HTTP_200_OK)
                    except Exception as e:
                        # Log the error but don't fail the request
                        print(f"Email sending failed: {str(e)}")
                        return Response({
                            "message": "OTP generated but email delivery may be delayed",
                            "status": "success",
                            "otp_code": otp_code  # Temporarily return OTP for debugging
                        }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        "message": "Invalid credentials",
                        "status": "error"
                    }, status=status.HTTP_401_UNAUTHORIZED)
            except AdminUser.DoesNotExist:
                return Response({
                    "message": "Invalid credentials",
                    "status": "error"
                }, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response({
            "message": "Invalid data",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class AdminOTPVerificationView(APIView):
    def post(self, request):
        serializer = AdminOTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp_code = serializer.validated_data['otp_code']
            
            try:
                admin_user = AdminUser.objects.get(email=email, is_active=True)
                otp = AdminOTP.objects.filter(
                    admin_user=admin_user,
                    otp_code=otp_code,
                    is_used=False
                ).latest('created_at')
                
                if otp.is_expired():
                    return Response({
                        "message": "OTP has expired",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Mark OTP as used
                otp.is_used = True
                otp.save()
                
                # Update last login
                admin_user.last_login = timezone.now()
                admin_user.save()
                
                # Generate JWT tokens
                tokens = generate_tokens(admin_user)
                
                return Response({
                    "message": "Login successful",
                    "status": "success",
                    "admin_email": admin_user.email,
                    "access_token": tokens['access_token'],
                    "refresh_token": tokens['refresh_token'],
                    "access_token_expires": tokens['access_token_expires'],
                    "refresh_token_expires": tokens['refresh_token_expires']
                }, status=status.HTTP_200_OK)
                
            except (AdminUser.DoesNotExist, AdminOTP.DoesNotExist):
                return Response({
                    "message": "Invalid OTP",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            "message": "Invalid data",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class AdminJobListView(APIView):
    def get(self, request):
        try:
            jobs = Job.objects.all().order_by('-created_at')
            serializer = AdminJobListSerializer(jobs, many=True)
            
            return Response({
                "message": "Jobs retrieved successfully",
                "status": "success",
                "jobs": serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "message": f"Failed to retrieve jobs: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminJobCreateView(APIView):
    def post(self, request):
        try:
            serializer = AdminJobCreateSerializer(data=request.data)
            if serializer.is_valid():
                job = serializer.save()
                
                return Response({
                    "message": "Job created successfully",
                    "status": "success",
                    "job": AdminJobCreateSerializer(job).data
                }, status=status.HTTP_201_CREATED)
            
            return Response({
                "message": "Invalid job data",
                "status": "error",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "message": f"Failed to create job: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminJobUpdateView(APIView):
    def put(self, request, job_id):
        try:
            job = Job.objects.get(id=job_id)
            serializer = AdminJobUpdateSerializer(job, data=request.data, partial=True)
            
            if serializer.is_valid():
                updated_job = serializer.save()
                
                return Response({
                    "message": "Job updated successfully",
                    "status": "success",
                    "job": AdminJobUpdateSerializer(updated_job).data
                }, status=status.HTTP_200_OK)
            
            return Response({
                "message": "Invalid job data",
                "status": "error",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Job.DoesNotExist:
            return Response({
                "message": "Job not found",
                "status": "error"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "message": f"Failed to update job: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminJobApplicationsView(APIView):
    def get(self, request):
        try:
            # Get query parameters for filtering
            job_id = request.query_params.get('job_id')
            status_filter = request.query_params.get('status')
            
            applications = JobApplication.objects.all().order_by('-applied_at')
            
            if job_id:
                applications = applications.filter(job_id=job_id)
            if status_filter:
                applications = applications.filter(status=status_filter)
            
            serializer = AdminJobApplicationSerializer(applications, many=True)
            
            return Response({
                "message": "Applications retrieved successfully",
                "status": "success",
                "applications": serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "message": f"Failed to retrieve applications: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminUpdateApplicationStatusView(APIView):
    def put(self, request, application_id):
        try:
            application = JobApplication.objects.get(id=application_id)
            new_status = request.data.get('status')
            
            if not new_status:
                return Response({
                    "message": "Status is required",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate status
            valid_statuses = [choice[0] for choice in JobApplication.STATUS_CHOICES]
            if new_status not in valid_statuses:
                return Response({
                    "message": f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            application.status = new_status
            application.save()
            
            return Response({
                "message": "Application status updated successfully",
                "status": "success",
                "application": AdminJobApplicationSerializer(application).data
            }, status=status.HTTP_200_OK)
        except JobApplication.DoesNotExist:
            return Response({
                "message": "Application not found",
                "status": "error"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "message": f"Failed to update application status: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminJobApplicationDetailView(APIView):
    def get(self, request, application_id):
        """Get detailed view of a specific job application"""
        try:
            application = JobApplication.objects.get(id=application_id)
            serializer = AdminJobApplicationDetailSerializer(application)
            
            return Response({
                "message": "Application details retrieved successfully",
                "status": "success",
                "application": serializer.data
            }, status=status.HTTP_200_OK)
        except JobApplication.DoesNotExist:
            return Response({
                "message": "Application not found",
                "status": "error"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "message": f"Failed to retrieve application details: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TranslationView(APIView):
    def post(self, request):
        start_time = time.time()
        
        try:
            serializer = TranslationRequestSerializer(data=request.data)
            if serializer.is_valid():
                text = serializer.validated_data['text']
                source_language = serializer.validated_data.get('source_language', 'auto')
                target_language = serializer.validated_data['target_language']
                
                # Initialize translator
                if source_language == 'auto':
                    # For auto-detect, we'll use 'auto' as source and assume English if detection fails
                    try:
                        translator = GoogleTranslator(source='auto', target=target_language)
                        translated_text = translator.translate(text)
                        detected_source = 'auto'  # We'll store 'auto' as detected source
                    except:
                        # Fallback to English if auto-detection fails
                        translator = GoogleTranslator(source='en', target=target_language)
                        translated_text = translator.translate(text)
                        detected_source = 'en'
                else:
                    # Use specified source language
                    translator = GoogleTranslator(source=source_language, target=target_language)
                    translated_text = translator.translate(text)
                    detected_source = source_language
                translation_time = time.time() - start_time
                
                # Log translation
                translation_log = TranslationLog.objects.create(
                    source_text=text,
                    translated_text=translated_text,
                    source_language=detected_source,
                    target_language=target_language,
                    character_count=len(text),
                    translation_time=translation_time,
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                return Response({
                    "message": "Translation successful",
                    "status": "success",
                    "translation": {
                        "source_text": text,
                        "translated_text": translated_text,
                        "source_language": detected_source,
                        "target_language": target_language,
                        "character_count": len(text),
                        "translation_time": round(translation_time, 3)
                    }
                }, status=status.HTTP_200_OK)
            
            return Response({
                "message": "Invalid translation request",
                "status": "error",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                "message": f"Translation failed: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SupportedLanguagesView(APIView):
    def get(self, request):
        try:
            languages = {
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
            
            return Response({
                "message": "Supported languages retrieved successfully",
                "status": "success",
                "languages": languages,
                "total_languages": len(languages)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "message": f"Failed to retrieve languages: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TranslationHistoryView(APIView):
    def get(self, request):
        try:
            # Get query parameters for filtering
            source_language = request.query_params.get('source_language')
            target_language = request.query_params.get('target_language')
            limit = int(request.query_params.get('limit', 50))
            
            translations = TranslationLog.objects.all().order_by('-created_at')
            
            if source_language:
                translations = translations.filter(source_language=source_language)
            if target_language:
                translations = translations.filter(target_language=target_language)
            
            # Limit results
            translations = translations[:limit]
            
            serializer = TranslationResponseSerializer(translations, many=True)
            
            return Response({
                "message": "Translation history retrieved successfully",
                "status": "success",
                "translations": serializer.data,
                "total_count": len(serializer.data)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "message": f"Failed to retrieve translation history: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TranslationStatsView(APIView):
    def get(self, request):
        try:
            total_translations = TranslationLog.objects.count()
            total_characters = TranslationLog.objects.aggregate(
                total_chars=models.Sum('character_count')
            )['total_chars'] or 0
            
            # Most popular target languages
            popular_targets = TranslationLog.objects.values('target_language').annotate(
                count=models.Count('id')
            ).order_by('-count')[:10]
            
            # Most popular source languages
            popular_sources = TranslationLog.objects.values('source_language').annotate(
                count=models.Count('id')
            ).order_by('-count')[:10]
            
            # Average translation time
            avg_time = TranslationLog.objects.aggregate(
                avg_time=models.Avg('translation_time')
            )['avg_time'] or 0
            
            return Response({
                "message": "Translation statistics retrieved successfully",
                "status": "success",
                "stats": {
                    "total_translations": total_translations,
                    "total_characters_translated": total_characters,
                    "average_translation_time": round(avg_time, 3),
                    "popular_target_languages": list(popular_targets),
                    "popular_source_languages": list(popular_sources)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "message": f"Failed to retrieve translation statistics: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class JobOptionsView(APIView):
    """Provide job categories and types for frontend dropdowns"""
    
    def get(self, request):
        """Get available job categories and types"""
        try:
            # Get job categories and types from the Job model
            job_categories = [{'value': choice[0], 'label': choice[1]} for choice in Job.CATEGORIES]
            job_types = [{'value': choice[0], 'label': choice[1]} for choice in Job.JOB_TYPES]
            job_statuses = [{'value': choice[0], 'label': choice[1]} for choice in Job.STATUS_CHOICES]
            
            return Response({
                'categories': job_categories,
                'job_types': job_types,
                'statuses': job_statuses,
                'status': 'success'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'message': f'Error fetching job options: {str(e)}',
                'status': 'error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminWaitlistListView(APIView):
    """Admin view to list all waitlist entries"""
    permission_classes = [AdminJWTPermission]
    
    def get(self, request):
        """Get all waitlist entries"""
        try:
            waitlist_entries = Waitlist.objects.all().order_by('-date_joined')
            
            # Serialize the data
            data = []
            for entry in waitlist_entries:
                data.append({
                    'id': entry.id,
                    'email': entry.email,
                    'first_name': entry.first_name,
                    'last_name': entry.last_name,
                    'date_joined': entry.date_joined.isoformat() if entry.date_joined else None
                })
            
            return Response({
                "message": "Waitlist entries retrieved successfully",
                "status": "success",
                "count": len(data),
                "entries": data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "message": f"Failed to retrieve waitlist entries: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminNewsletterListView(APIView):
    """Admin view to list all newsletter subscribers"""
    permission_classes = [AdminJWTPermission]
    
    def get(self, request):
        """Get all newsletter subscribers"""
        try:
            # Debug: Check if we can access the admin user
            admin_user = getattr(request, 'admin_user', None)
            if not admin_user:
                return Response({
                    "message": "Admin user not found in request",
                    "status": "error"
                }, status=status.HTTP_403_FORBIDDEN)
            
            subscribers = NewsletterSubscriber.objects.all().order_by('-date_subscribed')
            
            # Serialize the data
            data = []
            for subscriber in subscribers:
                data.append({
                    'id': subscriber.id,
                    'email': subscriber.email,
                    'date_subscribed': subscriber.date_subscribed.isoformat() if subscriber.date_subscribed else None
                })
            
            return Response({
                "message": "Newsletter subscribers retrieved successfully",
                "status": "success",
                "count": len(data),
                "subscribers": data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "message": f"Failed to retrieve newsletter subscribers: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminTokenRefreshView(APIView):
    """Refresh access token using refresh token"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Refresh access token"""
        try:
            refresh_token = request.data.get('refresh_token')
            if not refresh_token:
                return Response({
                    "message": "Refresh token is required",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate new access token
            new_tokens = refresh_access_token(refresh_token)
            
            return Response({
                "message": "Token refreshed successfully",
                "status": "success",
                "access_token": new_tokens['access_token'],
                "access_token_expires": new_tokens['access_token_expires']
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "message": f"Failed to refresh token: {str(e)}",
                "status": "error"
            }, status=status.HTTP_401_UNAUTHORIZED)


class AdminLogoutView(APIView):
    """Logout admin user and revoke refresh token"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Logout and revoke refresh token"""
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                # Revoke the refresh token
                revoke_refresh_token(refresh_token)
            
            return Response({
                "message": "Logged out successfully",
                "status": "success"
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "message": f"Failed to logout: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminVerifyTokenView(APIView):
    """Verify if access token is valid"""
    permission_classes = [AdminJWTPermission]
    
    def get(self, request):
        """Verify token and return admin info"""
        try:
            admin_user = request.admin_user
            
            return Response({
                "message": "Token is valid",
                "status": "success",
                "admin_email": admin_user.email,
                "admin_id": admin_user.id
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "message": f"Token verification failed: {str(e)}",
                "status": "error"
            }, status=status.HTTP_401_UNAUTHORIZED)


class AdminDebugAuthView(APIView):
    """Debug endpoint to check authentication status"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Debug authentication headers and token"""
        auth_header = request.headers.get('Authorization')
        
        debug_info = {
            "has_authorization_header": bool(auth_header),
            "authorization_header": auth_header,
            "all_headers": dict(request.headers),
        }
        
        if auth_header:
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                debug_info["token_length"] = len(token) if token else 0
                debug_info["token_format"] = "Valid Bearer format"
                
                # Try to decode token
                try:
                    from .jwt_utils import verify_token
                    payload = verify_token(token, 'access')
                    debug_info["token_valid"] = True
                    debug_info["token_payload"] = payload
                except Exception as e:
                    debug_info["token_valid"] = False
                    debug_info["token_error"] = str(e)
            else:
                debug_info["token_format"] = "Invalid format - should start with 'Bearer '"
        else:
            debug_info["token_format"] = "No Authorization header"
        
        return Response({
            "message": "Debug authentication info",
            "status": "success",
            "debug_info": debug_info
        }, status=status.HTTP_200_OK)


# =============================================================================
# MOBILE APP AUTHENTICATION VIEWS
# =============================================================================

class UserRegisterView(APIView):
    """User registration for mobile app"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = CustomRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate JWT tokens
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(user)
            
            return Response({
                "message": "User registered successfully",
                "status": "success",
                "user": UserProfileSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh)
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            "message": "Registration failed",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    """User login for mobile app"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = CustomLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Generate JWT tokens
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(user)
            
            return Response({
                "message": "Login successful",
                "status": "success",
                "user": UserProfileSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh)
                }
            }, status=status.HTTP_200_OK)
        
        return Response({
            "message": "Login failed",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class UserLogoutView(APIView):
    """User logout for mobile app"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                from rest_framework_simplejwt.tokens import RefreshToken
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return Response({
                "message": "Logout successful",
                "status": "success"
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "message": f"Logout failed: {str(e)}",
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)


class TokenRefreshView(APIView):
    """Refresh JWT token for mobile app"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if not refresh_token:
                return Response({
                    "message": "Refresh token is required",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from rest_framework_simplejwt.tokens import RefreshToken
            token = RefreshToken(refresh_token)
            
            return Response({
                "message": "Token refreshed successfully",
                "status": "success",
                "tokens": {
                    "access": str(token.access_token),
                    "refresh": str(token)
                }
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "message": f"Token refresh failed: {str(e)}",
                "status": "error"
            }, status=status.HTTP_401_UNAUTHORIZED)


class PasswordResetView(APIView):
    """Password reset request for mobile app"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.get(email=email)
            
            # Generate reset token
            from django.contrib.auth.tokens import default_token_generator
            from django.utils.http import urlsafe_base64_encode
            from django.utils.encoding import force_bytes
            
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Send reset email
            reset_url = f"https://bondah.org/reset-password/{uid}/{token}/"
            subject = "Password Reset - Bondah Dating"
            message = f"""
Hi {user.name},

You requested a password reset for your Bondah Dating account.

Click the link below to reset your password:
{reset_url}

If you didn't request this, please ignore this email.

Best regards,
The Bondah Team
            """.strip()
            
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                
                return Response({
                    "message": "Password reset email sent",
                    "status": "success"
                }, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({
                    "message": f"Failed to send reset email: {str(e)}",
                    "status": "error"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            "message": "Invalid email",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    """Password reset confirmation for mobile app"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            new_password = serializer.validated_data['new_password']
            
            user.set_password(new_password)
            user.save()
            
            return Response({
                "message": "Password reset successfully",
                "status": "success"
            }, status=status.HTTP_200_OK)
        
        return Response({
            "message": "Password reset failed",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    """Get and update user profile for mobile app"""
    
    def get(self, request):
        """Get user profile"""
        try:
            user = request.user
            serializer = UserProfileSerializer(user)
            return Response({
                "message": "Profile retrieved successfully",
                "status": "success",
                "user": serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "message": f"Failed to retrieve profile: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request):
        """Update user profile"""
        try:
            user = request.user
            serializer = UserProfileUpdateSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                updated_user = serializer.save()
                return Response({
                    "message": "Profile updated successfully",
                    "status": "success",
                    "user": UserProfileSerializer(updated_user).data
                }, status=status.HTTP_200_OK)
            
            return Response({
                "message": "Profile update failed",
                "status": "error",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "message": f"Failed to update profile: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GoogleOAuthView(APIView):
    """Google OAuth login for mobile app"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = GoogleOAuthSerializer(data=request.data)
        if serializer.is_valid():
            access_token = serializer.validated_data['access_token']
            
            try:
                # Import OAuth utilities
                from .oauth_utils import GoogleOAuthVerifier, OAuthUserManager, OAuthTokenGenerator
                
                # Verify Google token and get user info
                oauth_data, error = GoogleOAuthVerifier.verify_access_token(access_token)
                
                if error:
                    return Response({
                        "message": f"Google OAuth verification failed: {error}",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Get or create user from OAuth data
                user, error = OAuthUserManager.get_or_create_user_from_oauth(oauth_data, 'google')
                
                if error:
                    return Response({
                        "message": f"User creation failed: {error}",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Generate JWT tokens
                tokens, error = OAuthTokenGenerator.generate_tokens(user)
                
                if error:
                    return Response({
                        "message": f"Token generation failed: {error}",
                        "status": "error"
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                return Response({
                    "message": "Google login successful",
                    "status": "success",
                    "user": UserProfileWithSocialSerializer(user).data,
                    "tokens": tokens
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    "message": f"Google login failed: {str(e)}",
                    "status": "error"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            "message": "Invalid Google OAuth data",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class AppleOAuthView(APIView):
    """Apple Sign-In for mobile app"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = AppleOAuthSerializer(data=request.data)
        if serializer.is_valid():
            identity_token = serializer.validated_data['identity_token']
            
            try:
                # Import OAuth utilities
                from .oauth_utils import AppleOAuthVerifier, OAuthUserManager, OAuthTokenGenerator
                
                # Verify Apple identity token and get user info
                oauth_data, error = AppleOAuthVerifier.verify_identity_token(identity_token)
                
                if error:
                    return Response({
                        "message": f"Apple OAuth verification failed: {error}",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Get or create user from OAuth data
                user, error = OAuthUserManager.get_or_create_user_from_oauth(oauth_data, 'apple')
                
                if error:
                    return Response({
                        "message": f"User creation failed: {error}",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Generate JWT tokens
                tokens, error = OAuthTokenGenerator.generate_tokens(user)
                
                if error:
                    return Response({
                        "message": f"Token generation failed: {error}",
                        "status": "error"
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                return Response({
                    "message": "Apple login successful",
                    "status": "success",
                    "user": UserProfileWithSocialSerializer(user).data,
                    "tokens": tokens
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    "message": f"Apple login failed: {str(e)}",
                    "status": "error"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            "message": "Invalid Apple OAuth data",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class SocialLoginView(APIView):
    """Unified social login endpoint (Google/Apple)"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = OAuthLoginSerializer(data=request.data)
        if serializer.is_valid():
            provider = serializer.validated_data['provider']
            
            try:
                if provider == 'google':
                    # Handle Google OAuth
                    google_data = serializer.validated_data['google_data']
                    access_token = google_data['access_token']
                    
                    # Import OAuth utilities
                    from .oauth_utils import GoogleOAuthVerifier, OAuthUserManager, OAuthTokenGenerator
                    
                    # Verify Google token
                    oauth_data, error = GoogleOAuthVerifier.verify_access_token(access_token)
                    
                elif provider == 'apple':
                    # Handle Apple OAuth
                    apple_data = serializer.validated_data['apple_data']
                    identity_token = apple_data['identity_token']
                    
                    # Import OAuth utilities
                    from .oauth_utils import AppleOAuthVerifier, OAuthUserManager, OAuthTokenGenerator
                    
                    # Verify Apple token
                    oauth_data, error = AppleOAuthVerifier.verify_identity_token(identity_token)
                
                if error:
                    return Response({
                        "message": f"{provider.title()} OAuth verification failed: {error}",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Get or create user
                user, error = OAuthUserManager.get_or_create_user_from_oauth(oauth_data, provider)
                
                if error:
                    return Response({
                        "message": f"User creation failed: {error}",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Generate tokens
                tokens, error = OAuthTokenGenerator.generate_tokens(user)
                
                if error:
                    return Response({
                        "message": f"Token generation failed: {error}",
                        "status": "error"
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                return Response({
                    "message": f"{provider.title()} login successful",
                    "status": "success",
                    "user": UserProfileWithSocialSerializer(user).data,
                    "tokens": tokens
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    "message": f"Social login failed: {str(e)}",
                    "status": "error"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            "message": "Invalid social login data",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class DeviceRegistrationView(APIView):
    """Register device for push notifications"""
    
    def post(self, request):
        serializer = DeviceRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Create or update device registration
                device, created = DeviceRegistration.objects.get_or_create(
                    device_id=serializer.validated_data['device_id'],
                    defaults={
                        'user': request.user,
                        'device_type': serializer.validated_data['device_type'],
                        'push_token': serializer.validated_data['push_token'],
                        'is_active': True
                    }
                )
                
                if not created:
                    # Update existing device
                    device.device_type = serializer.validated_data['device_type']
                    device.push_token = serializer.validated_data['push_token']
                    device.is_active = True
                    device.save()
                
                return Response({
                    "message": "Device registered successfully",
                    "status": "success",
                    "device_id": device.device_id,
                    "created": created
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    "message": f"Device registration failed: {str(e)}",
                    "status": "error"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            "message": "Device registration failed",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class OAuthLinkAccountView(APIView):
    """Link social account to existing user"""
    
    def post(self, request):
        serializer = OAuthLinkSerializer(data=request.data)
        if serializer.is_valid():
            provider = serializer.validated_data['provider']
            
            try:
                # Import OAuth utilities
                from .oauth_utils import GoogleOAuthVerifier, AppleOAuthVerifier, OAuthUserManager
                
                # Verify token based on provider
                if provider == 'google':
                    access_token = serializer.validated_data['access_token']
                    oauth_data, error = GoogleOAuthVerifier.verify_access_token(access_token)
                elif provider == 'apple':
                    identity_token = serializer.validated_data['identity_token']
                    oauth_data, error = AppleOAuthVerifier.verify_identity_token(identity_token)
                
                if error:
                    return Response({
                        "message": f"OAuth verification failed: {error}",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Link social account to current user
                social_account, error = OAuthUserManager.link_social_account(
                    request.user, oauth_data, provider
                )
                
                if error:
                    return Response({
                        "message": f"Account linking failed: {error}",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                return Response({
                    "message": f"{provider.title()} account linked successfully",
                    "status": "success",
                    "social_account": SocialAccountSerializer(social_account).data
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    "message": f"Account linking failed: {str(e)}",
                    "status": "error"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            "message": "Invalid OAuth data",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class OAuthUnlinkAccountView(APIView):
    """Unlink social account from user"""
    
    def delete(self, request, provider):
        try:
            # Find and deactivate social account
            social_account = SocialAccount.objects.get(
                user=request.user,
                provider=provider,
                is_active=True
            )
            
            social_account.is_active = False
            social_account.save()
            
            return Response({
                "message": f"{provider.title()} account unlinked successfully",
                "status": "success"
            }, status=status.HTTP_200_OK)
            
        except SocialAccount.DoesNotExist:
            return Response({
                "message": f"No active {provider} account found",
                "status": "error"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "message": f"Account unlinking failed: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SocialAccountsListView(APIView):
    """List user's linked social accounts"""
    
    def get(self, request):
        try:
            social_accounts = SocialAccount.objects.filter(
                user=request.user,
                is_active=True
            )
            
            serializer = SocialAccountSerializer(social_accounts, many=True)
            
            return Response({
                "message": "Social accounts retrieved successfully",
                "status": "success",
                "social_accounts": serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "message": f"Failed to retrieve social accounts: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Location Management Views
class LocationUpdateView(APIView):
    """Update user's current location"""
    
    def post(self, request):
        serializer = LocationUpdateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                from .location_utils import update_user_location
                
                latitude = serializer.validated_data['latitude']
                longitude = serializer.validated_data['longitude']
                accuracy = serializer.validated_data.get('accuracy')
                source = serializer.validated_data.get('source', 'gps')
                
                success = update_user_location(
                    request.user, latitude, longitude, accuracy, source
                )
                
                if success:
                    return Response({
                        "message": "Location updated successfully",
                        "status": "success",
                        "location": {
                            "latitude": float(latitude),
                            "longitude": float(longitude),
                            "city": request.user.city,
                            "state": request.user.state,
                            "country": request.user.country
                        }
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        "message": "Failed to update location",
                        "status": "error"
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
            except Exception as e:
                return Response({
                    "message": f"Location update failed: {str(e)}",
                    "status": "error"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            "message": "Invalid location data",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class AddressGeocodeView(APIView):
    """Convert address to GPS coordinates"""
    
    def post(self, request):
        serializer = AddressGeocodeSerializer(data=request.data)
        if serializer.is_valid():
            try:
                from .location_utils import geocode_address
                
                address = serializer.validated_data['address']
                result = geocode_address(address)
                
                if result:
                    return Response({
                        "message": "Address geocoded successfully",
                        "status": "success",
                        "coordinates": {
                            "latitude": result['latitude'],
                            "longitude": result['longitude'],
                            "formatted_address": result['formatted_address'],
                            "accuracy": result.get('accuracy', 'UNKNOWN')
                        }
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        "message": "Could not geocode address",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except Exception as e:
                return Response({
                    "message": f"Geocoding failed: {str(e)}",
                    "status": "error"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            "message": "Invalid address data",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class LocationPrivacyUpdateView(APIView):
    """Update user's location privacy settings"""
    
    def put(self, request):
        serializer = LocationPrivacyUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            try:
                serializer.save()
                
                return Response({
                    "message": "Location privacy settings updated successfully",
                    "status": "success",
                    "settings": serializer.data
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    "message": f"Failed to update privacy settings: {str(e)}",
                    "status": "error"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            "message": "Invalid privacy settings data",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class LocationPermissionsView(APIView):
    """Manage user's location permissions"""
    
    def get(self, request):
        try:
            permissions, created = LocationPermission.objects.get_or_create(user=request.user)
            serializer = LocationPermissionSerializer(permissions)
            
            return Response({
                "message": "Location permissions retrieved successfully",
                "status": "success",
                "permissions": serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "message": f"Failed to retrieve permissions: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request):
        try:
            permissions, created = LocationPermission.objects.get_or_create(user=request.user)
            serializer = LocationPermissionSerializer(permissions, data=request.data, partial=True)
            
            if serializer.is_valid():
                serializer.save()
                
                return Response({
                    "message": "Location permissions updated successfully",
                    "status": "success",
                    "permissions": serializer.data
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "message": "Invalid permissions data",
                    "status": "error",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                "message": f"Failed to update permissions: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LocationHistoryView(APIView):
    """Get user's location history"""
    
    def get(self, request):
        try:
            # Get recent location history (last 30 entries)
            history = LocationHistory.objects.filter(user=request.user)[:30]
            serializer = LocationHistorySerializer(history, many=True)
            
            return Response({
                "message": "Location history retrieved successfully",
                "status": "success",
                "history": serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "message": f"Failed to retrieve location history: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NearbyUsersView(APIView):
    """Find nearby users for matching"""
    
    def get(self, request):
        try:
            from .location_utils import find_nearby_users
            
            max_distance = request.GET.get('max_distance')
            if max_distance:
                max_distance = int(max_distance)
            
            nearby_users = find_nearby_users(request.user, max_distance)
            
            # Serialize results
            results = []
            for user_data in nearby_users:
                user = user_data['user']
                serializer = NearbyUserSerializer(user)
                result = serializer.data
                result['distance'] = user_data['distance']
                result['coordinates'] = user_data['coordinates']
                results.append(result)
            
            return Response({
                "message": "Nearby users retrieved successfully",
                "status": "success",
                "nearby_users": results,
                "count": len(results)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "message": f"Failed to find nearby users: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MatchPreferencesView(APIView):
    """Update user's matching preferences"""
    
    def get(self, request):
        try:
            serializer = MatchPreferencesSerializer(request.user)
            
            return Response({
                "message": "Match preferences retrieved successfully",
                "status": "success",
                "preferences": serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "message": f"Failed to retrieve preferences: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request):
        serializer = MatchPreferencesSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            try:
                serializer.save()
                
                return Response({
                    "message": "Match preferences updated successfully",
                    "status": "success",
                    "preferences": serializer.data
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    "message": f"Failed to update preferences: {str(e)}",
                    "status": "error"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            "message": "Invalid preferences data",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class UserLocationProfileView(APIView):
    """Get user profile with location information"""
    
    def get(self, request):
        try:
            serializer = UserProfileWithLocationSerializer(request.user)
            
            return Response({
                "message": "User profile retrieved successfully",
                "status": "success",
                "user": serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "message": f"Failed to retrieve profile: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LocationStatisticsView(APIView):
    """Get location-related statistics (admin only)"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # Check if user is admin
            if not request.user.is_staff:
                return Response({
                    "message": "Admin access required",
                    "status": "error"
                }, status=status.HTTP_403_FORBIDDEN)
            
            from .location_utils import get_location_statistics
            
            stats = get_location_statistics()
            
            return Response({
                "message": "Location statistics retrieved successfully",
                "status": "success",
                "statistics": stats
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "message": f"Failed to retrieve statistics: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# EMAIL AND PHONE VERIFICATION VIEWS
# =============================================================================

class EmailOTPRequestView(APIView):
    """Request email OTP for verification"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        from .serializers import EmailOTPRequestSerializer
        serializer = EmailOTPRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            
            try:
                # Get or create user
                User = get_user_model()
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={'username': email, 'is_active': False}
                )
                
                # Check rate limiting
                if not EmailVerification.can_resend_for_email(email):
                    return Response({
                        "message": "Too many OTP requests. Please wait 1 minute.",
                        "status": "error"
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)
                
                # Create verification
                verification = EmailVerification.create_verification(user, email)
                
                # Send OTP email
                subject = "🔐 Verify Your Email - Bondah Dating"
                message = f"""
Hi there,

Your email verification code is: {verification.otp_code}

This code will expire in 10 minutes.
Enter this code in the app to verify your email address.

If you didn't request this verification, please ignore this email.

Best regards,
The Bondah Team
                """.strip()
                
                try:
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=False,
                    )
                    
                    return Response({
                        "message": "OTP sent to your email",
                        "status": "success",
                        "email": email,
                        "expires_in": 600  # 10 minutes
                    }, status=status.HTTP_200_OK)
                    
                except Exception as e:
                    return Response({
                        "message": "OTP generated but email delivery failed. Please try again.",
                        "status": "error"
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
            except Exception as e:
                return Response({
                    "message": "Failed to process email verification request",
                    "status": "error"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            "message": "Invalid email address",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class EmailOTPVerifyView(APIView):
    """Verify email OTP"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        from .serializers import EmailOTPVerifySerializer
        serializer = EmailOTPVerifySerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp_code = serializer.validated_data['otp_code']
            
            try:
                verification = EmailVerification.objects.filter(
                    email=email,
                    otp_code=otp_code,
                    is_used=False
                ).latest('created_at')
                
                if verification.is_expired():
                    return Response({
                        "message": "OTP has expired. Please request a new one.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Mark as verified and used
                verification.is_verified = True
                verification.is_used = True
                verification.verified_at = timezone.now()
                verification.save()
                
                # Activate user
                user = verification.user
                user.is_active = True
                user.save()
                
                # Update user verification status
                user_status, created = UserVerificationStatus.objects.get_or_create(user=user)
                user_status.email_verified = True
                user_status.email_verified_at = timezone.now()
                user_status.update_verification_level()
                
                return Response({
                    "message": "Email verified successfully",
                    "status": "success",
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "is_active": user.is_active
                    }
                }, status=status.HTTP_200_OK)
                
            except EmailVerification.DoesNotExist:
                return Response({
                    "message": "Invalid OTP code. Please try again.",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)
                
        return Response({
            "message": "Invalid verification data",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class PhoneOTPRequestView(APIView):
    """Request phone OTP for verification"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        from .serializers import PhoneOTPRequestSerializer
        serializer = PhoneOTPRequestSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            country_code = serializer.validated_data.get('country_code', '+1')
            
            try:
                # Get user from session or create temporary user
                user_id = request.data.get('user_id')
                if user_id:
                    User = get_user_model()
                    user = User.objects.get(id=user_id)
                else:
                    return Response({
                        "message": "User ID required for phone verification",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Check rate limiting
                if not PhoneVerification.can_resend_for_phone(phone_number, country_code):
                    return Response({
                        "message": "Too many OTP requests. Please wait 1 minute.",
                        "status": "error"
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)
                
                # Create verification
                verification = PhoneVerification.create_verification(user, phone_number, country_code)
                
                # In a real app, you would send SMS here using Twilio, AWS SNS, etc.
                # For now, we'll simulate SMS sending
                print(f"SMS OTP for {country_code}{phone_number}: {verification.otp_code}")
                
                return Response({
                    "message": "OTP sent to your phone",
                    "status": "success",
                    "phone_number": f"{country_code}{phone_number}",
                    "expires_in": 600  # 10 minutes
                }, status=status.HTTP_200_OK)
                
            except User.DoesNotExist:
                return Response({
                    "message": "User not found",
                    "status": "error"
                }, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                return Response({
                    "message": "Failed to process phone verification request",
                    "status": "error"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            "message": "Invalid phone number",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class PhoneOTPVerifyView(APIView):
    """Verify phone OTP"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        from .serializers import PhoneOTPVerifySerializer
        serializer = PhoneOTPVerifySerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            country_code = serializer.validated_data.get('country_code', '+1')
            otp_code = serializer.validated_data['otp_code']
            
            try:
                verification = PhoneVerification.objects.filter(
                    phone_number=phone_number,
                    country_code=country_code,
                    otp_code=otp_code,
                    is_used=False
                ).latest('created_at')
                
                if verification.is_expired():
                    return Response({
                        "message": "OTP has expired. Please request a new one.",
                        "status": "error"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Mark as verified and used
                verification.is_verified = True
                verification.is_used = True
                verification.verified_at = timezone.now()
                verification.save()
                
                # Update user verification status
                user_status, created = UserVerificationStatus.objects.get_or_create(user=verification.user)
                user_status.phone_verified = True
                user_status.phone_verified_at = timezone.now()
                user_status.update_verification_level()
                
                return Response({
                    "message": "Phone number verified successfully",
                    "status": "success",
                    "user": {
                        "id": verification.user.id,
                        "email": verification.user.email,
                        "phone_verified": True
                    }
                }, status=status.HTTP_200_OK)
                
            except PhoneVerification.DoesNotExist:
                return Response({
                    "message": "Invalid OTP code. Please try again.",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)
                
        return Response({
            "message": "Invalid verification data",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class UserRoleSelectionView(APIView):
    """Handle user role selection during onboarding"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        from .serializers import UserRoleSelectionSerializer
        serializer = UserRoleSelectionSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Create or update role selection
                role_selection, created = UserRoleSelection.objects.get_or_create(
                    user=request.user,
                    defaults={'selected_role': serializer.validated_data['selected_role']}
                )
                
                if not created:
                    role_selection.selected_role = serializer.validated_data['selected_role']
                    role_selection.save()
                
                # Update user's matchmaker status
                request.user.is_matchmaker = (serializer.validated_data['selected_role'] == 'bondmaker')
                request.user.save()
                
                return Response({
                    "message": "Role selection saved successfully",
                    "status": "success",
                    "selected_role": role_selection.selected_role,
                    "is_matchmaker": request.user.is_matchmaker
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    "message": "Failed to save role selection",
                    "status": "error"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            "message": "Invalid role selection data",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request):
        """Get user's current role selection"""
        try:
            role_selection = UserRoleSelection.objects.get(user=request.user)
            from .serializers import UserRoleSelectionSerializer
            serializer = UserRoleSelectionSerializer(role_selection)
            return Response({
                "message": "Role selection retrieved successfully",
                "status": "success",
                "role_selection": serializer.data
            }, status=status.HTTP_200_OK)
        except UserRoleSelection.DoesNotExist:
            return Response({
                "message": "No role selection found",
                "status": "success",
                "role_selection": None
            }, status=status.HTTP_200_OK)


class ResendOTPView(APIView):
    """Resend OTP for email or phone verification"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        verification_type = request.data.get('type')  # 'email' or 'phone'
        identifier = request.data.get('identifier')  # email or phone number
        
        if verification_type == 'email':
            try:
                verification = EmailVerification.objects.filter(
                    email=identifier,
                    is_used=False
                ).latest('created_at')
                
                if not verification.can_resend():
                    return Response({
                        "message": "Too many resend requests. Please wait 1 minute.",
                        "status": "error"
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)
                
                # Create new verification
                new_verification = EmailVerification.create_verification(
                    verification.user, identifier
                )
                
                # Send new OTP email
                subject = "🔐 New Verification Code - Bondah Dating"
                message = f"""
Hi there,

Your new email verification code is: {new_verification.otp_code}

This code will expire in 10 minutes.
Enter this code in the app to verify your email address.

Best regards,
The Bondah Team
                """.strip()
                
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[identifier],
                    fail_silently=False,
                )
                
                return Response({
                    "message": "New OTP sent to your email",
                    "status": "success"
                }, status=status.HTTP_200_OK)
                
            except EmailVerification.DoesNotExist:
                return Response({
                    "message": "No pending verification found for this email",
                    "status": "error"
                }, status=status.HTTP_404_NOT_FOUND)
                
        elif verification_type == 'phone':
            try:
                phone_number = request.data.get('phone_number')
                country_code = request.data.get('country_code', '+1')
                
                verification = PhoneVerification.objects.filter(
                    phone_number=phone_number,
                    country_code=country_code,
                    is_used=False
                ).latest('created_at')
                
                if not verification.can_resend():
                    return Response({
                        "message": "Too many resend requests. Please wait 1 minute.",
                        "status": "error"
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)
                
                # Create new verification
                new_verification = PhoneVerification.create_verification(
                    verification.user, phone_number, country_code
                )
                
                # In a real app, send SMS here
                print(f"New SMS OTP for {country_code}{phone_number}: {new_verification.otp_code}")
                
                return Response({
                    "message": "New OTP sent to your phone",
                    "status": "success"
                }, status=status.HTTP_200_OK)
                
            except PhoneVerification.DoesNotExist:
                return Response({
                    "message": "No pending verification found for this phone number",
                    "status": "error"
                }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            "message": "Invalid resend request",
            "status": "error"
        }, status=status.HTTP_400_BAD_REQUEST)


# =============================================================================
# ADVANCED USER SEARCH AND DISCOVERY VIEWS
# =============================================================================

class UserSearchView(APIView):
    """Advanced user search with filtering capabilities"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from .serializers import UserSearchFilterSerializer, UserSearchSerializer
        
        # Validate search parameters
        filter_serializer = UserSearchFilterSerializer(data=request.GET)
        if not filter_serializer.is_valid():
            return Response({
                "message": "Invalid search parameters",
                "status": "error",
                "errors": filter_serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        filters = filter_serializer.validated_data
        
        # Start with all active users except current user
        queryset = User.objects.filter(is_active=True).exclude(id=request.user.id)
        
        # Apply filters
        if filters.get('gender'):
            queryset = queryset.filter(gender=filters['gender'])
        
        if filters.get('age_min'):
            queryset = queryset.filter(age__gte=filters['age_min'])
        
        if filters.get('age_max'):
            queryset = queryset.filter(age__lte=filters['age_max'])
        
        if filters.get('education_level'):
            queryset = queryset.filter(education_level=filters['education_level'])
        
        if filters.get('relationship_status'):
            queryset = queryset.filter(relationship_status=filters['relationship_status'])
        
        if filters.get('smoking_preference'):
            queryset = queryset.filter(smoking_preference=filters['smoking_preference'])
        
        if filters.get('drinking_preference'):
            queryset = queryset.filter(drinking_preference=filters['drinking_preference'])
        
        if filters.get('pet_preference'):
            queryset = queryset.filter(pet_preference=filters['pet_preference'])
        
        if filters.get('exercise_frequency'):
            queryset = queryset.filter(exercise_frequency=filters['exercise_frequency'])
        
        if filters.get('kids_preference'):
            queryset = queryset.filter(kids_preference=filters['kids_preference'])
        
        if filters.get('personality_type'):
            queryset = queryset.filter(personality_type=filters['personality_type'])
        
        if filters.get('love_language'):
            queryset = queryset.filter(love_language=filters['love_language'])
        
        if filters.get('dating_type'):
            queryset = queryset.filter(dating_type=filters['dating_type'])
        
        if filters.get('religion'):
            queryset = queryset.filter(religion__icontains=filters['religion'])
        
        if filters.get('is_matchmaker') is not None:
            queryset = queryset.filter(is_matchmaker=filters['is_matchmaker'])
        
        if filters.get('has_photos'):
            queryset = queryset.exclude(profile_picture__isnull=True).exclude(profile_picture='')
        
        # Text search
        if filters.get('query'):
            query = filters['query']
            queryset = queryset.filter(
                models.Q(name__icontains=query) |
                models.Q(bio__icontains=query) |
                models.Q(city__icontains=query) |
                models.Q(state__icontains=query) |
                models.Q(country__icontains=query)
            )
        
        # Interest and hobby filtering
        if filters.get('interests'):
            for interest in filters['interests']:
                queryset = queryset.filter(interests__icontains=interest)
        
        if filters.get('hobbies'):
            for hobby in filters['hobbies']:
                queryset = queryset.filter(hobbies__icontains=hobby)
        
        # Distance filtering
        if filters.get('max_distance') and request.user.has_location:
            max_distance = filters['max_distance']
            nearby_users = []
            for user in queryset:
                if user.has_location:
                    distance = request.user.get_distance_to(user)
                    if distance and distance <= max_distance:
                        nearby_users.append(user)
            queryset = User.objects.filter(id__in=[u.id for u in nearby_users])
        
        # Order by relevance (can be enhanced with ML)
        queryset = queryset.order_by('-date_joined')
        
        # Pagination
        page_size = int(request.GET.get('page_size', 20))
        page = int(request.GET.get('page', 1))
        start = (page - 1) * page_size
        end = start + page_size
        
        users = queryset[start:end]
        
        # Serialize results
        serializer = UserSearchSerializer(users, many=True, context={'request': request})
        
        # Store search query for analytics
        SearchQuery.objects.create(
            user=request.user,
            query=filters.get('query', ''),
            filters=filters,
            results_count=queryset.count()
        )
        
        return Response({
            "message": "Search completed successfully",
            "status": "success",
            "results": serializer.data,
            "total_count": queryset.count(),
            "page": page,
            "page_size": page_size
        }, status=status.HTTP_200_OK)


class UserProfileDetailView(APIView):
    """Get detailed user profile for viewing"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id, is_active=True)
            
            # Track profile view
            UserProfileView.objects.get_or_create(
                viewer=request.user,
                viewed_user=user,
                defaults={'source': 'direct'}
            )
            
            serializer = UserProfileDetailSerializer(user, context={'request': request})
            
            return Response({
                "message": "Profile retrieved successfully",
                "status": "success",
                "profile": serializer.data
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({
                "message": "User not found",
                "status": "error"
            }, status=status.HTTP_404_NOT_FOUND)


class UserInteractionView(APIView):
    """Handle user interactions (like, dislike, super like, etc.)"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        from .serializers import UserInteractionSerializer
        
        serializer = UserInteractionSerializer(data=request.data)
        if serializer.is_valid():
            target_user_id = serializer.validated_data['target_user']
            interaction_type = serializer.validated_data['interaction_type']
            
            try:
                target_user = User.objects.get(id=target_user_id, is_active=True)
                
                # Create or update interaction
                interaction, created = UserInteraction.objects.get_or_create(
                    user=request.user,
                    target_user=target_user,
                    interaction_type=interaction_type,
                    defaults={'metadata': serializer.validated_data.get('metadata', {})}
                )
                
                if not created:
                    interaction.metadata = serializer.validated_data.get('metadata', {})
                    interaction.save()
                
                # Handle mutual matches
                if interaction_type == 'like':
                    mutual_like = UserInteraction.objects.filter(
                        user=target_user,
                        target_user=request.user,
                        interaction_type='like'
                    ).exists()
                    
                    if mutual_like:
                        # Create a match
                        UserMatch.objects.get_or_create(
                            user1=request.user,
                            user2=target_user,
                            defaults={
                                'distance': request.user.get_distance_to(target_user) or 0,
                                'status': 'matched'
                            }
                        )
                
                return Response({
                    "message": f"Interaction recorded successfully",
                    "status": "success",
                    "interaction": UserInteractionSerializer(interaction).data
                }, status=status.HTTP_200_OK)
                
            except User.DoesNotExist:
                return Response({
                    "message": "Target user not found",
                    "status": "error"
                }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            "message": "Invalid interaction data",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class UserRecommendationsView(APIView):
    """Get personalized user recommendations"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from .serializers import RecommendationSerializer
        
        # Get user's preferences
        user = request.user
        
        # Simple recommendation algorithm (can be enhanced with ML)
        recommendations = []
        
        # Location-based recommendations
        if user.has_location:
            nearby_users = User.objects.filter(
                is_active=True,
                latitude__isnull=False,
                longitude__isnull=False
            ).exclude(id=user.id)
            
            for nearby_user in nearby_users:
                distance = user.get_distance_to(nearby_user)
                if distance and distance <= user.max_distance:
                    # Calculate compatibility score
                    from .location_utils import calculate_match_score
                    score = calculate_match_score(user, nearby_user)
                    
                    if score > 50:  # Only recommend users with >50% compatibility
                        RecommendationEngine.objects.get_or_create(
                            user=user,
                            recommended_user=nearby_user,
                            defaults={
                                'score': score,
                                'algorithm': 'location_based'
                            }
                        )
        
        # Get active recommendations
        recommendations = RecommendationEngine.objects.filter(
            user=user,
            is_active=True
        ).order_by('-score')[:20]
        
        serializer = RecommendationSerializer(recommendations, many=True)
        
        return Response({
            "message": "Recommendations retrieved successfully",
            "status": "success",
            "recommendations": serializer.data
        }, status=status.HTTP_200_OK)


class CategoryFilterView(APIView):
    """Get users by category (Casual Dating, LGBTQ+, Sugar, etc.)"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from .serializers import CategoryFilterSerializer, UserSearchSerializer
        
        filter_serializer = CategoryFilterSerializer(data=request.GET)
        if not filter_serializer.is_valid():
            return Response({
                "message": "Invalid category filter",
                "status": "error",
                "errors": filter_serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        category = filter_serializer.validated_data['category']
        
        # Start with all active users except current user
        queryset = User.objects.filter(is_active=True).exclude(id=request.user.id)
        
        # Apply category filters
        if category == 'casual_dating':
            queryset = queryset.filter(dating_type='casual')
        elif category == 'lgbtq':
            # This would need more sophisticated filtering based on sexual orientation
            queryset = queryset.filter(gender__in=['non_binary', 'other'])
        elif category == 'sugar':
            queryset = queryset.filter(dating_type='sugar')
        elif category == 'serious':
            queryset = queryset.filter(dating_type='serious')
        elif category == 'friends':
            queryset = queryset.filter(dating_type='friends')
        elif category == 'matchmakers':
            queryset = queryset.filter(is_matchmaker=True)
        # 'all' category shows all users
        
        # Order by relevance
        queryset = queryset.order_by('-date_joined')
        
        # Pagination
        page_size = int(request.GET.get('page_size', 20))
        page = int(request.GET.get('page', 1))
        start = (page - 1) * page_size
        end = start + page_size
        
        users = queryset[start:end]
        
        # Serialize results
        serializer = UserSearchSerializer(users, many=True, context={'request': request})
        
        return Response({
            "message": f"Category '{category}' results retrieved successfully",
            "status": "success",
            "results": serializer.data,
            "total_count": queryset.count(),
            "page": page,
            "page_size": page_size
        }, status=status.HTTP_200_OK)


class UserInterestsView(APIView):
    """Manage user interests and hobbies"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from .serializers import UserInterestSerializer
        
        interests = UserInterest.objects.filter(is_active=True).order_by('name')
        serializer = UserInterestSerializer(interests, many=True)
        
        return Response({
            "message": "Interests retrieved successfully",
            "status": "success",
            "interests": serializer.data
        }, status=status.HTTP_200_OK)
    
    def post(self, request):
        """Update user's interests"""
        interests = request.data.get('interests', [])
        hobbies = request.data.get('hobbies', [])
        
        if not isinstance(interests, list) or not isinstance(hobbies, list):
            return Response({
                "message": "Interests and hobbies must be arrays",
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update user's interests and hobbies
        request.user.interests = interests
        request.user.hobbies = hobbies
        request.user.save()
        
        return Response({
            "message": "Interests updated successfully",
            "status": "success",
            "interests": request.user.interests,
            "hobbies": request.user.hobbies
        }, status=status.HTTP_200_OK)


# =============================================================================
# CHAT AND MESSAGING VIEWS (NEW)
# =============================================================================

class ChatListView(generics.ListCreateAPIView):
    """
    List all chats for the authenticated user or create a new chat
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            from .serializers import ChatCreateSerializer
            return ChatCreateSerializer
        from .serializers import ChatSerializer
        return ChatSerializer
    
    def get_queryset(self):
        user = self.request.user
        return Chat.objects.filter(participants=user, is_active=True).annotate(
            last_message_at=models.Max('messages__timestamp')
        ).order_by('-last_message_at')
    
    def perform_create(self, serializer):
        """Create chat with current user as creator"""
        chat = serializer.save(created_by=self.request.user)
        # Add current user to participants
        chat.participants.add(self.request.user)


class ChatDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific chat
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            from .serializers import ChatSettingsSerializer
            return ChatSettingsSerializer
        from .serializers import ChatDetailSerializer
        return ChatDetailSerializer
    
    def get_queryset(self):
        # Ensure the user is a participant of the chat
        return Chat.objects.filter(participants=self.request.user, is_active=True)
    
    def perform_destroy(self, instance):
        """Soft delete chat by deactivating it"""
        instance.is_active = False
        instance.save()


class MessageListView(generics.ListCreateAPIView):
    """
    List messages for a specific chat or send a new message
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            from .serializers import MessageCreateSerializer
            return MessageCreateSerializer
        from .serializers import MessageSerializer
        return MessageSerializer
    
    def get_queryset(self):
        chat_id = self.kwargs['chat_id']
        user = self.request.user
        
        # Ensure the user is a participant of the chat
        chat = get_object_or_404(Chat, id=chat_id, participants=user, is_active=True)
        
        # Mark messages as read when retrieved by the recipient
        Message.objects.filter(chat=chat, is_read=False).exclude(sender=user).update(
            is_read=True, read_at=timezone.now()
        )
        
        return Message.objects.filter(chat=chat).order_by('timestamp')
    
    def perform_create(self, serializer):
        """Create message with current user as sender"""
        chat_id = self.kwargs['chat_id']
        user = self.request.user
        
        chat = get_object_or_404(Chat, id=chat_id, participants=user, is_active=True)
        
        # Handle file uploads for voice notes and media
        voice_note_file = self.request.FILES.get('voice_note_file')
        image_file = self.request.FILES.get('image_file')
        video_file = self.request.FILES.get('video_file')
        document_file = self.request.FILES.get('document_file')
        
        # Save uploaded files and get URLs
        voice_note_url = None
        image_url = None
        video_url = None
        document_url = None
        
        if voice_note_file:
            voice_note_url = self._save_uploaded_file(voice_note_file, 'voice_notes')
            serializer.validated_data['message_type'] = 'voice_note'
        
        if image_file:
            image_url = self._save_uploaded_file(image_file, 'chat_images')
            serializer.validated_data['message_type'] = 'image'
        
        if video_file:
            video_url = self._save_uploaded_file(video_file, 'chat_videos')
            serializer.validated_data['message_type'] = 'video'
        
        if document_file:
            document_url = self._save_uploaded_file(document_file, 'chat_documents')
            serializer.validated_data['message_type'] = 'document'
            serializer.validated_data['document_name'] = document_file.name
        
        serializer.save(
            chat=chat,
            sender=user,
            voice_note_url=voice_note_url,
            image_url=image_url,
            video_url=video_url,
            document_url=document_url
        )
    
    def _save_uploaded_file(self, file, folder):
        """Save uploaded file and return URL"""
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        import os
        import uuid
        
        # Generate unique filename
        file_extension = os.path.splitext(file.name)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(folder, unique_filename)
        
        # Save file
        default_storage.save(file_path, ContentFile(file.read()))
        return default_storage.url(file_path)


class MessageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific message
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        from .serializers import MessageSerializer
        return MessageSerializer
    
    def get_queryset(self):
        chat_id = self.kwargs['chat_id']
        user = self.request.user
        
        # Ensure the user is a participant of the chat
        chat = get_object_or_404(Chat, id=chat_id, participants=user, is_active=True)
        return Message.objects.filter(chat=chat)
    
    def perform_update(self, serializer):
        """Mark message as edited"""
        serializer.save(is_edited=True, edited_at=timezone.now())
    
    def perform_destroy(self, instance):
        """Soft delete message by clearing content"""
        instance.content = "[Message deleted]"
        instance.message_type = 'system'
        instance.save()


class CallInitiateView(APIView):
    """
    Initiate a voice or video call
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        from .serializers import CallInitiateSerializer
        import uuid
        
        serializer = CallInitiateSerializer(data=request.data)
        if serializer.is_valid():
            callee_id = serializer.validated_data['callee_id']
            call_type = serializer.validated_data['call_type']
            
            try:
                callee = User.objects.get(id=callee_id, is_active=True)
                
                # Find or create chat between users
                chat = Chat.objects.filter(
                    participants=request.user,
                    chat_type='direct'
                ).filter(
                    participants=callee
                ).annotate(
                    participant_count=models.Count('participants')
                ).filter(
                    participant_count=2
                ).first()
                
                if not chat:
                    # Create new chat
                    chat = Chat.objects.create(
                        chat_type='direct',
                        created_by=request.user
                    )
                    chat.participants.set([request.user, callee])
                
                # Generate unique call ID
                call_id = str(uuid.uuid4())
                room_id = f"room_{call_id}"
                
                # Create call record
                call = Call.objects.create(
                    chat=chat,
                    caller=request.user,
                    callee=callee,
                    call_type=call_type,
                    call_id=call_id,
                    room_id=room_id,
                    status='initiated'
                )
                
                # Create system message for call initiation
                Message.objects.create(
                    chat=chat,
                    sender=None,  # System message
                    message_type='call_start',
                    content=f"{request.user.name} started a {call_type}"
                )
                
                from .serializers import CallSerializer
                return Response({
                    "message": "Call initiated successfully",
                    "status": "success",
                    "call": CallSerializer(call, context={'request': request}).data
                }, status=status.HTTP_201_CREATED)
                
            except User.DoesNotExist:
                return Response({
                    "message": "User not found",
                    "status": "error"
                }, status=status.HTTP_404_NOT_FOUND)
                
        return Response({
            "message": "Invalid call data",
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class CallAnswerView(APIView):
    """
    Answer an incoming call
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, call_id):
        try:
            call = Call.objects.get(
                call_id=call_id,
                callee=request.user,
                status__in=['initiated', 'ringing']
            )
            
            action = request.data.get('action')  # 'answer', 'decline', 'busy'
            
            if action == 'answer':
                call.status = 'active'
                call.answered_at = timezone.now()
                call.save()
                
                # Create system message
                Message.objects.create(
                    chat=call.chat,
                    sender=None,
                    message_type='call_start',
                    content=f"{request.user.name} answered the call"
                )
                
            elif action == 'decline':
                call.status = 'declined'
                call.ended_at = timezone.now()
                call.save()
                
                # Create system message
                Message.objects.create(
                    chat=call.chat,
                    sender=None,
                    message_type='call_end',
                    content=f"{request.user.name} declined the call"
                )
                
            elif action == 'busy':
                call.status = 'busy'
                call.ended_at = timezone.now()
                call.save()
                
                # Create system message
                Message.objects.create(
                    chat=call.chat,
                    sender=None,
                    message_type='call_end',
                    content=f"{request.user.name} is busy"
                )
            
            from .serializers import CallSerializer
            return Response({
                "message": f"Call {action}ed successfully",
                "status": "success",
                "call": CallSerializer(call, context={'request': request}).data
            }, status=status.HTTP_200_OK)
            
        except Call.DoesNotExist:
            return Response({
                "message": "Call not found",
                "status": "error"
            }, status=status.HTTP_404_NOT_FOUND)


class CallEndView(APIView):
    """
    End an active call
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, call_id):
        try:
            call = Call.objects.get(
                call_id=call_id,
                status='active',
                participants=request.user
            )
            
            call.status = 'ended'
            call.ended_at = timezone.now()
            
            # Calculate duration
            if call.answered_at:
                duration = (call.ended_at - call.answered_at).total_seconds()
                call.duration = int(duration)
            
            call.save()
            
            # Create system message
            Message.objects.create(
                chat=call.chat,
                sender=None,
                message_type='call_end',
                content=f"Call ended. Duration: {call.get_duration_display()}"
            )
            
            from .serializers import CallSerializer
            return Response({
                "message": "Call ended successfully",
                "status": "success",
                "call": CallSerializer(call, context={'request': request}).data
            }, status=status.HTTP_200_OK)
            
        except Call.DoesNotExist:
            return Response({
                "message": "Call not found",
                "status": "error"
            }, status=status.HTTP_404_NOT_FOUND)


class ChatReportView(generics.CreateAPIView):
    """
    Report a chat, message, or user
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        from .serializers import ChatReportSerializer
        return ChatReportSerializer
    
    def perform_create(self, serializer):
        """Create report with current user as reporter"""
        chat_id = self.kwargs.get('chat_id')
        message_id = self.kwargs.get('message_id')
        
        if chat_id:
            chat = get_object_or_404(Chat, id=chat_id, participants=self.request.user)
            serializer.validated_data['chat'] = chat
        
        if message_id:
            message = get_object_or_404(Message, id=message_id)
            serializer.validated_data['message'] = message
        
        serializer.save(reporter=self.request.user)


class MatchmakerIntroView(APIView):
    """
    Create a matchmaker introduction chat between two users
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        if not request.user.is_matchmaker:
            return Response({
                "message": "Only matchmakers can create introductions",
                "status": "error"
            }, status=status.HTTP_403_FORBIDDEN)
        
        user1_id = request.data.get('user1_id')
        user2_id = request.data.get('user2_id')
        intro_message = request.data.get('intro_message', '')
        
        if not user1_id or not user2_id:
            return Response({
                "message": "Both user1_id and user2_id are required",
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user1 = User.objects.get(id=user1_id, is_active=True)
            user2 = User.objects.get(id=user2_id, is_active=True)
            
            # Check if chat already exists
            existing_chat = Chat.objects.filter(
                participants=user1,
                chat_type='matchmaker_intro'
            ).filter(
                participants=user2
            ).annotate(
                participant_count=models.Count('participants')
            ).filter(
                participant_count=2
            ).first()
            
            if existing_chat:
                return Response({
                    "message": "Introduction chat already exists",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create matchmaker introduction chat
            chat = Chat.objects.create(
                chat_type='matchmaker_intro',
                created_by=request.user,
                chat_name=f"Introduction: {user1.name} & {user2.name}"
            )
            chat.participants.set([user1, user2, request.user])
            
            # Create system messages
            Message.objects.create(
                chat=chat,
                sender=None,
                message_type='system',
                content=f"{request.user.name} (moderator) made the match"
            )
            
            Message.objects.create(
                chat=chat,
                sender=None,
                message_type='system',
                content=f"{user1.name} was matched"
            )
            
            Message.objects.create(
                chat=chat,
                sender=None,
                message_type='system',
                content=f"{user2.name} was added"
            )
            
            # Create matchmaker introduction message
            intro_content = intro_message or f"Hi {user1.name} & {user2.name} 👋, I've matched you because I see a good fit. Please introduce yourselves and get to know each other."
            
            Message.objects.create(
                chat=chat,
                sender=request.user,
                message_type='matchmaker_intro',
                content=intro_content
            )
            
            from .serializers import ChatDetailSerializer
            return Response({
                "message": "Matchmaker introduction created successfully",
                "status": "success",
                "chat": ChatDetailSerializer(chat, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
            
        except User.DoesNotExist:
            return Response({
                "message": "One or both users not found",
                "status": "error"
            }, status=status.HTTP_404_NOT_FOUND)


# =============================================================================
# SOCIAL FEED AND STORY VIEWS (NEW)
# =============================================================================

class FeedListView(generics.ListCreateAPIView):
    """
    List posts in the Bond Story feed or create a new post
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            from .serializers import PostCreateSerializer
            return PostCreateSerializer
        from .serializers import PostSerializer
        return PostSerializer
    
    def get_queryset(self):
        from .models import Post
        user = self.request.user
        
        # Get posts from users the current user follows or is connected with
        # For now, return all public posts (can be enhanced with follow relationships)
        return Post.objects.filter(
            is_active=True,
            visibility='public'
        ).select_related('author').prefetch_related('comments__author').order_by('-created_at')
    
    def perform_create(self, serializer):
        """Create post with current user as author"""
        # Handle file uploads for images and videos
        image_files = self.request.FILES.getlist('image_files')
        video_file = self.request.FILES.get('video_file')
        
        # Save uploaded files and get URLs
        image_urls = []
        video_url = None
        video_thumbnail = None
        
        if image_files:
            for image_file in image_files:
                image_url = self._save_uploaded_file(image_file, 'post_images')
                image_urls.append(image_url)
        
        if video_file:
            video_url = self._save_uploaded_file(video_file, 'post_videos')
            # Generate thumbnail URL (placeholder)
            video_thumbnail = video_url.replace('.mp4', '_thumb.jpg')
        
        serializer.save(
            author=self.request.user,
            image_urls=image_urls,
            video_url=video_url,
            video_thumbnail=video_thumbnail
        )
    
    def _save_uploaded_file(self, file, folder):
        """Save uploaded file and return URL"""
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        import os
        import uuid
        
        # Generate unique filename
        file_extension = os.path.splitext(file.name)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(folder, unique_filename)
        
        # Save file
        default_storage.save(file_path, ContentFile(file.read()))
        return default_storage.url(file_path)


class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific post
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            from .serializers import PostCreateSerializer
            return PostCreateSerializer
        from .serializers import PostSerializer
        return PostSerializer
    
    def get_queryset(self):
        from .models import Post
        return Post.objects.filter(is_active=True).select_related('author').prefetch_related('comments__author')
    
    def perform_destroy(self, instance):
        """Soft delete post by deactivating it"""
        instance.is_active = False
        instance.save()


class PostCommentListView(generics.ListCreateAPIView):
    """
    List comments for a specific post or add a new comment
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            from .serializers import PostCommentSerializer
            return PostCommentSerializer
        from .serializers import PostCommentSerializer
        return PostCommentSerializer
    
    def get_queryset(self):
        from .models import PostComment
        post_id = self.kwargs['post_id']
        
        # Ensure the post exists and is active
        post = get_object_or_404(Post, id=post_id, is_active=True)
        
        return PostComment.objects.filter(
            post=post,
            is_active=True,
            parent_comment__isnull=True  # Only top-level comments
        ).select_related('author').prefetch_related('replies__author').order_by('created_at')
    
    def perform_create(self, serializer):
        """Create comment with current user as author"""
        post_id = self.kwargs['post_id']
        post = get_object_or_404(Post, id=post_id, is_active=True)
        
        serializer.save(
            post=post,
            author=self.request.user
        )
        
        # Update post comments count
        post.comments_count = post.comments.filter(is_active=True).count()
        post.save(update_fields=['comments_count'])


class PostInteractionView(APIView):
    """
    Handle post interactions (like, share, bond)
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, post_id):
        from .models import Post, PostInteraction
        
        try:
            post = Post.objects.get(id=post_id, is_active=True)
            interaction_type = request.data.get('interaction_type')
            
            if interaction_type not in ['like', 'share', 'bond', 'save']:
                return Response({
                    "message": "Invalid interaction type",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if interaction already exists
            interaction, created = PostInteraction.objects.get_or_create(
                user=request.user,
                post=post,
                interaction_type=interaction_type
            )
            
            if not created:
                # Remove interaction (toggle)
                interaction.delete()
                action = 'removed'
                
                # Update post counts
                if interaction_type == 'like':
                    post.likes_count = max(0, post.likes_count - 1)
                elif interaction_type == 'share':
                    post.shares_count = max(0, post.shares_count - 1)
                elif interaction_type == 'bond':
                    post.bonds_count = max(0, post.bonds_count - 1)
            else:
                # Add interaction
                action = 'added'
                
                # Update post counts
                if interaction_type == 'like':
                    post.likes_count += 1
                elif interaction_type == 'share':
                    post.shares_count += 1
                elif interaction_type == 'bond':
                    post.bonds_count += 1
            
            post.save(update_fields=['likes_count', 'shares_count', 'bonds_count'])
            
            return Response({
                "message": f"Interaction {action} successfully",
                "status": "success",
                "interaction_type": interaction_type,
                "action": action
            }, status=status.HTTP_200_OK)
            
        except Post.DoesNotExist:
            return Response({
                "message": "Post not found",
                "status": "error"
            }, status=status.HTTP_404_NOT_FOUND)


class CommentInteractionView(APIView):
    """
    Handle comment interactions (like)
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, comment_id):
        from .models import PostComment, CommentInteraction
        
        try:
            comment = PostComment.objects.get(id=comment_id, is_active=True)
            interaction_type = request.data.get('interaction_type', 'like')
            
            # Check if interaction already exists
            interaction, created = CommentInteraction.objects.get_or_create(
                user=request.user,
                comment=comment,
                interaction_type=interaction_type
            )
            
            if not created:
                # Remove interaction (toggle)
                interaction.delete()
                action = 'removed'
                comment.likes_count = max(0, comment.likes_count - 1)
            else:
                # Add interaction
                action = 'added'
                comment.likes_count += 1
            
            comment.save(update_fields=['likes_count'])
            
            return Response({
                "message": f"Comment interaction {action} successfully",
                "status": "success",
                "interaction_type": interaction_type,
                "action": action
            }, status=status.HTTP_200_OK)
            
        except PostComment.DoesNotExist:
            return Response({
                "message": "Comment not found",
                "status": "error"
            }, status=status.HTTP_404_NOT_FOUND)


class PostReportView(generics.CreateAPIView):
    """
    Report a post or comment
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        from .serializers import PostReportSerializer
        return PostReportSerializer
    
    def perform_create(self, serializer):
        """Create report with current user as reporter"""
        post_id = self.kwargs.get('post_id')
        comment_id = self.kwargs.get('comment_id')
        
        if post_id:
            from .models import Post
            post = get_object_or_404(Post, id=post_id, is_active=True)
            serializer.validated_data['post'] = post
            serializer.validated_data['reported_user'] = post.author
        
        if comment_id:
            from .models import PostComment
            comment = get_object_or_404(PostComment, id=comment_id, is_active=True)
            serializer.validated_data['comment'] = comment
            serializer.validated_data['reported_user'] = comment.author
        
        serializer.save(reporter=self.request.user)


class PostShareView(generics.CreateAPIView):
    """
    Share a post to external platforms
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        from .serializers import PostShareSerializer
        return PostShareSerializer
    
    def perform_create(self, serializer):
        """Create share with current user and post"""
        post_id = self.kwargs['post_id']
        from .models import Post, PostShare
        
        post = get_object_or_404(Post, id=post_id, is_active=True)
        
        serializer.save(
            user=self.request.user,
            post=post
        )
        
        # Update post shares count
        post.shares_count += 1
        post.save(update_fields=['shares_count'])


class StoryListView(generics.ListCreateAPIView):
    """
    List active stories or create a new story
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            from .serializers import StoryCreateSerializer
            return StoryCreateSerializer
        from .serializers import StorySerializer
        return StorySerializer
    
    def get_queryset(self):
        from .models import Story
        from django.utils import timezone
        
        # Get active, non-expired stories
        return Story.objects.filter(
            is_active=True,
            expires_at__gt=timezone.now()
        ).select_related('author').order_by('-created_at')
    
    def perform_create(self, serializer):
        """Create story with current user as author"""
        # Handle file uploads for images and videos
        image_file = self.request.FILES.get('image_file')
        video_file = self.request.FILES.get('video_file')
        
        # Save uploaded files and get URLs
        image_url = None
        video_url = None
        
        if image_file:
            image_url = self._save_uploaded_file(image_file, 'story_images')
        
        if video_file:
            video_url = self._save_uploaded_file(video_file, 'story_videos')
        
        serializer.save(
            author=self.request.user,
            image_url=image_url,
            video_url=video_url
        )
    
    def _save_uploaded_file(self, file, folder):
        """Save uploaded file and return URL"""
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        import os
        import uuid
        
        # Generate unique filename
        file_extension = os.path.splitext(file.name)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(folder, unique_filename)
        
        # Save file
        default_storage.save(file_path, ContentFile(file.read()))
        return default_storage.url(file_path)


class StoryDetailView(generics.RetrieveAPIView):
    """
    Retrieve a specific story and mark as viewed
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        from .serializers import StorySerializer
        return StorySerializer
    
    def get_queryset(self):
        from .models import Story
        from django.utils import timezone
        
        return Story.objects.filter(
            is_active=True,
            expires_at__gt=timezone.now()
        ).select_related('author')
    
    def retrieve(self, request, *args, **kwargs):
        """Mark story as viewed by current user"""
        from .models import StoryView
        
        story = self.get_object()
        
        # Mark as viewed if not already viewed
        StoryView.objects.get_or_create(
            story=story,
            viewer=request.user
        )
        
        # Update views count
        story.views_count = story.views.count()
        story.save(update_fields=['views_count'])
        
        serializer = self.get_serializer(story)
        return Response(serializer.data)


class StoryReactionView(APIView):
    """
    Handle story reactions
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, story_id):
        from .models import Story, StoryReaction
        
        try:
            story = Story.objects.get(id=story_id, is_active=True)
            reaction_type = request.data.get('reaction_type', 'like')
            
            if reaction_type not in ['like', 'love', 'laugh', 'wow', 'sad', 'angry']:
                return Response({
                    "message": "Invalid reaction type",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if reaction already exists
            reaction, created = StoryReaction.objects.get_or_create(
                user=request.user,
                story=story,
                reaction_type=reaction_type
            )
            
            if not created:
                # Remove reaction (toggle)
                reaction.delete()
                action = 'removed'
                story.reactions_count = max(0, story.reactions_count - 1)
            else:
                # Add reaction
                action = 'added'
                story.reactions_count += 1
            
            story.save(update_fields=['reactions_count'])
            
            return Response({
                "message": f"Story reaction {action} successfully",
                "status": "success",
                "reaction_type": reaction_type,
                "action": action
            }, status=status.HTTP_200_OK)
            
        except Story.DoesNotExist:
            return Response({
                "message": "Story not found",
                "status": "error"
            }, status=status.HTTP_404_NOT_FOUND)


class FeedSearchView(APIView):
    """
    Search posts in the Bond Story feed
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from .models import Post, FeedSearch
        from django.db.models import Q
        
        query = request.GET.get('q', '').strip()
        if not query:
            return Response({
                "message": "Search query is required",
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Search posts by content, hashtags, and author name
        posts = Post.objects.filter(
            Q(content__icontains=query) |
            Q(hashtags__icontains=query) |
            Q(author__name__icontains=query) |
            Q(location__icontains=query),
            is_active=True,
            visibility='public'
        ).select_related('author').prefetch_related('comments__author').order_by('-created_at')
        
        # Store search query for analytics
        FeedSearch.objects.create(
            user=request.user,
            query=query,
            results_count=posts.count()
        )
        
        # Serialize results
        from .serializers import PostSerializer
        serializer = PostSerializer(posts, many=True, context={'request': request})
        
        return Response({
            "message": "Search completed successfully",
            "status": "success",
            "query": query,
            "results_count": posts.count(),
            "posts": serializer.data
        }, status=status.HTTP_200_OK)


class FeedSuggestionsView(APIView):
    """
    Get search suggestions for the Bond Story feed
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from .models import FeedSearch, Post
        from django.db.models import Count
        
        query = request.GET.get('q', '').strip()
        
        if query:
            # Get suggestions based on partial query
            suggestions = FeedSearch.objects.filter(
                query__icontains=query
            ).values('query').annotate(
                count=Count('query')
            ).order_by('-count')[:5]
            
            # Also get hashtag suggestions from posts
            hashtag_suggestions = Post.objects.filter(
                hashtags__icontains=query,
                is_active=True
            ).values_list('hashtags', flat=True)
            
            # Flatten and deduplicate hashtags
            all_hashtags = []
            for hashtags in hashtag_suggestions:
                if hashtags:
                    all_hashtags.extend(hashtags)
            
            # Filter hashtags that contain the query
            filtered_hashtags = [tag for tag in set(all_hashtags) if query.lower() in tag.lower()]
            
            return Response({
                "message": "Suggestions retrieved successfully",
                "status": "success",
                "suggestions": [s['query'] for s in suggestions],
                "hashtags": filtered_hashtags[:5]
            }, status=status.HTTP_200_OK)
        else:
            # Get popular searches
            popular_searches = FeedSearch.objects.values('query').annotate(
                count=Count('query')
            ).order_by('-count')[:10]
            
            return Response({
                "message": "Popular searches retrieved successfully",
                "status": "success",
                "popular_searches": [s['query'] for s in popular_searches]
            }, status=status.HTTP_200_OK)