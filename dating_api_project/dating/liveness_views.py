"""
Liveness Verification API Views
Endpoints for facial verification and liveness detection
"""

import uuid
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
import random

from .models import LivenessVerification, UserVerificationStatus
from .liveness_utils import (
    LivenessVerifier,
    AWSRekognitionVerifier,
    FacePlusPlusVerifier,
)
from .serializers import (
    LivenessVerificationSerializer,
    UserVerificationStatusSerializer,
)
from response_serializers import (
    StartLivenessResponseSerializer,
    CustomErrorResponseSerializer,
    SubmitLivenessRequestSerializer,
    SubmitLivenessResponseSerializer,
    SubmitLivenessImagesRequestSerializer,
    SubmitLivenessImagesResponseSerializer,
    RetryLivenessResponseSerializer,
    RetryLivenessRequestSerializer,
)
from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView


class StartLivenessCheckView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,  # explicitly declare no request body
        responses={
            200: StartLivenessResponseSerializer,
            201: StartLivenessResponseSerializer,
            500: CustomErrorResponseSerializer,
        },
    )
    def post(self, request):
        try:
            user = request.user

            # Check for existing active session
            existing_session = LivenessVerification.objects.filter(
                user=user,
                status__in=["pending", "in_progress"],
            ).first()

            if existing_session and not existing_session.is_expired():
                return Response(
                    {
                        "session_id": existing_session.session_id,
                        "status": existing_session.status,
                        "actions_required": existing_session.actions_required,
                        "message": "You have an active liveness check session",
                    },
                    status=status.HTTP_200_OK,
                )

            # Create new session
            all_actions = ["turn_left", "turn_right", "open_mouth", "smile", "blink"]
            actions_required = random.sample(all_actions, 3)

            session_id = uuid.uuid4()
            expires_at = timezone.now() + timedelta(minutes=10)

            liveness_check = LivenessVerification.objects.create(
                user=user,
                session_id=session_id,
                status="pending",
                actions_required=actions_required,
                expires_at=expires_at,
                verification_method="video",
            )

            return Response(
                {
                    "session_id": session_id,
                    "actions_required": actions_required,
                    "expires_at": expires_at,
                    "max_attempts": liveness_check.max_attempts,
                    "current_attempt": liveness_check.attempts_count,
                    "status": "pending",
                    "message": "Liveness check session started. Follow the instructions.",
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SubmitLivenessVideoView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SubmitLivenessRequestSerializer

    @extend_schema(
        request=SubmitLivenessRequestSerializer,
        responses={
            200: SubmitLivenessResponseSerializer,
            400: CustomErrorResponseSerializer,
            404: CustomErrorResponseSerializer,
            500: CustomErrorResponseSerializer,
        },
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = request.user
            session_id = serializer.validated_data["session_id"]
            video_data = serializer.validated_data["video_data"]

            try:
                liveness_check = LivenessVerification.objects.get(
                    session_id=session_id, user=user
                )
            except LivenessVerification.DoesNotExist:
                return Response(
                    {"error": "Invalid session ID or session not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if liveness_check.is_expired():
                liveness_check.status = "expired"
                liveness_check.save()
                return Response(
                    {"error": "Session expired. Please start a new liveness check."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if liveness_check.status in ["passed", "failed"]:
                return Response(
                    {"error": "Session already completed"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            liveness_check.status = "in_progress"
            liveness_check.save()

            result, error = LivenessVerifier.verify_liveness_from_video(
                video_data, liveness_check.actions_required
            )

            if error:
                liveness_check.status = "failed"
                liveness_check.save()
                return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

            liveness_check.is_live_person = result.get("is_live", False)
            liveness_check.confidence_score = result.get("confidence", 0.0)
            liveness_check.face_quality_score = result.get("face_match_score", 0.0)
            liveness_check.spoof_detected = result.get("spoof_detected", False)
            liveness_check.actions_completed = result.get("actions_detected", [])
            liveness_check.provider_response = result
            liveness_check.completed_at = timezone.now()

            if (
                result.get("is_live")
                and result.get("confidence", 0) >= 85
                and not result.get("spoof_detected")
                and len(result.get("actions_detected", []))
                >= len(liveness_check.actions_required)
            ):
                liveness_check.status = "passed"

                verification_status, _ = UserVerificationStatus.objects.get_or_create(
                    user=user
                )
                verification_status.liveness_verified = True
                verification_status.liveness_verified_at = timezone.now()
                verification_status.update_verification_level()

                message = "Liveness check passed! Your identity has been verified."
            else:
                liveness_check.status = "failed"
                message = "Liveness check failed. Please try again."

            liveness_check.save()

            return Response(
                {
                    "session_id": session_id,
                    "status": liveness_check.status,
                    "confidence": liveness_check.confidence_score,
                    "actions_completed": liveness_check.actions_completed,
                    "can_retry": liveness_check.can_retry(),
                    "message": message,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SubmitLivenessImagesView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SubmitLivenessImagesRequestSerializer

    @extend_schema(
        request=SubmitLivenessImagesRequestSerializer,
        responses={
            200: SubmitLivenessImagesResponseSerializer,
            400: CustomErrorResponseSerializer,
            404: CustomErrorResponseSerializer,
            500: CustomErrorResponseSerializer,
        },
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = request.user
            session_id = serializer.validated_data["session_id"]
            images = serializer.validated_data["images"]

            try:
                liveness_check = LivenessVerification.objects.get(
                    session_id=session_id, user=user
                )
            except LivenessVerification.DoesNotExist:
                return Response(
                    {"error": "Invalid session ID"}, status=status.HTTP_404_NOT_FOUND
                )

            if liveness_check.is_expired():
                liveness_check.status = "expired"
                liveness_check.save()
                return Response(
                    {"error": "Session expired"}, status=status.HTTP_400_BAD_REQUEST
                )

            liveness_check.status = "in_progress"
            liveness_check.verification_method = "images"
            liveness_check.save()

            images_data = [img["image_data"] for img in images]
            actions = [img["action"] for img in images]

            result, error = LivenessVerifier.verify_face_from_images(
                images_data, actions
            )

            if error:
                liveness_check.status = "failed"
                liveness_check.save()
                return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

            liveness_check.is_live_person = result.get("is_live", False)
            liveness_check.confidence_score = result.get("confidence", 0.0)
            liveness_check.spoof_detected = result.get("spoof_detected", False)
            liveness_check.actions_completed = result.get("actions_verified", [])
            liveness_check.provider_response = result
            liveness_check.completed_at = timezone.now()
            liveness_check.images_data = {"images": images}

            if (
                result.get("is_live")
                and result.get("confidence", 0) >= 85
                and not result.get("spoof_detected")
            ):
                liveness_check.status = "passed"

                verification_status, _ = UserVerificationStatus.objects.get_or_create(
                    user=user
                )
                verification_status.liveness_verified = True
                verification_status.liveness_verified_at = timezone.now()
                verification_status.update_verification_level()

                message = "Liveness check passed!"
            else:
                liveness_check.status = "failed"
                message = "Liveness check failed. Please try again."

            liveness_check.save()

            return Response(
                {
                    "session_id": session_id,
                    "status": liveness_check.status,
                    "confidence": liveness_check.confidence_score,
                    "can_retry": liveness_check.can_retry(),
                    "message": message,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LivenessCheckStatusView(GenericAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: LivenessVerificationSerializer,
            404: CustomErrorResponseSerializer,
        }
    )
    def get(self, request, session_id):
        try:
            liveness_check = LivenessVerification.objects.get(
                session_id=session_id, user=request.user
            )
        except LivenessVerification.DoesNotExist:
            return Response(
                {"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            LivenessVerificationSerializer(liveness_check).data,
            status=status.HTTP_200_OK,
        )


class UserVerificationStatusView(GenericAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserVerificationStatusSerializer})
    def get(self, request):
        verification_status, _ = UserVerificationStatus.objects.get_or_create(
            user=request.user
        )

        data = UserVerificationStatusSerializer(verification_status).data

        recent_checks = LivenessVerification.objects.filter(user=request.user)[:5]
        data["recent_liveness_checks"] = LivenessVerificationSerializer(
            recent_checks, many=True
        ).data

        return Response(data, status=status.HTTP_200_OK)


class RetryLivenessCheckView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RetryLivenessRequestSerializer

    @extend_schema(
        request=RetryLivenessRequestSerializer,
        responses={
            201: RetryLivenessResponseSerializer,
            400: CustomErrorResponseSerializer,
            404: CustomErrorResponseSerializer,
            500: CustomErrorResponseSerializer,
        },
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = request.user
            session_id = serializer.validated_data["session_id"]

            try:
                old_check = LivenessVerification.objects.get(
                    session_id=session_id, user=user
                )
            except LivenessVerification.DoesNotExist:
                return Response(
                    {"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND
                )

            if not old_check.can_retry():
                return Response(
                    {
                        "error": "Maximum retry attempts reached. Please start a new session."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            all_actions = ["turn_left", "turn_right", "open_mouth", "smile", "blink"]
            actions_required = random.sample(all_actions, 3)

            new_session_id = uuid.uuid4()
            expires_at = timezone.now() + timedelta(minutes=10)

            new_check = LivenessVerification.objects.create(
                user=user,
                session_id=new_session_id,
                status="pending",
                actions_required=actions_required,
                expires_at=expires_at,
                attempts_count=old_check.attempts_count + 1,
                max_attempts=old_check.max_attempts,
            )

            return Response(
                {
                    "session_id": new_session_id,
                    "actions_required": actions_required,
                    "expires_at": expires_at,
                    "attempt_number": new_check.attempts_count,
                    "max_attempts": new_check.max_attempts,
                    "message": "New liveness check session created",
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
