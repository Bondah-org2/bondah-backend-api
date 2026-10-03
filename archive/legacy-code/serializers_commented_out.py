"""
Commented-out code removed from dating/serializers.py when it was split into a package.
Kept for reference only; nothing imports this file.
"""

# ============================================================================
# before UsernameUpdateSerializer (original lines 768-828)
# ============================================================================
    
# =============================================================================
# USERNAME VALIDATION SERIALIZERS (NEW FROM FIGMA)
# =============================================================================


# class CreateUsernameSerializer(serializers.Serializer):
#     username = serializers.CharField(max_length=30)

#     def validate_username(self, value):
#         user = self.context["request"].user

#         # User already has username
#         if user.username:
#             raise serializers.ValidationError(
#                 "Username is already set. You cannot change it here."
#             )

#         clean_username = value.strip().lstrip("@")

#         # Validate format
#         try:
#             validate_username_format(clean_username)
#         except ValidationError as e:
#             raise serializers.ValidationError(str(e))

#         # Check availability
#         is_valid, message, suggestions = UsernameValidation.validate_username(
#             clean_username
#         )

#         # Attach result for use in create()
#         self._username_check = {
#             "is_valid": is_valid,
#             "message": message,
#             "suggestions": suggestions,
#             "clean_username": clean_username,
#         }

#         return clean_username

#     def create(self, validated_data):
#         check = self._username_check
#         user = self.context["request"].user

#         # If username is taken → DO NOT create
#         if not check["is_valid"]:
#             raise serializers.ValidationError(
#                 {
#                     "message": check["message"],
#                     "suggestions": check["suggestions"],
#                 }
#             )

#         # Create username
#         user.username = check["clean_username"]
#         user.save(update_fields=["username"])

#         return user



# ============================================================================
# before TokensSerializer (original lines 925-1048)
# ============================================================================


# class JobDetailSerializer(serializers.ModelSerializer):
#     jobType = serializers.CharField(source="job_type")
#     salaryRange = serializers.CharField(source="salary_range")
#     createdAt = serializers.DateTimeField(source="created_at")

#     class Meta:
#         model = Job
#         fields = [
#             "id",
#             "title",
#             "jobType",
#             "category",
#             "status",
#             "description",
#             "location",
#             "salaryRange",
#             "requirements",
#             "createdAt",
#         ]


# class JobApplicationSerializer(serializers.ModelSerializer):
#     # Input fields (write)
#     jobId = serializers.IntegerField(write_only=True)
#     firstName = serializers.CharField(source="first_name")
#     lastName = serializers.CharField(source="last_name")
#     email = serializers.EmailField()
#     phone = serializers.CharField()
#     resumeUrl = serializers.URLField(
#         write_only=True, required=False, allow_blank=True, source="resume_url"
#     )
#     coverLetter = serializers.CharField(
#         write_only=True, required=False, allow_blank=True, source="cover_letter"
#     )
#     experienceYears = serializers.IntegerField(
#         source="experience_years", required=False
#     )
#     currentCompany = serializers.CharField(
#         source="current_company", required=False, allow_blank=True
#     )
#     expectedSalary = serializers.CharField(
#         source="expected_salary", required=False, allow_blank=True
#     )

#     # Output fields (read-only, camelCase)
#     appliedAt = serializers.DateTimeField(source="applied_at", read_only=True)
#     resumeUrlOut = serializers.SerializerMethodField()
#     coverLetterOut = serializers.SerializerMethodField()

#     class Meta:
#         model = JobApplication
#         fields = [
#             "id",
#             "jobId",
#             "firstName",
#             "lastName",
#             "email",
#             "phone",
#             "resumeUrl",
#             "coverLetter",
#             "resumeUrlOut",
#             "coverLetterOut",
#             "experienceYears",
#             "currentCompany",
#             "expectedSalary",
#             "status",
#             "appliedAt",
#         ]
#         read_only_fields = [
#             "id",
#             "status",
#             "appliedAt",
#             "resumeUrlOut",
#             "coverLetterOut",
#         ]

#     # Output camelCase methods
#     def get_resumeUrlOut(self, obj) -> str | None:
#         return obj.resume_url

#     def get_coverLetterOut(self, obj) -> str | None:
#         return obj.cover_letter

#     # Validation
#     def validate(self, data):
#         job_id = data.get("jobId") or data.get("job", {}).get("id")
#         try:
#             job = Job.objects.get(id=job_id)
#             if job.status != "open":
#                 raise serializers.ValidationError(
#                     "This job is not currently accepting applications."
#                 )
#         except Job.DoesNotExist:
#             raise serializers.ValidationError("Job not found.")

#         email = data.get("email")
#         if JobApplication.objects.filter(job=job, email=email).exists():
#             raise serializers.ValidationError("You have already applied for this job.")

#         data["job"] = job  # attach Job instance for creation
#         return data

#     # Ensure jobId is removed before saving
#     def create(self, validated_data):
#         validated_data.pop("jobId", None)
#         return super().create(validated_data)

#     # Optional: standard success response
#     def to_representation(self, instance):
#         return {
#             "message": "Job application submitted successfully!",
#             "status": "success",
#             "applicationId": instance.id,
#         }


# class ResendOTPSerializer(serializers.Serializer):
#     type = serializers.ChoiceField(choices=["email", "phone"])
#     identifier = serializers.CharField(required=False)
#     phone_number = serializers.CharField(required=False)
#     country_code = serializers.CharField(default="+1", required=False)


# ============================================================================
# before SocialLoginSerializer (original lines 1499-1550)
# ============================================================================


# class UserProfileUpdateSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = User
#         fields = ("name", "gender", "age", "location", "bio", "is_matchmaker")
#         read_only_fields = ("is_matchmaker",)  # Prevent privilege escalation

#     def validate_bio(self, value):
#         """Sanitize bio text for XSS prevention"""
#         if value:
#             return self._sanitize_text_input(value)
#         return value

#     def validate_name(self, value):
#         """Sanitize name for XSS prevention"""
#         if value:
#             return self._sanitize_text_input(value)
#         return value

#     def _sanitize_text_input(self, text):
#         """Sanitize text input to prevent XSS attacks"""
#         import re
#         import html

#         if not text:
#             return text

#         # Escape HTML entities
#         text = html.escape(text, quote=True)

#         # Remove or escape potentially dangerous patterns
#         dangerous_patterns = [
#             r"<script[^>]*>.*?</script>",  # Script tags
#             r"javascript:",  # JavaScript URLs
#             r"vbscript:",  # VBScript URLs
#             r"data:",  # Data URLs
#             r"on\w+\s*=",  # Event handlers
#         ]

#         for pattern in dangerous_patterns:
#             text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)

#         return text

#     def update(self, instance, validated_data):
#         for attr, value in validated_data.items():
#             setattr(instance, attr, value)
#         instance.save()
#         return instance



# ============================================================================
# before UserInterestSerializer (original lines 2589-2632)
# ============================================================================


# class UserSearchSerializer(serializers.ModelSerializer):
#     """Serializer for user search results"""

#     distance = serializers.SerializerMethodField()
#     match_score = serializers.SerializerMethodField()

#     class Meta:
#         model = User
#         fields = [
#             "id",
#             "name",
#             "age",
#             "gender",
#             "bio",
#             "profile_picture",
#             "city",
#             "state",
#             "country",
#             "education_level",
#             "height",
#             "zodiac_sign",
#             "relationship_status",
#             "dating_type",
#             "distance",
#             "match_score",
#         ]

#     def get_distance(self, obj) -> float | None:
#         request = self.context.get("request")
#         if request and request.user.has_location and obj.has_location:
#             return request.user.get_distance_to(obj)
#         return None

#     def get_match_score(self, obj) -> float | None:
#         request = self.context.get("request")
#         if request and request.user != obj:
#             from .location_utils import calculate_match_score

#             return calculate_match_score(request.user, obj)
#         return None



# ============================================================================
# before MessageSerializer (original lines 2867-2912)
# ============================================================================


# class ChatParticipantSerializer(serializers.ModelSerializer):
#     """Serializer for chat participants (simplified user info)"""

#     user_id = serializers.IntegerField(source="user.id", read_only=True)
#     name = serializers.CharField(source="user.name", read_only=True)
#     profile_picture = serializers.URLField(
#         source="user.profile_picture", read_only=True
#     )
#     is_online = serializers.SerializerMethodField()
#     is_muted = serializers.SerializerMethodField()

#     class Meta:
#         model = ChatParticipant
#         fields = [
#             "user_id",
#             "name",
#             "profile_picture",
#             "is_online",
#             "joined_at",
#             "last_seen_at",
#             "is_active",
#             "custom_nickname",
#             "notifications_enabled",
#             "is_muted",
#         ]
#         read_only_fields = [
#             "user_id",
#             "name",
#             "profile_picture",
#             "is_online",
#             "joined_at",
#             "last_seen_at",
#         ]

#     def get_is_online(self, obj) -> bool:
#         """Check if user is online (placeholder - implement with real-time status)"""
#         return False

#     @extend_schema_field({"type": "boolean"})
#     def get_is_muted(self, obj) -> bool:
#         """Check if chat is muted for this participant"""
#         return obj.is_muted



# ============================================================================
# before PostCommentSerializer (original lines 3045-3244)
# ============================================================================

    # def get_is_from_current_user(self, obj) -> bool:
    #     """Check if message is from the current user"""
    #     request = self.context.get("request")
    #     if request and request.user.is_authenticated:
    #         return obj.sender == request.user
    #     return False

    # def get_reply_to_message(self, obj) -> str:
    #     """Get the message being replied to"""
    #     if obj.reply_to:
    #         return {
    #             "id": obj.reply_to.id,
    #             "content": (
    #                 obj.reply_to.content[:100] + "..."
    #                 if len(obj.reply_to.content or "") > 100
    #                 else obj.reply_to.content
    #             ),
    #             "sender_name": (
    #                 obj.reply_to.sender.name if obj.reply_to.sender else "System"
    #             ),
    #             "message_type": obj.reply_to.message_type,
    #             "timestamp": obj.reply_to.timestamp,
    #         }
    #     return None

    # def get_formatted_timestamp(self, obj) -> str:
    #     """Get formatted timestamp for display"""
    #     from django.utils import timezone

    #     now = timezone.now()
    #     diff = now - obj.timestamp

    #     if diff.days == 0:
    #         return obj.timestamp.strftime("%H:%M")
    #     elif diff.days == 1:
    #         return "Yesterday"
    #     elif diff.days < 7:
    #         return obj.timestamp.strftime("%A")
    #     else:
    #         return obj.timestamp.strftime("%m/%d/%Y")


# class VoiceNoteSerializer(serializers.ModelSerializer):
#     """Serializer for voice notes"""

#     message_id = serializers.IntegerField(source="message.id", read_only=True)

#     class Meta:
#         model = VoiceNote
#         fields = [
#             "id",
#             "message_id",
#             "audio_url",
#             "duration",
#             "file_size",
#             "transcription",
#             "transcription_confidence",
#             "created_at",
#         ]
#         read_only_fields = ["id", "message_id", "created_at"]


# class CallSerializer(serializers.ModelSerializer):
#     """Serializer for voice/video calls"""

#     caller_name = serializers.CharField(source="caller.name", read_only=True)
#     caller_profile_picture = serializers.URLField(
#         source="caller.profile_picture", read_only=True
#     )
#     callee_name = serializers.CharField(source="callee.name", read_only=True)
#     callee_profile_picture = serializers.URLField(
#         source="callee.profile_picture", read_only=True
#     )
#     duration_display = serializers.CharField(
#         source="get_duration_display", read_only=True
#     )

#     class Meta:
#         model = Call
#         fields = [
#             "id",
#             "chat",
#             "caller",
#             "caller_name",
#             "caller_profile_picture",
#             "callee",
#             "callee_name",
#             "callee_profile_picture",
#             "call_type",
#             "status",
#             "started_at",
#             "answered_at",
#             "ended_at",
#             "duration",
#             "duration_display",
#             "call_id",
#             "room_id",
#             "quality_score",
#             "is_recorded",
#             "recording_url",
#         ]
#         read_only_fields = [
#             "id",
#             "chat",
#             "caller",
#             "caller_name",
#             "caller_profile_picture",
#             "callee",
#             "callee_name",
#             "callee_profile_picture",
#             "started_at",
#             "answered_at",
#             "ended_at",
#             "duration",
#             "duration_display",
#             "quality_score",
#         ]


# class CallInitiateSerializer(serializers.Serializer):
#     """Serializer for initiating calls"""

#     callee_id = serializers.IntegerField()
#     call_type = serializers.ChoiceField(
#         choices=[("voice", "Voice Call"), ("video", "Video Call")]
#     )

#     def validate_callee_id(self, value):
#         """Validate callee exists"""
#         if not User.objects.filter(id=value, is_active=True).exists():
#             raise serializers.ValidationError("User not found or inactive")
#         return value


# class ChatReportSerializer(serializers.ModelSerializer):
#     """Serializer for chat reports"""

#     reporter_name = serializers.CharField(source="reporter.name", read_only=True)
#     reported_user_name = serializers.CharField(
#         source="reported_user.name", read_only=True
#     )

#     class Meta:
#         model = ChatReport
#         fields = [
#             "id",
#             "reporter",
#             "reporter_name",
#             "reported_user",
#             "reported_user_name",
#             "chat",
#             "message",
#             "report_type",
#             "description",
#             "status",
#             "moderator_notes",
#             "action_taken",
#             "resolved_by",
#             "resolved_at",
#             "created_at",
#         ]
#         read_only_fields = [
#             "id",
#             "reporter",
#             "reporter_name",
#             "reported_user_name",
#             "status",
#             "moderator_notes",
#             "action_taken",
#             "resolved_by",
#             "resolved_at",
#             "created_at",
#         ]

#     def create(self, validated_data):
#         """Create report with current user as reporter"""
#         request = self.context.get("request")
#         if request and request.user.is_authenticated:
#             validated_data["reporter"] = request.user
#         return super().create(validated_data)

# class ChatSettingsSerializer(serializers.ModelSerializer):
#     """Serializer for chat settings"""

#     class Meta:
#         model = Chat
#         fields = ["chat_name", "chat_theme"]

#     def update(self, instance, validated_data):
#         """Update chat settings"""
#         for attr, value in validated_data.items():
#             setattr(instance, attr, value)
#         instance.save()
#         return instance

# # =============================================================================
# # SOCIAL FEED AND STORY SERIALIZERS (NEW)
# # =============================================================================


# ============================================================================
# before StorySerializer (original lines 3378-3431)
# ============================================================================

    # def get_has_bonded(self, obj) -> bool:
    #     user = self.context["request"].user
    #     return obj.interactions.filter(user=user, interaction_type="bond").exists()


# class PostCreateSerializer(serializers.ModelSerializer):
#     """Serializer for creating new posts"""

#     class Meta:
#         model = Post
#         fields = [
#             "post_type",
#             "content",
#             "image_urls",
#             "video_url",
#             "video_thumbnail",
#             "visibility",
#             "location",
#             "hashtags",
#             "mentions",
#         ]

#     def validate_content(self, value):
#         """Validate and sanitize post content"""
#         if not value or len(value.strip()) == 0:
#             raise serializers.ValidationError("Post content cannot be empty")
#         if len(value) > 2000:
#             raise serializers.ValidationError(
#                 "Post content cannot exceed 2000 characters"
#             )
#         # Sanitize for XSS prevention
#         return self._sanitize_text_input(value)

#     def validate_location(self, value):
#         """Sanitize location text"""
#         if value:
#             return self._sanitize_text_input(value)
#         return value

#     def validate_image_urls(self, value):
#         """Validate image URLs"""
#         if value and len(value) > 10:
#             raise serializers.ValidationError("Cannot attach more than 10 images")
#         return value

#     def create(self, validated_data):
#         """Create post with current user as author"""
#         request = self.context.get("request")
#         if request and request.user.is_authenticated:
#             validated_data["author"] = request.user
#         return super().create(validated_data)



# ============================================================================
# before SubscriptionPlanSerializer (original lines 3608-3711)
# ============================================================================


# class PostReportSerializer(serializers.ModelSerializer):
#     """Serializer for post/comment reports"""

#     reporter_name = serializers.CharField(source="reporter.name", read_only=True)
#     reported_user_name = serializers.CharField(
#         source="reported_user.name", read_only=True
#     )

#     class Meta:
#         model = PostReport
#         fields = [
#             "id",
#             "reporter",
#             "reporter_name",
#             "reported_user",
#             "reported_user_name",
#             "post",
#             "comment",
#             "report_type",
#             "description",
#             "status",
#             "moderator_notes",
#             "action_taken",
#             "resolved_by",
#             "resolved_at",
#             "created_at",
#         ]
#         read_only_fields = [
#             "id",
#             "reporter",
#             "reporter_name",
#             "reported_user_name",
#             "status",
#             "moderator_notes",
#             "action_taken",
#             "resolved_by",
#             "resolved_at",
#             "created_at",
#         ]

#     def create(self, validated_data):
#         """Create report with current user as reporter"""
#         request = self.context.get("request")
#         if request and request.user.is_authenticated:
#             validated_data["reporter"] = request.user
#         return super().create(validated_data)


# class PostShareSerializer(serializers.ModelSerializer):
#     """Serializer for post shares"""

#     class Meta:
#         model = PostShare
#         fields = ["platform"]

#     def create(self, validated_data):
#         """Create share with current user"""
#         request = self.context.get("request")
#         if request and request.user.is_authenticated:
#             validated_data["user"] = request.user
#         return super().create(validated_data)


# class FeedSearchSerializer(serializers.ModelSerializer):
#     """Serializer for feed search queries"""

#     class Meta:
#         model = FeedSearch
#         fields = ["query", "filters_applied"]

#     def create(self, validated_data):
#         """Create search with current user"""
#         request = self.context.get("request")
#         if request and request.user.is_authenticated:
#             validated_data["user"] = request.user
#         return super().create(validated_data)


# class FeedSuggestionSerializer(serializers.Serializer):
#     query = serializers.CharField()
#     count = serializers.IntegerField(required=False)


# class FeedSuggestionsResponseSerializer(serializers.Serializer):
#     message = serializers.CharField()
#     status = serializers.CharField()
#     suggestions = serializers.ListField(
#         child=serializers.CharField(), required=False
#     )
#     hashtags = serializers.ListField(
#         child=serializers.CharField(), required=False
#     )
#     popular_searches = serializers.ListField(
#         child=serializers.CharField(), required=False
#    )


# =============================================================================
# SUBSCRIPTION PLANS SERIALIZERS (NEW FROM FIGMA)
# =============================================================================


