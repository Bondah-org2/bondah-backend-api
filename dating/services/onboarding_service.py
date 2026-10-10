"""
Onboarding, roles and account status (rebuild phase 11).

Roles
    A person has a *mode* they last chose (UserRoleSelection: love seeker or
    bondmaker) and, separately, whether Team Bondah approved them as a
    bondmaker (User.is_matchmaker). The mode alone never grants anything: the
    active mode is "bondmaker" only for approved bondmakers.

Onboarding
    state() is the single answer to "where should the app send this person".
    The app routes from it after sign-in, on launch and after each setup step,
    so an unfinished setup resumes on any device.

Bondmaker applications
    The ID document, selfie and a snapshot of the profile and answers are tied
    into one BondmakerApplication. Team Bondah approves it, rejects it (the
    person may apply again after REAPPLY_DAYS) or asks for changes (they fix
    and resubmit at once). One open application per person, enforced in the DB.

Account status
    banned: no sign-in and every request refused. restricted: read-only (see
    RESTRICTED_ALLOWED_VIEWS for the writes still allowed).
"""

import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from ..models import (
    AccountStatusChange,
    BondmakerApplication,
    DocumentVerification,
    SelfieVerification,
    UserRoleSelection,
    UserSecurityQuestion,
    UserSocialHandle,
)

logger = logging.getLogger(__name__)
User = get_user_model()

REAPPLY_DAYS = 30

LOVE_SEEKER = "looking_for_love"
BONDMAKER = "bondmaker"

# What a love seeker needs before others can see them and they can match
SEEKER_REQUIRED_FIELDS = ("name", "gender", "date_of_birth", "profile_picture", "preferred_gender")

# Answers the application asks for (the rest of QUESTION_TYPES stay optional)
APPLICATION_REQUIRED_ANSWERS = (
    "data_protection",
    "scam_prevention",
    "user_verification",
    "business_service",
    "relationship_guidance",
)
APPLICATION_REQUIRED_FIELDS = ("name", "gender", "date_of_birth", "username", "thought_leadership")

# Writes a restricted account may still make: signing out, keeping its
# devices and settings in order, reading notifications, leaving the platform.
RESTRICTED_ALLOWED_VIEWS = frozenset({
    "user-logout",
    "token-refresh",
    "device-register",
    "notification-settings",
    "language-settings",
    "preferences",
    "account-delete",
    "user-role-selection",
    "two-factor-setup",
    "two-factor-confirm",
    "two-factor-disable",
})

ACCOUNT_STATUSES = ("active", "restricted", "banned")


class OnboardingError(Exception):
    def __init__(self, code: str, message: str, missing: list | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.missing = missing or []


# ------------------------------------------------------------------- roles

def selected_role(user) -> str | None:
    return UserRoleSelection.objects.filter(user=user).values_list("selected_role", flat=True).first()


def set_selected_role(user, role: str) -> str:
    """Store the mode the person wants. Approval is still checked by active_mode()."""
    if role not in (LOVE_SEEKER, BONDMAKER):
        raise OnboardingError("invalid_role", "Unknown role.")
    UserRoleSelection.objects.update_or_create(user=user, defaults={"selected_role": role})
    return role


# --------------------------------------------------------- seeker profile

def seeker_missing(user) -> list[str]:
    return [f for f in SEEKER_REQUIRED_FIELDS if not getattr(user, f, None)]


# ----------------------------------------------------------- applications

def latest_application(user) -> BondmakerApplication | None:
    return (
        BondmakerApplication.objects.filter(user=user)
        .select_related("document", "selfie")
        .order_by("-submitted_at")
        .first()
    )


def _pending_document(user) -> DocumentVerification | None:
    return (
        DocumentVerification.objects.filter(user=user, status="pending")
        .order_by("-uploaded_at")
        .first()
    )


def _pending_selfie(document) -> SelfieVerification | None:
    if not document:
        return None
    return (
        SelfieVerification.objects.filter(document_verification=document, status="pending")
        .order_by("-created_at")
        .first()
    )


def application_missing(user) -> list[str]:
    """Codes for what the person still has to provide before submitting."""
    missing = [f for f in APPLICATION_REQUIRED_FIELDS if not getattr(user, f, None)]
    if not (user.bondmaker_profile_picture or user.profile_picture):
        missing.append("profile_picture")
    if not user.bondmaker_skills:
        missing.append("skills")

    answered = set(
        UserSecurityQuestion.objects.filter(user=user, question_type__in=APPLICATION_REQUIRED_ANSWERS)
        .exclude(response_text__isnull=True, response_choice__isnull=True)
        .values_list("question_type", flat=True)
    )
    missing += [f"answer:{q}" for q in APPLICATION_REQUIRED_ANSWERS if q not in answered]

    if not UserSocialHandle.objects.filter(user=user).exists():
        missing.append("social_handle")

    document = _pending_document(user)
    if not document or not document.front_image_url:
        missing.append("id_document")
    elif not _pending_selfie(document):
        missing.append("selfie")
    return missing


def apply_blocker(user, now=None) -> tuple[str, str] | None:
    """Why this person can't start or submit an application now, if anything."""
    now = now or timezone.now()
    if user.is_matchmaker:
        return ("already_bondmaker", "You are already a bondmaker.")
    app = latest_application(user)
    if app and app.status == "pending":
        return ("application_pending", "Your application is being reviewed.")
    if app and app.status == "rejected" and app.reapply_after and app.reapply_after > now:
        return ("reapply_later", "You can apply again after your waiting period ends.")
    return None


def _snapshot(user) -> dict:
    answers = {
        q.question_type: q.response_text if q.response_text is not None else q.response_choice
        for q in UserSecurityQuestion.objects.filter(user=user)
    }
    return {
        "name": user.name,
        "username": user.username,
        "gender": user.gender,
        "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
        "country": user.country,
        "city": user.city,
        "education_level": user.education_level,
        "relationship_status": user.relationship_status,
        "bondmaker_bio": user.bondmaker_bio,
        "thought_leadership": user.thought_leadership,
        "skills": list(user.bondmaker_skills or []),
        "answers": answers,
        "social_handles": [
            {"platform": h.platform, "url": h.url}
            for h in UserSocialHandle.objects.filter(user=user).order_by("platform")
        ],
    }


def submit_application(user, now=None) -> BondmakerApplication:
    now = now or timezone.now()
    with transaction.atomic():
        # Serialises two submits from the same person (double tap, two devices)
        User.objects.select_for_update().only("id").get(pk=user.pk)

        blocker = apply_blocker(user, now)
        if blocker:
            raise OnboardingError(*blocker)
        missing = application_missing(user)
        if missing:
            raise OnboardingError("incomplete", "Some parts of your application are missing.", missing)

        document = _pending_document(user)
        selfie = _pending_selfie(document)
        fields = {
            "document": document,
            "selfie": selfie,
            "snapshot": _snapshot(user),
            "status": "pending",
            "submitted_at": now,
            "reviewed_at": None,
            "reviewed_by": None,
            "review_note": "",
            "reapply_after": None,
        }
        reopened = BondmakerApplication.objects.filter(user=user, status="changes_requested").first()
        try:
            if reopened:
                for k, v in fields.items():
                    setattr(reopened, k, v)
                reopened.save()
                app = reopened
            else:
                app = BondmakerApplication.objects.create(user=user, **fields)
        except IntegrityError:
            raise OnboardingError("application_pending", "Your application is being reviewed.")
        set_selected_role(user, BONDMAKER)
    return app


def review_application(app_id: int, action: str, admin, note: str = "", redo_identity: bool = False, now=None):
    """approve | reject | request_changes. Only pending applications can be reviewed."""
    from ..tasks import notify_user, send_bondmaker_approval_email, send_bondmaker_rejection_email

    now = now or timezone.now()
    note = (note or "").strip()
    if action not in ("approve", "reject", "request_changes"):
        raise OnboardingError("invalid_action", "Unknown action.")
    if action in ("reject", "request_changes") and not note:
        raise OnboardingError("note_required", "Tell the applicant why.")

    with transaction.atomic():
        app = (
            BondmakerApplication.objects.select_for_update()
            .select_related("user", "document", "selfie")
            .get(pk=app_id)
        )
        if app.status != "pending":
            raise OnboardingError("already_reviewed", "This application was already reviewed.")
        user = app.user
        document, selfie = app.document, app.selfie

        app.reviewed_at = now
        app.reviewed_by = admin
        app.review_note = note

        if action == "approve":
            app.status = "approved"
            document.status = "approved"
            document.is_authentic = True
            document.verified_at = now
            if selfie:
                selfie.status, selfie.is_match, selfie.verified_at = "approved", True, now
            user.is_matchmaker = True
            user.save(update_fields=["is_matchmaker"])
            set_selected_role(user, BONDMAKER)
        elif action == "reject":
            app.status = "rejected"
            app.reapply_after = now + timedelta(days=REAPPLY_DAYS)
            document.status = "rejected"
            document.rejection_reason = note
            if selfie:
                selfie.status, selfie.is_match = "rejected", False
        else:
            app.status = "changes_requested"
            if redo_identity:
                # A new ID scan and selfie are needed; the old ones can't be reused
                document.status = "rejected"
                document.rejection_reason = note
                if selfie:
                    selfie.status, selfie.is_match = "rejected", False

        document.processed_at = now
        document.save()
        if selfie:
            selfie.save()
        app.save()

        titles = {
            "approve": ("Application approved", "Welcome to Team Bondah. You can now use bondmaker mode."),
            "reject": ("Application not approved", note),
            "request_changes": ("Changes needed on your application", note),
        }
        title, message = titles[action]
        data = {"type": "bondmaker_application", "status": app.status, "application_id": app.id}

        def _after_commit():
            notify_user.delay(user_id=user.id, title=title, message=message, data=data)
            try:
                if action == "approve":
                    send_bondmaker_approval_email.delay(user.name, user.email)
                elif action == "reject":
                    send_bondmaker_rejection_email.delay(user.name, user.email, note)
            except Exception:
                logger.error("Application email for user %s not queued", user.id, exc_info=True)

        transaction.on_commit(_after_commit)
    return app


def application_payload(app: BondmakerApplication | None, now=None) -> dict | None:
    if not app:
        return None
    now = now or timezone.now()
    redo_identity = app.status == "changes_requested" and app.document.status == "rejected"
    return {
        "id": app.id,
        "status": app.status,
        "submitted_at": app.submitted_at,
        "reviewed_at": app.reviewed_at,
        "review_note": app.review_note if app.status in ("rejected", "changes_requested") else "",
        "reapply_after": app.reapply_after,
        "can_reapply": app.status == "rejected" and (not app.reapply_after or app.reapply_after <= now),
        "redo_identity": redo_identity,
    }


# ------------------------------------------------------------------- state

def active_mode(user, role: str | None, seeker_complete: bool) -> str | None:
    if role == BONDMAKER and user.is_matchmaker:
        return "bondmaker"
    if role is None and user.is_matchmaker:
        return "bondmaker"
    if seeker_complete:
        return "love_seeker"
    return None


def state(user, now=None) -> dict:
    """Where the app should send this person, and why."""
    now = now or timezone.now()
    role = selected_role(user)
    missing = seeker_missing(user)
    seeker_complete = not missing
    mode = active_mode(user, role, seeker_complete)
    app = None if user.is_matchmaker else latest_application(user)
    application = application_payload(app, now)

    if role == LOVE_SEEKER:
        # An approved bondmaker who switched to seeker mode without a seeker profile lands here too
        next_step = "app" if seeker_complete else "seeker_setup"
    elif role == BONDMAKER:
        if user.is_matchmaker or seeker_complete:
            next_step = "app"
        elif app and (app.is_open or not application["can_reapply"]):
            next_step = "application_status"
        else:
            next_step = "bondmaker_setup"
    else:
        next_step = "app" if mode else "choose_role"

    # Someone mid-application in seeker mode shouldn't be dropped into bondmaker mode
    if next_step == "app" and mode is None:
        next_step = "seeker_setup"

    payload = {
        "next": next_step,
        "selected_role": role,
        "active_mode": mode if next_step == "app" else None,
        "is_bondmaker": user.is_matchmaker,
        "account": {
            "status": user.status,
            "reason": user.status_reason if user.status != "active" else "",
        },
        "seeker_profile": {"complete": seeker_complete, "missing": missing},
        "bondmaker_application": application,
    }
    # Anyone working toward an application (also a seeker applying from inside
    # the app) gets the list, so the app opens the first unfinished step
    if not user.is_matchmaker and (role == BONDMAKER or next_step == "bondmaker_setup"):
        payload["application_missing"] = application_missing(user)
    return payload


# ---------------------------------------------------------- account status

def set_account_status(user, status: str, *, reason: str = "", by=None) -> User:
    from .account_service import _sign_out_everywhere
    from ..tasks import notify_user

    if status not in ACCOUNT_STATUSES:
        raise OnboardingError("invalid_status", "Unknown account status.")
    if user.is_principal_admin:
        raise OnboardingError("protected_account", "The principal admin's status can't be changed.")
    reason = (reason or "").strip()
    if status != "active" and not reason:
        raise OnboardingError("reason_required", "Give a reason the user will see.")

    with transaction.atomic():
        locked = User.objects.select_for_update().get(pk=user.pk)
        previous = locked.status
        if previous == status and locked.status_reason == reason:
            return locked
        locked.status = status
        locked.status_reason = reason if status != "active" else ""
        locked.save(update_fields=["status", "status_reason"])
        AccountStatusChange.objects.create(
            user=locked, from_status=previous, to_status=status, reason=reason, changed_by=by
        )
        if status == "banned":
            transaction.on_commit(lambda: _sign_out_everywhere(locked))
        elif status == "restricted":
            transaction.on_commit(lambda: notify_user.delay(
                user_id=locked.id,
                title="Your account is restricted",
                message=reason,
                data={"type": "account_status", "status": status},
            ))
    return locked
