"""
Liveness Detection Utilities for Facial Verification
Provides face detection, liveness check, and anti-spoofing functionality
"""

import base64
import io
import json
import os
from PIL import Image
from django.conf import settings


class LivenessVerifier:
    """
    Handle liveness detection and facial verification
    
    This can integrate with:
    - AWS Rekognition
    - Azure Face API
    - Google Cloud Vision
    - Face++ API
    - Custom ML model
    """
    
    @staticmethod
    def verify_liveness_from_video(video_data, actions_required):
        """
        Verify liveness from video frames
        
        Args:
            video_data: Base64 encoded video or list of frames
            actions_required: List of actions ['turn_left', 'turn_right', 'open_mouth', 'smile']
        
        Returns:
            dict: {
                'is_live': True/False,
                'confidence': 0-100,
                'actions_detected': ['turn_left', ...],
                'face_quality': 'good'/'poor',
                'message': 'Verification successful'
            }
        """
        try:
            # In production, this would call actual face detection API
            # For now, we'll return a mock response structure
            
            result = {
                'is_live': True,
                'confidence': 95.5,
                'actions_detected': actions_required,
                'face_quality': 'good',
                'face_match_score': 98.2,
                'spoof_detected': False,
                'message': 'Liveness verification successful'
            }
            
            return result, None
            
        except Exception as e:
            return None, str(e)
    
    @staticmethod
    def verify_face_from_images(images_data, actions_required):
        """
        Verify liveness from multiple images (one per action)
        
        Args:
            images_data: List of base64 encoded images
            actions_required: List of corresponding actions
        
        Returns:
            dict: Verification result
        """
        try:
            if len(images_data) != len(actions_required):
                return None, "Number of images must match number of actions"
            
            # Decode and validate images
            faces_detected = []
            for img_data in images_data:
                face_data = LivenessVerifier._process_image(img_data)
                if face_data:
                    faces_detected.append(face_data)
            
            if len(faces_detected) < len(actions_required):
                return None, "Could not detect face in all images"
            
            result = {
                'is_live': True,
                'confidence': 93.0,
                'actions_verified': actions_required,
                'faces_detected': len(faces_detected),
                'face_quality': 'good',
                'spoof_detected': False,
                'message': 'All liveness checks passed'
            }
            
            return result, None
            
        except Exception as e:
            return None, str(e)
    
    @staticmethod
    def _process_image(base64_image):
        """Process and validate a single image"""
        try:
            # Remove data URL prefix if present
            if ',' in base64_image:
                base64_image = base64_image.split(',')[1]
            
            # Decode base64
            image_data = base64.b64decode(base64_image)
            image = Image.open(io.BytesIO(image_data))
            
            # Basic validations
            if image.size[0] < 300 or image.size[1] < 300:
                return None  # Image too small
            
            # In production, run face detection here
            face_detected = {
                'width': image.size[0],
                'height': image.size[1],
                'face_found': True,
                'quality': 'good'
            }
            
            return face_detected
            
        except Exception:
            return None
    
    @staticmethod
    def compare_faces(reference_image, comparison_image):
        """
        Compare two face images for matching
        Used to verify if the same person across multiple checks
        
        Returns:
            dict: {
                'match': True/False,
                'similarity': 0-100,
                'confidence': 0-100
            }
        """
        try:
            # In production, use actual face comparison API
            result = {
                'match': True,
                'similarity': 96.5,
                'confidence': 98.0,
                'message': 'Faces match'
            }
            
            return result, None
            
        except Exception as e:
            return None, str(e)
    
    @staticmethod
    def detect_spoof(image_data):
        """
        Detect if image is from a real person or spoofed (photo/video)
        
        Returns:
            dict: {
                'is_real': True/False,
                'spoof_type': None/'photo'/'video'/'mask',
                'confidence': 0-100
            }
        """
        try:
            # In production, use anti-spoofing detection
            result = {
                'is_real': True,
                'spoof_type': None,
                'confidence': 97.5,
                'message': 'Real person detected'
            }
            
            return result, None
            
        except Exception as e:
            return None, str(e)


class AWSRekognitionVerifier:
    """
    AWS Rekognition integration for production use
    Requires: boto3, AWS credentials
    """
    
    @staticmethod
    def verify_liveness_session(session_id, video_data):
        """
        Use AWS Rekognition Face Liveness
        
        This requires:
        1. AWS account with Rekognition enabled
        2. boto3 installed
        3. AWS credentials configured
        """
        try:
            # import boto3  # Uncomment when ready
            
            # client = boto3.client('rekognition', 
            #                      region_name='us-east-1',
            #                      aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            #                      aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
            
            # response = client.detect_faces(
            #     Image={'Bytes': video_data},
            #     Attributes=['ALL']
            # )
            
            # For now, return mock
            result = {
                'liveness_check': 'PASSED',
                'confidence': 99.5,
                'session_id': session_id
            }
            
            return result, None
            
        except Exception as e:
            return None, str(e)


class FacePlusPlusVerifier:
    """
    Face++ API integration (alternative to AWS)
    More affordable and easier to set up
    """
    
    FACE_PLUS_PLUS_API_KEY = os.getenv('FACEPP_API_KEY', '')
    FACE_PLUS_PLUS_API_SECRET = os.getenv('FACEPP_API_SECRET', '')
    
    @staticmethod
    def verify_liveness(image_data):
        """
        Use Face++ API for liveness detection
        
        Endpoint: https://api-us.faceplusplus.com/facepp/v1/face/thousandlandmarks
        """
        try:
            import requests
            
            if not FacePlusPlusVerifier.FACE_PLUS_PLUS_API_KEY:
                return None, "Face++ API key not configured"
            
            # In production, make actual API call
            # response = requests.post(
            #     'https://api-us.faceplusplus.com/facepp/v3/detect',
            #     data={
            #         'api_key': FacePlusPlusVerifier.FACE_PLUS_PLUS_API_KEY,
            #         'api_secret': FacePlusPlusVerifier.FACE_PLUS_PLUS_API_SECRET,
            #         'image_base64': image_data,
            #         'return_attributes': 'eyestatus,facequality'
            #     }
            # )
            
            result = {
                'faces': 1,
                'liveness_passed': True,
                'confidence': 97.0
            }
            
            return result, None
            
        except Exception as e:
            return None, str(e)

