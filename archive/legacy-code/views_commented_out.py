"""
Commented-out code removed from dating/views.py when it was split into a package.
Kept for reference only; nothing imports this file.
"""

# ============================================================================
# module header (commented-out imports etc.)
# ============================================================================

# from .location_utils import find_nearby_users, get_location_statistics
# from .integrations.firebase import (
#     verify_firebase_token,
#     get_or_create_user_from_firebase,
#     get_user_profile_from_firestore,
#     update_user_profile_in_firestore,
#     create_match_in_firestore,
#     send_push_notification,
#     get_matches_for_user,
# )


User = get_user_model()
logger = logging.getLogger(__name__)


# class UserCreateView(generics.CreateAPIView):
#     queryset = User.objects.all()
#     serializer_class = CustomRegisterSerializer

#     def create(self, request, *args, **kwargs):
#         try:
#             return super().create(request, *args, **kwargs)
#         except Exception as e:
#             return Response(
#                 {"message": f"User creation failed: {str(e)}", "status": "error"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )


# ============================================================================
# before AdminLoginView (original lines 660-1096)
# ============================================================================


# ------------------------------
# EarnCoinsView
# ------------------------------
# class EarnCoinsView(generics.GenericAPIView):
#     serializer_class = EarnCoinsRequestSerializer

#     @extend_schema(
#         request=EarnCoinsRequestSerializer,
#         responses={201: WalletTransactionSerializer},
#     )
#     def post(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         user_id = serializer.validated_data["user_id"]
#         amount = serializer.validated_data["amount"]

#         try:
#             user = User.objects.get(id=user_id)
#         except User.DoesNotExist:
#             return Response({"error": "User not found."}, status=404)

#         if not has_solved_puzzle(user):
#             return Response(
#                 {"error": "You must solve a puzzle before earning coins."},
#                 status=403,
#             )

#         transaction = WalletTransaction.objects.create(
#             user=user, tx_type="credit", amount=amount
#         )

#         return Response(WalletTransactionSerializer(transaction).data, status=201)


# # ------------------------------
# # SpendCoinsView
# # ------------------------------
# class SpendCoinsView(generics.GenericAPIView):
#     serializer_class = SpendCoinsRequestSerializer

#     @extend_schema(
#         request=SpendCoinsRequestSerializer,
#         responses={201: WalletTransactionSerializer},
#     )
#     def post(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         user_id = serializer.validated_data["user_id"]
#         amount = serializer.validated_data["amount"]

#         try:
#             user = User.objects.get(id=user_id)
#         except User.DoesNotExist:
#             return Response({"error": "User not found."}, status=404)

#         if not has_solved_puzzle(user):
#             return Response(
#                 {"error": "You must solve a puzzle before spending coins."},
#                 status=403,
#             )

#         # calculate balance
#         total_earned = (
#             WalletTransaction.objects.filter(
#                 user=user, tx_type="credit"
#             ).aggregate(total=Sum("amount"))["total"]
#             or 0
#         )
#         total_spent = (
#             WalletTransaction.objects.filter(
#                 user=user, tx_type="debit"
#             ).aggregate(total=Sum("amount"))["total"]
#             or 0
#         )

#         balance = total_earned - total_spent
#         if amount > balance:
#             return Response({"error": "Insufficient coin balance."}, status=400)

#         transaction = WalletTransaction.objects.create(
#             user=user, tx_type="debit", amount=amount
#         )

#         return Response(WalletTransactionSerializer(transaction).data, status=201)


# class JobListView(generics.ListAPIView):
#     serializer_class = JobListSerializer
#     queryset = Job.objects.all()

#     def get_queryset(self):
#         queryset = super().get_queryset().filter(status="open")

#         job_type = self.request.query_params.get("jobType")
#         category = self.request.query_params.get("category")
#         status_param = self.request.query_params.get("status")

#         if job_type:
#             queryset = queryset.filter(job_type=job_type)
#         if category:
#             queryset = queryset.filter(category=category)
#         if status_param:
#             queryset = queryset.filter(status=status_param)

#         return queryset

#     def list(self, request, *args, **kwargs):
#         try:
#             return super().list(request, *args, **kwargs)
#         except Exception as e:
#             return Response(
#                 {"status": "error", "message": f"Failed to retrieve jobs: {str(e)}"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )


# class JobDetailView(generics.RetrieveAPIView):
#     queryset = Job.objects.all()
#     serializer_class = JobDetailSerializer
#     lookup_field = "id"

#     def retrieve(self, request, *args, **kwargs):
#         try:
#             return super().retrieve(request, *args, **kwargs)
#         except Exception as e:
#             return Response(
#                 {"message": f"Failed to retrieve job: {str(e)}", "status": "error"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )


# class JobApplicationView(generics.CreateAPIView):
#     serializer_class = JobApplicationSerializer

#     def create(self, request, *args, **kwargs):
#         try:
#             # Handle both DRF request and regular Django request
#             if hasattr(request, "data"):
#                 data = request.data
#             else:
#                 # For regular Django request, parse JSON from body
#                 import json

#                 data = json.loads(request.body.decode("utf-8")) if request.body else {}

#             serializer = self.get_serializer(data=data)
#             if serializer.is_valid():
#                 # Get the job
#                 job_id = serializer.validated_data.get("job", {}).get("id")
#                 job = Job.objects.get(id=job_id)

#                 # Get applicant details
#                 applicant_email = serializer.validated_data.get("email", "")
#                 first_name = serializer.validated_data.get("first_name", "")
#                 last_name = serializer.validated_data.get("last_name", "")
#                 applicant_name = f"{first_name} {last_name}".strip()

#                 # Create the application
#                 application = serializer.save(job=job)

#                 # Send automatic confirmation email
#                 subject = f"Application Received - {job.title} at Bondah Dating"
#                 message = f"""
# Hi {applicant_name},

# Thank you for your interest in joining the Bondah Dating team!

# We've received your application for the {job.title} position and are excited to review your qualifications.

# What happens next:
# • Our team will review your application within 3-5 business days
# • If selected, we'll contact you for the next steps
# • You'll receive updates on your application status

# Application Details:
# • Position: {job.title}
# • Application ID: {application.id}
# • Applied: {application.applied_at.strftime('%B %d, %Y')}

# We appreciate your interest in helping us build the future of dating!

# Best regards,
# The Bondah Team

# P.S. Follow us on social media to stay updated on our journey!
#                 """.strip()

#                 # Log email attempt
#                 email_log = EmailLog.objects.create(
#                     email_type="job_application_confirmation",
#                     recipient_email=applicant_email,
#                     subject=subject,
#                     message=message,
#                 )

#                 try:
#                     # Send email using Django's email functionality
#                     send_mail(
#                         subject=subject,
#                         message=message,
#                         from_email=settings.DEFAULT_FROM_EMAIL,
#                         recipient_list=[applicant_email],
#                         fail_silently=False,
#                     )

#                     email_log.is_sent = True
#                     email_log.save()

#                 except Exception as e:
#                     email_log.is_sent = False
#                     email_log.error_message = str(e)
#                     email_log.save()
#                     # Don't fail the application if email fails

#                 # Return success response
#                 return Response(
#                     {
#                         "message": "Job application submitted successfully! Confirmation email sent.",
#                         "status": "success",
#                         "applicationId": application.id,
#                     },
#                     status=status.HTTP_201_CREATED,
#                 )

#             return Response(
#                 {
#                     "message": "Invalid application data",
#                     "status": "error",
#                     "errors": serializer.errors,
#                 },
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         except Job.DoesNotExist:
#             return Response(
#                 {"message": "Job not found", "status": "error"},
#                 status=status.HTTP_404_NOT_FOUND,
#             )
#         except Exception as e:
#             return Response(
#                 {"message": f"Application failed: {str(e)}", "status": "error"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )


# class AdminJobListView(generics.ListAPIView):
#     queryset = Job.objects.all()
#     serializer_class = AdminJobListSerializer

#     @extend_schema(
#         responses={200: AdminJobListSerializer(many=True)},
#         description="List all jobs with summary information.",
#     )
#     def get(self, request, *args, **kwargs):
#         return super().get(request, *args, **kwargs)


# class AdminJobCreateView(generics.CreateAPIView):
#     queryset = Job.objects.all()
#     serializer_class = AdminJobCreateSerializer

#     @extend_schema(
#         request=AdminJobCreateSerializer,
#         responses={201: AdminJobCreateSerializer, 400: SimpleStatusResponseSerializer},
#         description="Create a new job posting.",
#     )
#     def post(self, request, *args, **kwargs):
#         return super().post(request, *args, **kwargs)


# class AdminJobUpdateView(generics.UpdateAPIView):
#     queryset = Job.objects.all()
#     serializer_class = AdminJobUpdateSerializer

#     @extend_schema(
#         request=AdminJobUpdateSerializer,
#         responses={200: AdminJobUpdateSerializer, 400: SimpleStatusResponseSerializer},
#         description="Update an existing job posting.",
#     )
#     def put(self, request, *args, **kwargs):
#         return super().put(request, *args, **kwargs)


# class AdminJobApplicationsView(GenericAPIView):
#     serializer_class = AdminJobApplicationSerializer

#     @extend_schema(
#         responses={200: AdminJobApplicationSerializer(many=True)},
#         description="Retrieve job applications with optional filters",
#     )
#     def get(self, request, *args, **kwargs):
#         job_id = request.query_params.get("job_id")
#         status_filter = request.query_params.get("status")

#         applications = JobApplication.objects.all().order_by("-applied_at")
#         if job_id:
#             applications = applications.filter(job_id=job_id)
#         if status_filter:
#             applications = applications.filter(status=status_filter)

#         serializer = self.get_serializer(applications, many=True)
#         return Response(
#             {
#                 "message": "Applications retrieved successfully",
#                 "status": "success",
#                 "applications": serializer.data,
#             }
#         )


# class AdminUpdateApplicationStatusView(GenericAPIView):
#     serializer_class = AdminUpdateApplicationStatusSerializer

#     @extend_schema(
#         request=AdminUpdateApplicationStatusSerializer,
#         responses={200: AdminJobApplicationSerializer},
#         description="Update the status of a specific job application",
#     )
#     def put(self, request, application_id, *args, **kwargs):
#         try:
#             application = JobApplication.objects.get(id=application_id)

#             serializer = self.get_serializer(data=request.data)
#             serializer.is_valid(raise_exception=True)

#             application.status = serializer.validated_data["status"]
#             application.save()

#             return Response(
#                 {
#                     "message": "Application status updated successfully",
#                     "status": "success",
#                     "application": AdminJobApplicationSerializer(application).data,
#                 },
#                 status=status.HTTP_200_OK,
#             )

#         except JobApplication.DoesNotExist:
#             return Response(
#                 {"message": "Application not found", "status": "error"},
#                 status=status.HTTP_404_NOT_FOUND,
#             )
#         except Exception as e:
#             return Response(
#                 {
#                     "message": f"Failed to update application status: {str(e)}",
#                     "status": "error",
#                 },
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )


# class AdminJobApplicationDetailView(GenericAPIView):
#     serializer_class = AdminJobApplicationDetailSerializer

#     @extend_schema(
#         responses={200: AdminJobApplicationDetailSerializer},
#         description="Retrieve detailed information of a specific job application",
#     )
#     def get(self, request, application_id, *args, **kwargs):
#         """Get detailed view of a specific job application"""
#         try:
#             application = JobApplication.objects.get(id=application_id)
#             serializer = self.get_serializer(application)
#             return Response(
#                 {
#                     "message": "Application details retrieved successfully",
#                     "status": "success",
#                     "application": serializer.data,
#                 },
#                 status=status.HTTP_200_OK,
#             )
#         except JobApplication.DoesNotExist:
#             return Response(
#                 {"message": "Application not found", "status": "error"},
#                 status=status.HTTP_404_NOT_FOUND,
#             )
#         except Exception as e:
#             return Response(
#                 {
#                     "message": f"Failed to retrieve application details: {str(e)}",
#                     "status": "error",
#                 },
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )


# @extend_schema(
#     responses={200: OpenApiTypes.OBJECT},
#     description="Debug endpoint to check authentication status",
# )
# class AdminDebugAuthView(GenericAPIView):
#     permission_classes = [AllowAny]

#     def get(self, request, *args, **kwargs):
#         auth_header = request.headers.get("Authorization")
#         debug_info = {
#             "has_authorization_header": bool(auth_header),
#             "authorization_header": auth_header,
#             "all_headers": dict(request.headers),
#         }

#         if auth_header:
#             if auth_header.startswith("Bearer "):
#                 token = auth_header.split(" ")[1]
#                 debug_info["token_length"] = len(token) if token else 0
#                 debug_info["token_format"] = "Valid Bearer format"
#                 try:
#                     from .jwt_utils import verify_token

#                     payload = verify_token(token, "access")
#                     debug_info["token_valid"] = True
#                     debug_info["token_payload"] = payload
#                 except Exception as e:
#                     debug_info["token_valid"] = False
#                     debug_info["token_error"] = str(e)
#             else:
#                 debug_info["token_format"] = (
#                     "Invalid format - should start with 'Bearer '"
#                 )
#         else:
#             debug_info["token_format"] = "No Authorization header"

#         return Response(
#             {
#                 "message": "Debug authentication info",
#                 "status": "success",
#                 "debug_info": debug_info,
#             },
#             status=status.HTTP_200_OK,
#         )



# ============================================================================
# before UserProfileDetailView (original lines 3192-3285)
# ============================================================================


# =============================================================================
# ADVANCED USER SEARCH AND DISCOVERY VIEWS
# =============================================================================


# class UserSearchView(generics.ListAPIView):
#     permission_classes = [IsAuthenticated]
#     serializer_class = UserSearchSerializer  # Output serializer
#     # pagination_class = CustomPagination

#     @extend_schema(
#         request=UserSearchFilterSerializer,
#         responses={200: UserSearchSerializer(many=True)},
#     )
#     def get_queryset(self):

#         filter_serializer = UserSearchFilterSerializer(data=self.request.GET)
#         filter_serializer.is_valid(raise_exception=True)
#         filters = filter_serializer.validated_data

#         queryset = User.objects.filter(is_active=True).exclude(id=self.request.user.id)

#         # Apply dynamic filters
#         filter_map = {
#             "gender": "gender",
#             "age_min": "age__gte",
#             "age_max": "age__lte",
#             "education_level": "education_level",
#             "relationship_status": "relationship_status",
#             "smoking_preference": "smoking_preference",
#             "drinking_preference": "drinking_preference",
#             "pet_preference": "pet_preference",
#             "exercise_frequency": "exercise_frequency",
#             "kids_preference": "kids_preference",
#             "personality_type": "personality_type",
#             "love_language": "love_language",
#             "dating_type": "dating_type",
#         }

#         for key, field in filter_map.items():
#             if filters.get(key):
#                 queryset = queryset.filter(**{field: filters[key]})

#         if filters.get("religion"):
#             queryset = queryset.filter(religion__icontains=filters["religion"])
#         if filters.get("is_matchmaker") is not None:
#             queryset = queryset.filter(is_matchmaker=filters["is_matchmaker"])
#         if filters.get("has_photos"):
#             queryset = queryset.exclude(profile_picture__isnull=True).exclude(
#                 profile_picture=""
#             )

#         # Text search
#         if filters.get("query"):
#             q = filters["query"]
#             queryset = queryset.filter(
#                 models.Q(name__icontains=q)
#                 | models.Q(bio__icontains=q)
#                 | models.Q(city__icontains=q)
#                 | models.Q(state__icontains=q)
#                 | models.Q(country__icontains=q)
#             )

#         # Interests & hobbies
#         for field in ["interests", "hobbies"]:
#             if filters.get(field):
#                 for value in filters[field]:
#                     queryset = queryset.filter(**{f"{field}__icontains": value})

#         # Distance filtering
#         if filters.get("max_distance") and self.request.user.has_location:
#             max_distance = filters["max_distance"]
#             nearby_ids = [
#                 u.id
#                 for u in queryset
#                 if u.has_location
#                 and self.request.user.get_distance_to(u) <= max_distance
#             ]
#             queryset = queryset.filter(id__in=nearby_ids)

#         queryset = queryset.order_by("-date_joined")

#         # Optional: Store search query for analytics
#         SearchQuery.objects.create(
#             user=self.request.user,
#             query=filters.get("query", ""),
#             filters=filters,
#             results_count=queryset.count(),
#         )

#         return queryset


# ============================================================================
# before UserInterestsView (original lines 3343-3416)
# ============================================================================


# class UserRecommendationsView(generics.ListAPIView):
#     permission_classes = [IsAuthenticated]
#     serializer_class = RecommendationSerializer

#     def get_queryset(self):
#         user = self.request.user

#         if user.has_location:
#             nearby_users = User.objects.filter(
#                 is_active=True, latitude__isnull=False, longitude__isnull=False
#             ).exclude(id=user.id)
#             for nearby_user in nearby_users:
#                 distance = user.get_distance_to(nearby_user)
#                 if distance and distance <= user.max_distance:
#                     from .location_utils import calculate_match_score

#                     score = calculate_match_score(user, nearby_user)
#                     if score > 50:
#                         RecommendationEngine.objects.get_or_create(
#                             user=user,
#                             recommended_user=nearby_user,
#                             defaults={"score": score, "algorithm": "location_based"},
#                         )

#         return RecommendationEngine.objects.filter(user=user, is_active=True).order_by(
#             "-score"
#         )[:20]


# class CategoryFilterView(generics.ListAPIView):
#     permission_classes = [IsAuthenticated]
#     serializer_class = UserSearchSerializer  # Output serializer

#     @extend_schema(
#         request=None,
#         responses=UserSearchSerializer(many=True),
#         parameters=[
#             OpenApiParameter(
#                 name="category",
#                 type=str,
#                 required=True,
#                 description="User category to filter",
#             ),
#             OpenApiParameter(name="page", type=int, required=False),
#             OpenApiParameter(name="page_size", type=int, required=False),
#         ],
#     )
#     def get_queryset(self):
#         from .serializers import CategoryFilterSerializer

#         filter_serializer = CategoryFilterSerializer(data=self.request.GET)
#         filter_serializer.is_valid(raise_exception=True)
#         category = filter_serializer.validated_data["category"]

#         queryset = User.objects.filter(is_active=True).exclude(id=self.request.user.id)

#         category_map = {
#             "casual_dating": {"dating_type": "casual"},
#             "lgbtq": {"gender__in": ["non_binary", "other"]},
#             "sugar": {"dating_type": "sugar"},
#             "serious": {"dating_type": "serious"},
#             "friends": {"dating_type": "friends"},
#             "matchmakers": {"is_matchmaker": True},
#             "all": {},
#         }

#         filters = category_map.get(category, {})
#         if filters:
#             queryset = queryset.filter(**filters)

#         return queryset.order_by("-date_joined")


# ============================================================================
# before PostViewSet (original lines 3674-4311)
# ============================================================================
        

    

# class ChatListView(generics.ListCreateAPIView):
#     """
#     List all chats for the authenticated user or create a new chat.
#     """

#     permission_classes = [IsAuthenticated]

#     def get_serializer_class(self):
#         if self.request.method == "POST":
#             return ChatCreateSerializer
#         return ChatSerializer

#     def get_queryset(self):
#         user = self.request.user
#         return (
#             Chat.objects.filter(participants=user, is_active=True)
#             .annotate(last_message_at=models.Max("messages__timestamp"))
#             .order_by("-last_message_at")
#         )

#     def perform_create(self, serializer):
#         chat = serializer.save(created_by=self.request.user)
#         chat.participants.add(self.request.user)


# class ChatDetailView(generics.RetrieveUpdateDestroyAPIView):
#     """
#     Retrieve, update, or soft delete a specific chat.
#     """

#     permission_classes = [IsAuthenticated]

#     def get_serializer_class(self):
#         if self.request.method in ["PUT", "PATCH"]:
#             return ChatSettingsSerializer
#         return ChatDetailSerializer

#     def get_queryset(self):
#         return Chat.objects.filter(participants=self.request.user, is_active=True)

#     def perform_destroy(self, instance):
#         instance.is_active = False
#         instance.save()


# # --------------------------
# # Message Views
# # --------------------------
# class MessageListView(generics.ListCreateAPIView):
#     """
#     List messages for a chat or send a new message (supports media and tips).
#     """

#     permission_classes = [IsAuthenticated]
#     parser_classes = [MultiPartParser, FormParser]

#     def get_serializer_class(self):
#         if self.request.method == "POST":
#             return MessageCreateSerializer
#         return MessageSerializer

#     def get_queryset(self):
#         chat = get_object_or_404(
#             Chat,
#             id=self.kwargs["chat_id"],
#             participants=self.request.user,
#             is_active=True,
#         )
#         # Mark unread messages as read
#         Message.objects.filter(chat=chat, is_read=False).exclude(
#             sender=self.request.user
#         ).update(is_read=True, read_at=timezone.now())
#         return Message.objects.filter(chat=chat).order_by("timestamp")

#     def perform_create(self, serializer):
#         user = self.request.user
#         chat = get_object_or_404(
#             Chat, id=self.kwargs["chat_id"], participants=user, is_active=True
#         )

#         # Handle uploaded files
#         media_fields = {
#             "voice_note_file": "voice_notes",
#             "image_file": "chat_images",
#             "video_file": "chat_videos",
#             "document_file": "chat_documents",
#         }

#         media_urls = {}
#         for field, folder in media_fields.items():
#             file = self.request.FILES.get(field)
#             if file:
#                 media_urls[field.replace("_file", "_url")] = self._save_file(
#                     file, folder
#                 )
#                 serializer.validated_data["message_type"] = field.replace("_file", "")

#         # Handle tip messages
#         msg_type = serializer.validated_data.get("message_type", "text")
#         tip_amount = serializer.validated_data.get("tip_amount", 0)
#         if msg_type == "tip" and tip_amount > 0:
#             if user.bondcoin_balance < tip_amount:
#                 raise serializers.ValidationError("Insufficient Bondcoins for this tip")
#             recipient = chat.participants.exclude(id=user.id).first()
#             if not recipient:
#                 raise serializers.ValidationError("No recipient found for this tip")
#             # Deduct and credit Bondcoins
#             user.bondcoin_balance -= tip_amount
#             recipient.bondcoin_balance += tip_amount
#             user.save()
#             recipient.save()
#             WalletTransaction.objects.create(
#                 user=user,
#                 tx_type="debit",
#                 amount=-tip_amount,
#                 status="completed",
#                 payment_method="bondcoin",
#             )
#             WalletTransaction.objects.create(
#                 user=recipient,
#                 tx_type="gift_received",
#                 amount=tip_amount,
#                 status="completed",
#                 payment_method="bondcoin",
#             )

#         serializer.save(chat=chat, sender=user, **media_urls)

#     def _save_file(self, file, folder):
#         ext = os.path.splitext(file.name)[1]
#         filename = f"{uuid.uuid4()}{ext}"
#         path = os.path.join(folder, filename)
#         default_storage.save(path, ContentFile(file.read()))
#         return default_storage.url(path)


# class MessageDetailView(generics.RetrieveUpdateDestroyAPIView):
#     """
#     Retrieve, update, or soft-delete a message.
#     """

#     permission_classes = [IsAuthenticated]
#     serializer_class = MessageSerializer

#     def get_queryset(self):
#         chat = get_object_or_404(
#             Chat,
#             id=self.kwargs["chat_id"],
#             participants=self.request.user,
#             is_active=True,
#         )
#         return Message.objects.filter(chat=chat)

#     def perform_update(self, serializer):
#         serializer.save(is_edited=True, edited_at=timezone.now())

#     def perform_destroy(self, instance):
#         instance.content = "[Message deleted]"
#         instance.message_type = "system"
#         instance.save()


# class CallInitiateView(generics.CreateAPIView):
#     """
#     Initiate a voice or video call.
#     """

#     serializer_class = CallInitiateSerializer
#     permission_classes = [IsAuthenticated]

#     def perform_create(self, serializer):
#         callee_id = serializer.validated_data["callee_id"]
#         call_type = serializer.validated_data["call_type"]

#         callee = get_object_or_404(User, id=callee_id, is_active=True)

#         # Find or create chat
#         chat = (
#             Chat.objects.filter(participants=self.request.user, chat_type="direct")
#             .filter(participants=callee)
#             .annotate(participant_count=models.Count("participants"))
#             .filter(participant_count=2)
#             .first()
#         )
#         if not chat:
#             chat = Chat.objects.create(chat_type="direct", created_by=self.request.user)
#             chat.participants.set([self.request.user, callee])

#         import uuid

#         call_id = str(uuid.uuid4())
#         room_id = f"room_{call_id}"

#         call = Call.objects.create(
#             chat=chat,
#             caller=self.request.user,
#             callee=callee,
#             call_type=call_type,
#             call_id=call_id,
#             room_id=room_id,
#             status="initiated",
#         )

#         # System message
#         Message.objects.create(
#             chat=chat,
#             sender=None,
#             message_type="call_start",
#             content=f"{self.request.user.name} started a {call_type} call",
#         )

#         return call


# class CallAnswerView(generics.UpdateAPIView):
#     """
#     Answer, decline, or mark a call as busy.
#     """

#     serializer_class = CallSerializer
#     permission_classes = [IsAuthenticated]
#     lookup_field = "call_id"

#     def get_queryset(self):
#         return Call.objects.filter(
#             callee=self.request.user, status__in=["initiated", "ringing"]
#         )

#     def update(self, request, *args, **kwargs):
#         call = self.get_object()
#         action = request.data.get("action")

#         if action == "answer":
#             call.status = "active"
#             call.answered_at = timezone.now()
#             content = f"{request.user.name} answered the call"
#             message_type = "call_start"

#         elif action == "decline":
#             call.status = "declined"
#             call.ended_at = timezone.now()
#             content = f"{request.user.name} declined the call"
#             message_type = "call_end"

#         elif action == "busy":
#             call.status = "busy"
#             call.ended_at = timezone.now()
#             content = f"{request.user.name} is busy"
#             message_type = "call_end"

#         else:
#             return Response(
#                 {"message": "Invalid action", "status": "error"},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         call.save()

#         # System message
#         Message.objects.create(
#             chat=call.chat,
#             sender=None,
#             message_type=message_type,
#             content=content,
#         )

#         serializer = self.get_serializer(call)
#         return Response(
#             {
#                 "message": f"Call {action}ed successfully",
#                 "status": "success",
#                 "call": serializer.data,
#             }
#         )


# class CallEndView(generics.UpdateAPIView):
#     """
#     End an active call.
#     """

#     serializer_class = CallSerializer
#     permission_classes = [IsAuthenticated]
#     lookup_field = "call_id"

#     def get_queryset(self):
#         # User must be a participant and call must be active
#         return Call.objects.filter(status="active", participants=self.request.user)

#     def update(self, request, *args, **kwargs):
#         call = self.get_object()

#         call.status = "ended"
#         call.ended_at = timezone.now()
#         if call.answered_at:
#             call.duration = int((call.ended_at - call.answered_at).total_seconds())
#         call.save()

#         Message.objects.create(
#             chat=call.chat,
#             sender=None,
#             message_type="call_end",
#             content=f"Call ended. Duration: {call.get_duration_display()}",
#         )

#         serializer = self.get_serializer(call)
#         return Response(
#             {
#                 "message": "Call ended successfully",
#                 "status": "success",
#                 "call": serializer.data,
#             }
#         )


# class ChatReportView(generics.CreateAPIView):
#     """
#     Report a chat, message, or user
#     """

#     permission_classes = [IsAuthenticated]

#     def get_serializer_class(self):
#         from .serializers import ChatReportSerializer

#         return ChatReportSerializer

#     def perform_create(self, serializer):
#         """Create report with current user as reporter"""
#         chat_id = self.kwargs.get("chat_id")
#         message_id = self.kwargs.get("message_id")

#         if chat_id:
#             chat = get_object_or_404(Chat, id=chat_id, participants=self.request.user)
#             serializer.validated_data["chat"] = chat

#         if message_id:
#             message = get_object_or_404(Message, id=message_id)
#             serializer.validated_data["message"] = message

#         serializer.save(reporter=self.request.user)


# class MatchmakerIntroView(generics.GenericAPIView):
#     """
#     Create a matchmaker introduction chat between two users
#     """

#     permission_classes = [IsAuthenticated]
#     serializer_class = ChatDetailSerializer

#     @extend_schema(
#         request=None,  # you can define an input serializer if you want docs for request body
#         responses={
#             201: ChatDetailSerializer,
#             400: OpenApiResponse(description="Bad request"),
#             403: OpenApiResponse(description="Forbidden"),
#             404: OpenApiResponse(description="User not found"),
#             500: OpenApiResponse(description="Server error"),
#         },
#     )
#     def post(self, request, *args, **kwargs):
#         try:
#             if not request.user.is_matchmaker:
#                 return Response(
#                     {
#                         "message": "Only matchmakers can create introductions",
#                         "status": "error",
#                     },
#                     status=status.HTTP_403_FORBIDDEN,
#                 )

#             user1_id = request.data.get("user1_id")
#             user2_id = request.data.get("user2_id")
#             intro_message = request.data.get("intro_message", "")

#             if not user1_id or not user2_id:
#                 return Response(
#                     {
#                         "message": "Both user1_id and user2_id are required",
#                         "status": "error",
#                     },
#                     status=status.HTTP_400_BAD_REQUEST,
#                 )

#             try:
#                 user1 = User.objects.get(id=user1_id, is_active=True)
#                 user2 = User.objects.get(id=user2_id, is_active=True)

#                 # Check if chat already exists
#                 existing_chat = (
#                     Chat.objects.filter(
#                         participants=user1, chat_type="matchmaker_intro"
#                     )
#                     .filter(participants=user2)
#                     .annotate(participant_count=models.Count("participants"))
#                     .filter(participant_count=2)
#                     .first()
#                 )

#                 if existing_chat:
#                     return Response(
#                         {
#                             "message": "Introduction chat already exists",
#                             "status": "error",
#                         },
#                         status=status.HTTP_400_BAD_REQUEST,
#                     )

#                 # Create matchmaker introduction chat
#                 chat = Chat.objects.create(
#                     chat_type="matchmaker_intro",
#                     created_by=request.user,
#                     chat_name=f"Introduction: {user1.name} & {user2.name}",
#                 )
#                 chat.participants.set([user1, user2, request.user])

#                 # Create system messages
#                 Message.objects.create(
#                     chat=chat,
#                     sender=None,
#                     message_type="system",
#                     content=f"{request.user.name} (moderator) made the match",
#                 )
#                 Message.objects.create(
#                     chat=chat,
#                     sender=None,
#                     message_type="system",
#                     content=f"{user1.name} was matched",
#                 )
#                 Message.objects.create(
#                     chat=chat,
#                     sender=None,
#                     message_type="system",
#                     content=f"{user2.name} was added",
#                 )

#                 # Create matchmaker introduction message
#                 intro_content = (
#                     intro_message
#                     or f"Hi {user1.name} & {user2.name} 👋, I've matched you because I see a good fit. Please introduce yourselves and get to know each other."
#                 )

#                 Message.objects.create(
#                     chat=chat,
#                     sender=request.user,
#                     message_type="matchmaker_intro",
#                     content=intro_content,
#                 )

#                 return Response(
#                     {
#                         "message": "Matchmaker introduction created successfully",
#                         "status": "success",
#                         "chat": self.get_serializer(
#                             chat, context={"request": request}
#                         ).data,
#                     },
#                     status=status.HTTP_201_CREATED,
#                 )

#             except User.DoesNotExist:
#                 return Response(
#                     {"message": "One or both users not found", "status": "error"},
#                     status=status.HTTP_404_NOT_FOUND,
#                 )

#         except Exception as e:
#             return Response(
#                 {
#                     "message": f"An unexpected error occurred: {str(e)}",
#                     "status": "error",
#                 },
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )


# =============================================================================
# LIVE SESSION VIEWS (NEW)
# =============================================================================


# class LiveSessionListView(generics.ListCreateAPIView):
#     """
#     List active live sessions or create a new live session
#     """

#     permission_classes = [IsAuthenticated]

#     def get_serializer_class(self):
#         if self.request.method == "POST":
#             from .serializers import LiveSessionCreateSerializer

#             return LiveSessionCreateSerializer
#         from .serializers import LiveSessionSerializer

#         return LiveSessionSerializer

#     def get_queryset(self):
#         from .models import LiveSession
#         from django.utils import timezone

#         # Get active live sessions
#         return (
#             LiveSession.objects.filter(
#                 status="active",
#                 start_time__gte=timezone.now()
#                 - timezone.timedelta(hours=24),  # Only recent sessions
#             )
#             .select_related("user")
#             .order_by("-start_time")
#         )

#     def perform_create(self, serializer):
#         """Create live session with current user"""
#         serializer.save(user=self.request.user)


# class LiveSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
#     """
#     Retrieve, update, or end a specific live session
#     """

#     permission_classes = [IsAuthenticated]

#     def get_serializer_class(self):
#         return LiveSessionSerializer

#     def get_queryset(self):
#         return LiveSession.objects.filter(user=self.request.user)

#     def perform_destroy(self, instance):
#         """End the live session instead of deleting"""

#         instance.status = "ended"
#         instance.end_time = timezone.now()
#         instance.save()


# class LiveSessionJoinView(generics.CreateAPIView):
#     """
#     Join a live session as a viewer
#     """

#     permission_classes = [IsAuthenticated]
#     serializer_class = LiveParticipantSerializer

#     def create(self, request, session_id):
#         try:
#             session = LiveSession.objects.get(id=session_id, status="active")

#             # Check if user is already a participant
#             participant, created = LiveParticipant.objects.get_or_create(
#                 session=session, user=request.user, defaults={"role": "viewer"}
#             )

#             if created:
#                 # Update viewers count
#                 session.viewers_count += 1
#                 session.save(update_fields=["viewers_count"])

#                 serializer = self.get_serializer(participant)
#                 return Response(
#                     {
#                         "message": "Successfully joined live session",
#                         "status": "success",
#                         "participant_id": participant.id,
#                         "data": serializer.data,
#                     },
#                     status=status.HTTP_201_CREATED,
#                 )
#             else:
#                 serializer = self.get_serializer(participant)
#                 return Response(
#                     {
#                         "message": "Already participating in this session",
#                         "status": "info",
#                         "data": serializer.data,
#                     },
#                     status=status.HTTP_200_OK,
#                 )

#         except LiveSession.DoesNotExist:
#             return Response(
#                 {"message": "Live session not found or not active", "status": "error"},
#                 status=status.HTTP_404_NOT_FOUND,
#             )


# class LiveSessionLeaveView(generics.GenericAPIView):
#     """
#     Leave a live session
#     """

#     permission_classes = [IsAuthenticated]
#     serializer_class = LiveParticipantSerializer  # For schema purposes

#     @extend_schema(
#         request=None,
#         responses={
#             200: OpenApiResponse(
#                 response=LiveParticipantSerializer,
#                 description="Successfully left the live session",
#             ),
#             404: OpenApiResponse(description="Live session or participation not found"),
#         },
#     )
#     def post(self, request, session_id, *args, **kwargs):
#         # Get the live session
#         session = get_object_or_404(LiveSession, id=session_id)

#         # Get the participant record
#         participant = get_object_or_404(
#             LiveParticipant, session=session, user=request.user, left_at__isnull=True
#         )

#         # Mark as left
#         participant.left_at = timezone.now()
#         participant.save()

#         # Update viewers count safely
#         session.viewers_count = max(0, session.viewers_count - 1)
#         session.save(update_fields=["viewers_count"])

#         return Response(
#             {"message": "Successfully left live session", "status": "success"},
#             status=status.HTTP_200_OK,
#         )


# =============================================================================
# SOCIAL FEED AND STORY VIEWS (NEW)
# =============================================================================


# ============================================================================
# before UserSocialHandleListView (original lines 4540-4830)
# ============================================================================


# class PostReportView(generics.CreateAPIView):
#     """
#     Report a post or comment
#     """

#     permission_classes = [IsAuthenticated]

#     def get_serializer_class(self):
#         from .serializers import PostReportSerializer

#         return PostReportSerializer

#     def perform_create(self, serializer):
#         """Create report with current user as reporter"""
#         post_id = self.kwargs.get("post_id")
#         comment_id = self.kwargs.get("comment_id")

#         if post_id:
#             from .models import Post

#             post = get_object_or_404(Post, id=post_id, is_active=True)
#             serializer.validated_data["post"] = post
#             serializer.validated_data["reported_user"] = post.author

#         if comment_id:
#             from .models import PostComment

#             comment = get_object_or_404(PostComment, id=comment_id, is_active=True)
#             serializer.validated_data["comment"] = comment
#             serializer.validated_data["reported_user"] = comment.author

#         serializer.save(reporter=self.request.user)


# @extend_schema_view(
#     retrieve=extend_schema(
#         parameters=[
#             OpenApiParameter(name="pk", description="Story ID", location=OpenApiParameter.PATH, type=int),
#             OpenApiParameter(name="id", description="Story ID", location=OpenApiParameter.PATH, type=int),
#         ]
#     ),
#     update=extend_schema(
#         parameters=[
#             OpenApiParameter(name="pk", description="Story ID", location=OpenApiParameter.PATH, type=int),
#             OpenApiParameter(name="id", description="Story ID", location=OpenApiParameter.PATH, type=int),
#         ]
#     ),
#     partial_update=extend_schema(
#         parameters=[
#             OpenApiParameter(name="pk", description="Story ID", location=OpenApiParameter.PATH, type=int),
#             OpenApiParameter(name="id", description="Story ID", location=OpenApiParameter.PATH, type=int),
#         ]
#     ),
#     destroy=extend_schema(
#         parameters=[
#             OpenApiParameter(name="pk", description="Story ID", location=OpenApiParameter.PATH, type=int),
#             OpenApiParameter(name="id", description="Story ID", location=OpenApiParameter.PATH, type=int),
#         ]
#     ),
#     like=extend_schema(
#         parameters=[
#             OpenApiParameter(name="pk", description="Story ID", location=OpenApiParameter.PATH, type=int),
#             OpenApiParameter(name="id", description="Story ID", location=OpenApiParameter.PATH, type=int),
#         ]
#     ),
#     share=extend_schema(
#         parameters=[
#             OpenApiParameter(name="pk", description="Story ID", location=OpenApiParameter.PATH, type=int),
#             OpenApiParameter(name="id", description="Story ID", location=OpenApiParameter.PATH, type=int),
#         ]
#     ),
# )
# class StoryViewSet(StoryQueryMixin, viewsets.ModelViewSet):
#     permission_classes = [permissions.IsAuthenticated]
#     lookup_field = "pk"

#     def get_queryset(self):
#         return self.base_queryset()

#     def get_serializer_class(self):
#         if self.action == "create":
#             return StoryCreateSerializer
#         return StorySerializer

#     def perform_create(self, serializer):
#         """Automatically set author and 24-hour expiration"""
#         serializer.save(
#             author=self.request.user, expires_at=timezone.now() + timedelta(hours=24)
#         )

#     def retrieve(self, request, pk=None):
#         """Retrieve story and track a view for the current user."""
#         story = get_object_or_404(self.get_queryset(), pk=pk)
#         StoryView.objects.get_or_create(story=story, viewer=request.user)
#         serializer = self.get_serializer(story)
#         return Response(serializer.data)

#     @action(detail=True, methods=["post"])
#     def like(self, request, pk=None):
#         """Toggle like on a story"""
#         story = self.get_object()
#         interaction, created = StoryInteraction.objects.get_or_create(
#             story=story, user=request.user, interaction_type="like"
#         )

#         if not created:
#             # Toggle off if already liked
#             interaction.delete()
#             liked = False
#         else:
#             liked = True

#         # Update reactions_count
#         story.reactions_count = story.interactions.count()
#         story.save(update_fields=["reactions_count"])

#         return Response({"liked": liked, "reactions_count": story.reactions_count})

#     @action(detail=True, methods=["post"])
#     def share(self, request, pk=None):
#         """Share a story once"""
#         story = self.get_object()
#         interaction, created = StoryInteraction.objects.get_or_create(
#             story=story, user=request.user, interaction_type="share"
#         )

#         if not created:
#             return Response(
#                 {"shared": False, "detail": "Already shared"},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         # Update reactions_count
#         story.reactions_count = story.interactions.count()
#         story.save(update_fields=["reactions_count"])

#         return Response({"shared": True})


# class StoryViewersListView(generics.ListAPIView):
#     serializer_class = StoryViewerSerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def get_queryset(self):
#         story = get_object_or_404(Story, pk=self.kwargs["pk"])

#         if story.author != self.request.user:
#             return StoryView.objects.none()

#         return story.views.select_related("viewer")


# class FeedSearchView(generics.ListAPIView):
#     """
#     Search posts in the Bond Story feed
#     """

#     serializer_class = PostSerializer
#     permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         query = self.request.GET.get("q", "").strip()
#         if not query:
#             return Post.objects.none()

#         # Search posts by content, hashtags, and author name
#         return (
#             Post.objects.filter(
#                 Q(content__icontains=query)
#                 | Q(hashtags__icontains=query)
#                 | Q(author__name__icontains=query)
#                 | Q(location__icontains=query),
#                 is_active=True,
#                 visibility="public",
#             )
#             .select_related("author")
#             .prefetch_related("comments__author")
#             .order_by("-created_at")
#         )

#     def list(self, request, *args, **kwargs):
#         try:
#             queryset = self.get_queryset()
#             query = self.request.GET.get("q", "").strip()

#             # Store search query for analytics
#             FeedSearch.objects.create(
#                 user=request.user, query=query, results_count=queryset.count()
#             )

#             # Use paginated response if needed, otherwise standard list
#             page = self.paginate_queryset(queryset)
#             if page is not None:
#                 serializer = self.get_serializer(page, many=True)
#                 return self.get_paginated_response(serializer.data)

#             serializer = self.get_serializer(queryset, many=True)
#             return Response(
#                 {
#                     "message": "Search completed successfully",
#                     "status": "success",
#                     "query": query,
#                     "results_count": queryset.count(),
#                     "posts": serializer.data,
#                 },
#                 status=status.HTTP_200_OK,
#             )
#         except Exception as e:
#             return Response(
#                 {
#                     "message": f"An unexpected error occurred during search: {str(e)}",
#                     "status": "error",
#                 },
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )


# @extend_schema(responses=FeedSuggestionsResponseSerializer)
# class FeedSuggestionsView(generics.ListAPIView):
#     """
#     Get search suggestions for the Bond Story feed
#     """

#     permission_classes = [IsAuthenticated]
#     serializer_class = FeedSuggestionsResponseSerializer

#     def get_queryset(self):
#         # Required by ListAPIView but unused
#         return FeedSearch.objects.none()

#     def list(self, request, *args, **kwargs):
#         from .models import FeedSearch, Post
#         from django.db.models import Count

#         query = request.GET.get("q", "").strip()

#         if query:
#             suggestions = (
#                 FeedSearch.objects.filter(query__icontains=query)
#                 .values("query")
#                 .annotate(count=Count("query"))
#                 .order_by("-count")[:5]
#             )

#             hashtag_suggestions = Post.objects.filter(
#                 hashtags__icontains=query, is_active=True
#             ).values_list("hashtags", flat=True)

#             all_hashtags = []
#             for hashtags in hashtag_suggestions:
#                 if hashtags:
#                     all_hashtags.extend(hashtags)

#             filtered_hashtags = [
#                 tag for tag in set(all_hashtags) if query.lower() in tag.lower()
#             ]

#             return Response(
#                 FeedSuggestionsResponseSerializer(
#                     {
#                         "message": "Suggestions retrieved successfully",
#                         "status": "success",
#                         "suggestions": [s["query"] for s in suggestions],
#                         "hashtags": filtered_hashtags[:5],
#                     }
#                 ).data
#             )
#         else:
#             popular_searches = (
#                 FeedSearch.objects.values("query")
#                 .annotate(count=Count("query"))
#                 .order_by("-count")[:10]
#             )

#             return Response(
#                 FeedSuggestionsResponseSerializer(
#                     {
#                         "message": "Popular searches retrieved successfully",
#                         "status": "success",
#                         "popular_searches": [s["query"] for s in popular_searches],
#                     }
#                 ).data
#             )


# =============================================================================
# SOCIAL MEDIA HANDLES VIEWS (NEW FROM FIGMA)
# =============================================================================


# ============================================================================
# before UsernameUpdateView (original lines 4956-4993)
# ============================================================================


# =============================================================================
# USERNAME VALIDATION VIEWS (NEW FROM FIGMA)
# =============================================================================


# class CreateUsernameView(generics.CreateAPIView):
#     permission_classes = [IsAuthenticated]
#     serializer_class = CreateUsernameSerializer

#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)

#         try:
#             serializer.is_valid(raise_exception=True)
#             user = serializer.save()

#             return Response(
#                 {
#                     "message": "Username created successfully",
#                     "status": "success",
#                     "username": user.username,
#                 },
#                 status=status.HTTP_201_CREATED,
#             )

#         except serializers.ValidationError as e:
#             # This is where suggestions come back
#             return Response(
#                 {
#                     "message": "Username unavailable",
#                     "status": "error",
#                     **e.detail,
#                 },
#                 status=status.HTTP_400_BAD_REQUEST,
#             )


# ============================================================================
# before LANGUAGE_NAMES (original lines 5717-5889)
# ============================================================================


# Firebase Integration Views
# These views integrate Firebase Auth and Firestore for
# user authentication, profiles, and matches.


# class FirebaseLoginView(generics.GenericAPIView):
#     """
#     Authenticate user with Firebase ID token.
#     Returns Django JWT tokens.
#     """

#     permission_classes = [AllowAny]
#     serializer_class = UserSerializer

#     @extend_schema(request=None, responses={200: UserSerializer})
#     def post(self, request, *args, **kwargs):
#         auth_header = request.headers.get("Authorization")
#         if not auth_header or not auth_header.startswith("Bearer "):
#             return Response(
#                 {"error": "Missing or invalid Authorization header"},
#                 status=status.HTTP_401_UNAUTHORIZED,
#             )

#         id_token = auth_header.split(" ")[1]
#         decoded_token = verify_firebase_token(id_token)
#         if not decoded_token:
#             return Response(
#                 {"error": "Invalid Firebase token"}, status=status.HTTP_401_UNAUTHORIZED
#             )

#         user = get_or_create_user_from_firebase(decoded_token)

#         from rest_framework_simplejwt.tokens import RefreshToken

#         refresh = RefreshToken.for_user(user)

#         return Response(
#             {
#                 "message": "Login successful",
#                 "user": UserSerializer(user).data,
#                 "access_token": str(refresh.access_token),
#                 "refresh_token": str(refresh),
#             }
#         )


# class FirebaseUserProfileView(generics.GenericAPIView):
#     """
#     Get or update user profile in Firestore.
#     """

#     permission_classes = [IsAuthenticated]
#     serializer_class = UserProfileSerializer

#     def _get_uid(self, request):
#         auth_header = request.headers.get("Authorization")
#         if not auth_header or not auth_header.startswith("Bearer "):
#             return None
#         id_token = auth_header.split(" ")[1]
#         decoded_token = verify_firebase_token(id_token)
#         if not decoded_token:
#             return None
#         return decoded_token["uid"]

#     def get(self, request, *args, **kwargs):
#         uid = self._get_uid(request)
#         if not uid:
#             return Response(
#                 {"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED
#             )

#         profile = get_user_profile_from_firestore(uid)
#         if not profile:
#             return Response(
#                 {"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND
#             )

#         serializer = self.get_serializer(profile)
#         return Response(serializer.data)

#     def post(self, request, *args, **kwargs):
#         uid = self._get_uid(request)
#         if not uid:
#             return Response(
#                 {"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED
#             )

#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         success = update_user_profile_in_firestore(uid, serializer.validated_data)
#         if success:
#             return Response({"message": "Profile updated"})
#         return Response(
#             {"error": "Update failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
#         )


# class FirebaseMatchView(generics.GenericAPIView):
#     """
#     Create a match between users.
#     """

#     permission_classes = [IsAuthenticated]
#     serializer_class = FirebaseMatchSerializer

#     def post(self, request, *args, **kwargs):
#         uid = FirebaseUserProfileView()._get_uid(request)
#         if not uid:
#             return Response(
#                 {"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED
#             )

#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         matched_uid = serializer.validated_data["matched_uid"]

#         success = create_match_in_firestore(uid, matched_uid)
#         if success:
#             return Response({"message": "Match created"})
#         return Response(
#             {"error": "Match creation failed"},
#             status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#         )


# class FirebaseMatchesListView(generics.ListAPIView):
#     """
#     Get list of matches for the authenticated user.
#     """

#     permission_classes = [IsAuthenticated]
#     serializer_class = FirebaseMatchSerializer

#     def list(self, request, *args, **kwargs):
#         uid = FirebaseUserProfileView()._get_uid(request)
#         if not uid:
#             return Response(
#                 {"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED
#             )
#         matches = get_matches_for_user(uid)
#         serializer = self.get_serializer(matches, many=True)
#         return Response(serializer.data)


# class FirebasePushNotificationView(generics.GenericAPIView):
#     permission_classes = [AllowAny]
#     serializer_class = PushNotificationSerializer

#     def post(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         token = serializer.validated_data["token"]
#         title = serializer.validated_data.get("title", "Notification")
#         body = serializer.validated_data.get("body", "Message")

#         response = send_push_notification(token, title, body)
#         if response:
#             return Response({"message": "Notification sent", "response": response})
#         return Response(
#             {"error": "Failed to send notification"},
#             status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#        )


# ==========================
# TRANSLATION
# ==========================



# ============================================================================
# before SendGenericEmailView (original lines 6082-6109)
# ============================================================================


# ==========================
# JOB OPTIONS
# ==========================


# class JobOptionsView(APIView):
#     def get(self, request):
#         return Response(
#             {
#                 "message": "Job options retrieved",
#                 "status": "success",
#                 "data": {
#                     "categories": [{"value": k, "label": v} for k, v in Job.CATEGORIES],
#                     "types": [{"value": k, "label": v} for k, v in Job.JOB_TYPES],
#                     "statuses": [
#                         {"value": k, "label": v} for k, v in Job.STATUS_CHOICES
#                     ],
#                 },
#             }
#         )


# ==========================
# EMAIL
# ==========================

