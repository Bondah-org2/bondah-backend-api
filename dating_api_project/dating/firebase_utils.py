"""
Firebase utilities for the dating app.
Handles authentication, Firestore operations, and Firebase Cloud Messaging.
"""

import firebase_admin
from firebase_admin import auth, firestore, messaging
from django.conf import settings
from .models.users import User  # Import your User model
import logging
from firebase_admin import credentials
from typing import Optional, Dict
from .models import DeviceRegistration
from firebase_admin.exceptions import FirebaseError
from .circuit_breakers import firebase_breaker

logger = logging.getLogger(__name__)

# Remove global Firestore client initialization - will be lazy loaded
_db = None


def get_firestore_client():
    """Get Firestore client with lazy initialization"""
    global _db
    if _db is None:
        # Ensure Firebase is initialized
        if not firebase_admin._apps:
            # This should have been initialized in settings.py, but just in case
            if (
                hasattr(settings, "FIREBASE_CREDENTIALS_JSON")
                and settings.FIREBASE_CREDENTIALS_JSON
            ):
                import json

                cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
                cred = credentials.Certificate(cred_dict)
            else:
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
        _db = firestore.client()
    return _db


def ensure_firestore_user_document(uid, user):
    """
    Ensure a Firestore user document exists for this UID.
    Idempotent: safe to call anytime.
    """
    try:
        db = get_firestore_client()
        doc_ref = db.collection("users").document(uid)
        doc = doc_ref.get()

        if not doc.exists:
            doc_ref.set(
                {
                    "email": user.email,
                    "name": user.name,
                    "bio": "",
                    "interests": [],
                    "photos": [],
                    "created_at": firestore.SERVER_TIMESTAMP,
                }
            )
    except Exception as e:
        logger.error(f"Error ensuring Firestore user document: {e}")


def verify_firebase_token(id_token):
    """
    Verify a Firebase ID token and return decoded claims.
    Used for authenticating users in views.
    """
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token  # Contains uid, email, etc.
    except Exception as e:
        logger.error(f"Firebase token verification failed: {e}")
        return None


def get_or_create_user_from_firebase(decoded_token):
    uid = decoded_token["uid"]
    email = decoded_token.get("email")
    name = decoded_token.get("name", "")

    user = User.objects.filter(email=email).first()

    if not user:
        user = User.objects.create_user(
            username=email,
            email=email,
            name=name,
        )

    # GUARANTEE FIRESTORE DOC EXISTS FOR EVERY USER
    ensure_firestore_user_document(uid, user)

    return user


def get_user_profile_from_firestore(uid):
    try:
        db = get_firestore_client()
        doc_ref = db.collection("users").document(uid)
        doc = doc_ref.get(timeout=3)

        if doc.exists:
            return doc.to_dict()

        return None

    except Exception as e:
        logger.error(f"Error fetching user profile from Firestore: {e}")
        return None


def update_user_profile_in_firestore(uid, data):
    """
    Update user profile in Firestore.
    Data should be a dict of fields to update.
    """
    try:
        db = get_firestore_client()
        doc_ref = db.collection("users").document(uid)
        doc_ref.set(data, merge=True)  # Merge to update existing fields
        return True
    except Exception as e:
        logger.error(f"Error updating user profile in Firestore: {e}")
        return False


@firebase_breaker
def send_push_notification(token, title, body, data=None):
    if not token:
        return None

    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
        )

        return messaging.send(message)

    except FirebaseError as e:
        error_str = str(e)

        #  Handle invalid tokens
        if "registration-token-not-registered" in error_str:
            DeviceRegistration.objects.filter(push_token=token).update(
                is_active=False
            )

        logger.error(f"FCM error: {e}")
        return None


def get_matches_for_user(uid):
    """
    Retrieve matches for a user from Firestore.
    """
    try:
        db = get_firestore_client()
        matches = []
        query = db.collection("matches").where("user1", "==", uid).stream()
        for doc in query:
            matches.append(doc.to_dict())
        query2 = db.collection("matches").where("user2", "==", uid).stream()
        for doc in query2:
            matches.append(doc.to_dict())
        return matches
    except Exception as e:
        logger.error(f"Error fetching matches: {e}")
        return []


def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)
