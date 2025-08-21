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
from .models import NewsletterSubscriber, PuzzleVerification, CoinTransaction, Waitlist, EmailLog, Job, JobApplication, AdminUser, AdminOTP, TranslationLog
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
    SupportedLanguagesSerializer
)
import time
from deep_translator import GoogleTranslator
from django.db import models

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
    queryset = Waitlist.objects.all()
    serializer_class = WaitlistSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Check if email already exists
            email = serializer.validated_data.get('email')
            first_name = serializer.validated_data.get('firstName', '')
            last_name = serializer.validated_data.get('lastName', '')
            
            if Waitlist.objects.filter(email=email).exists():
                return Response({
                    "message": "Email already registered on waitlist",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Save the waitlist entry
            waitlist_entry = serializer.save()
            
            # Send automatic confirmation email
            subject = f"You're on the Bondah Waitlist, {first_name}! ⏳"
            message = f"""
Hi {first_name} {last_name},

Great news! You've successfully joined the Bondah Dating waitlist.

Your spot is reserved, and we'll notify you as soon as:
• Our platform launches
• Early access becomes available
• Special features are ready
• Exclusive beta testing opportunities

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
                
            except Exception as e:
                email_log.is_sent = False
                email_log.error_message = str(e)
                email_log.save()
                # Don't fail the signup if email fails
            
            # Return success response
            return Response({
                "message": "You've successfully joined the waitlist! Confirmation email sent.",
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


class JobApplicationView(generics.CreateAPIView):
    serializer_class = JobApplicationSerializer

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                # Get the job
                job_id = serializer.validated_data.get('job', {}).get('id')
                job = Job.objects.get(id=job_id)
                
                # Get applicant details
                applicant_email = serializer.validated_data.get('email', '')
                applicant_name = serializer.validated_data.get('name', '')
                
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
                        send_mail(
                            subject=subject,
                            message=message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[email],
                            fail_silently=False,
                        )
                        
                        return Response({
                            "message": "OTP sent to your email",
                            "status": "success"
                        }, status=status.HTTP_200_OK)
                    except Exception as e:
                        return Response({
                            "message": f"Failed to send OTP: {str(e)}",
                            "status": "error"
                        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
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
                
                return Response({
                    "message": "Login successful",
                    "status": "success",
                    "admin_email": admin_user.email
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