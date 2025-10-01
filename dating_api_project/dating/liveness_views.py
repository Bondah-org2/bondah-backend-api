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

from .models import LivenessVerification, UserVerificationStatus
from .liveness_utils import LivenessVerifier, AWSRekognitionVerifier, FacePlusPlusVerifier
from .serializers import LivenessVerificationSerializer, UserVerificationStatusSerializer

User = get_user_model()


class StartLivenessCheckView(APIView):
    """
    Start a new liveness verification session
    
    POST /api/liveness/start/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            user = request.user
            
            # Check if user has a pending/in-progress session
            existing_session = LivenessVerification.objects.filter(
                user=user,
                status__in=['pending', 'in_progress']
            ).first()
            
            if existing_session and not existing_session.is_expired():
                return Response({
                    'session_id': existing_session.session_id,
                    'status': existing_session.status,
                    'actions_required': existing_session.actions_required,
                    'message': 'You have an active liveness check session'
                }, status=status.HTTP_200_OK)
            
            # Generate random actions for verification
            import random
            all_actions = ['turn_left', 'turn_right', 'open_mouth', 'smile', 'blink']
            actions_required = random.sample(all_actions, 3)  # Require 3 actions
            
            # Create new session
            session_id = str(uuid.uuid4())
            expires_at = timezone.now() + timedelta(minutes=10)  # 10 min expiry
            
            liveness_check = LivenessVerification.objects.create(
                user=user,
                session_id=session_id,
                status='pending',
                actions_required=actions_required,
                expires_at=expires_at,
                verification_method='video'
            )
            
            return Response({
                'session_id': session_id,
                'actions_required': actions_required,
                'expires_at': expires_at.isoformat(),
                'max_attempts': liveness_check.max_attempts,
                'current_attempt': liveness_check.attempts_count,
                'message': 'Liveness check session started. Follow the instructions.'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SubmitLivenessVideoView(APIView):
    """
    Submit video for liveness verification
    
    POST /api/liveness/submit/video/
    Body: {
        "session_id": "uuid",
        "video_data": "base64_encoded_video",
        "format": "mp4/webm/mov"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            user = request.user
            session_id = request.data.get('session_id')
            video_data = request.data.get('video_data')
            
            if not session_id or not video_data:
                return Response({
                    'error': 'session_id and video_data are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get session
            try:
                liveness_check = LivenessVerification.objects.get(
                    session_id=session_id,
                    user=user
                )
            except LivenessVerification.DoesNotExist:
                return Response({
                    'error': 'Invalid session ID or session not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check if expired
            if liveness_check.is_expired():
                liveness_check.status = 'expired'
                liveness_check.save()
                return Response({
                    'error': 'Session expired. Please start a new liveness check.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if already completed
            if liveness_check.status in ['passed', 'failed']:
                return Response({
                    'error': 'Session already completed'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update status
            liveness_check.status = 'in_progress'
            liveness_check.save()
            
            # Verify liveness
            result, error = LivenessVerifier.verify_liveness_from_video(
                video_data,
                liveness_check.actions_required
            )
            
            if error:
                liveness_check.status = 'failed'
                liveness_check.save()
                return Response({
                    'error': error
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update verification record
            liveness_check.is_live_person = result.get('is_live', False)
            liveness_check.confidence_score = result.get('confidence', 0.0)
            liveness_check.face_quality_score = result.get('face_match_score', 0.0)
            liveness_check.spoof_detected = result.get('spoof_detected', False)
            liveness_check.actions_completed = result.get('actions_detected', [])
            liveness_check.provider_response = result
            liveness_check.completed_at = timezone.now()
            
            # Determine if passed (confidence > 85%, all actions detected, no spoof)
            if (result.get('is_live') and 
                result.get('confidence', 0) >= 85 and 
                not result.get('spoof_detected') and
                len(result.get('actions_detected', [])) >= len(liveness_check.actions_required)):
                liveness_check.status = 'passed'
                
                # Update user verification status
                verification_status, created = UserVerificationStatus.objects.get_or_create(
                    user=user
                )
                verification_status.liveness_verified = True
                verification_status.liveness_verified_at = timezone.now()
                verification_status.update_verification_level()
                
                message = 'Liveness check passed! Your identity has been verified.'
            else:
                liveness_check.status = 'failed'
                message = 'Liveness check failed. Please try again.'
            
            liveness_check.save()
            
            return Response({
                'session_id': session_id,
                'status': liveness_check.status,
                'confidence': liveness_check.confidence_score,
                'actions_completed': liveness_check.actions_completed,
                'can_retry': liveness_check.can_retry(),
                'message': message
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SubmitLivenessImagesView(APIView):
    """
    Submit multiple images for liveness verification (alternative to video)
    
    POST /api/liveness/submit/images/
    Body: {
        "session_id": "uuid",
        "images": [
            {"action": "turn_left", "image_data": "base64..."},
            {"action": "turn_right", "image_data": "base64..."},
            {"action": "open_mouth", "image_data": "base64..."}
        ]
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            user = request.user
            session_id = request.data.get('session_id')
            images = request.data.get('images', [])
            
            if not session_id or not images:
                return Response({
                    'error': 'session_id and images are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get session
            try:
                liveness_check = LivenessVerification.objects.get(
                    session_id=session_id,
                    user=user
                )
            except LivenessVerification.DoesNotExist:
                return Response({
                    'error': 'Invalid session ID'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check if expired
            if liveness_check.is_expired():
                liveness_check.status = 'expired'
                liveness_check.save()
                return Response({
                    'error': 'Session expired'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update status
            liveness_check.status = 'in_progress'
            liveness_check.verification_method = 'images'
            liveness_check.save()
            
            # Extract image data and actions
            images_data = [img['image_data'] for img in images]
            actions = [img['action'] for img in images]
            
            # Verify liveness
            result, error = LivenessVerifier.verify_face_from_images(
                images_data,
                actions
            )
            
            if error:
                liveness_check.status = 'failed'
                liveness_check.save()
                return Response({
                    'error': error
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update verification record
            liveness_check.is_live_person = result.get('is_live', False)
            liveness_check.confidence_score = result.get('confidence', 0.0)
            liveness_check.spoof_detected = result.get('spoof_detected', False)
            liveness_check.actions_completed = result.get('actions_verified', [])
            liveness_check.provider_response = result
            liveness_check.completed_at = timezone.now()
            liveness_check.images_data = {'images': images}
            
            # Determine if passed
            if (result.get('is_live') and 
                result.get('confidence', 0) >= 85 and 
                not result.get('spoof_detected')):
                liveness_check.status = 'passed'
                
                # Update user verification status
                verification_status, created = UserVerificationStatus.objects.get_or_create(
                    user=user
                )
                verification_status.liveness_verified = True
                verification_status.liveness_verified_at = timezone.now()
                verification_status.update_verification_level()
                
                message = 'Liveness check passed!'
            else:
                liveness_check.status = 'failed'
                message = 'Liveness check failed. Please try again.'
            
            liveness_check.save()
            
            return Response({
                'session_id': session_id,
                'status': liveness_check.status,
                'confidence': liveness_check.confidence_score,
                'can_retry': liveness_check.can_retry(),
                'message': message
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LivenessCheckStatusView(APIView):
    """
    Get status of a liveness check session
    
    GET /api/liveness/status/<session_id>/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, session_id):
        try:
            user = request.user
            
            try:
                liveness_check = LivenessVerification.objects.get(
                    session_id=session_id,
                    user=user
                )
            except LivenessVerification.DoesNotExist:
                return Response({
                    'error': 'Session not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = LivenessVerificationSerializer(liveness_check)
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserVerificationStatusView(APIView):
    """
    Get user's overall verification status
    
    GET /api/verification/status/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user
            
            verification_status, created = UserVerificationStatus.objects.get_or_create(
                user=user
            )
            
            serializer = UserVerificationStatusSerializer(verification_status)
            
            # Include recent liveness checks
            recent_checks = LivenessVerification.objects.filter(
                user=user
            )[:5]
            
            recent_checks_data = LivenessVerificationSerializer(recent_checks, many=True).data
            
            response_data = serializer.data
            response_data['recent_liveness_checks'] = recent_checks_data
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RetryLivenessCheckView(APIView):
    """
    Retry a failed liveness check
    
    POST /api/liveness/retry/
    Body: {"session_id": "uuid"}
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            user = request.user
            session_id = request.data.get('session_id')
            
            if not session_id:
                return Response({
                    'error': 'session_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                old_check = LivenessVerification.objects.get(
                    session_id=session_id,
                    user=user
                )
            except LivenessVerification.DoesNotExist:
                return Response({
                    'error': 'Session not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check if can retry
            if not old_check.can_retry():
                return Response({
                    'error': 'Maximum retry attempts reached. Please start a new session.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create new session
            import random
            all_actions = ['turn_left', 'turn_right', 'open_mouth', 'smile', 'blink']
            actions_required = random.sample(all_actions, 3)
            
            new_session_id = str(uuid.uuid4())
            expires_at = timezone.now() + timedelta(minutes=10)
            
            new_check = LivenessVerification.objects.create(
                user=user,
                session_id=new_session_id,
                status='pending',
                actions_required=actions_required,
                expires_at=expires_at,
                attempts_count=old_check.attempts_count + 1,
                max_attempts=old_check.max_attempts
            )
            
            return Response({
                'session_id': new_session_id,
                'actions_required': actions_required,
                'expires_at': expires_at.isoformat(),
                'attempt_number': new_check.attempts_count,
                'max_attempts': new_check.max_attempts,
                'message': 'New liveness check session created'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

