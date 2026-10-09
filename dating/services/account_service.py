"""
Deleting an account (rebuild phase 10).

A request hides the account straight away (is_active=False, so every list,
deck and search that filters on is_active drops it) and signs out every
device. For 30 days, signing in again cancels the deletion. After that,
purge_due_accounts wipes the personal data but keeps the user row, so the coin
ledger, withdrawals, gifts and store records stay intact for accounting.

Deletion is refused while money is in flight: a pending withdrawal, or coins
held for a match request or private visibility. Whatever is left in the
wallet is forfeited at purge time, in the ledger like every other movement.
"""

import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from ..models import Wallet, WalletTransaction, Withdrawal
from . import wallet_service

logger = logging.getLogger(__name__)
User = get_user_model()

GRACE_DAYS = 30

# Uploads that belong to other people's conversations stay readable for them.
KEEP_UPLOAD_PURPOSES = ("chat_image", "chat_video", "chat_voice_note")


class DeletionBlocked(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def blockers(user) -> list[dict]:
    """Reasons this account can't be deleted yet; empty when it can."""
    reasons = []
    if Withdrawal.objects.filter(user=user, status="pending").exists():
        reasons.append({
            "code": "withdrawal_pending",
            "message": "You have a withdrawal in progress. Wait for it to finish or cancel it first.",
        })
    if WalletTransaction.objects.filter(user=user, status=wallet_service.HOLD_PENDING).exists():
        reasons.append({
            "code": "coins_on_hold",
            "message": "Some of your coins are on hold for a request. Wait for it to be answered or expire first.",
        })
    return reasons


def overview(user) -> dict:
    """What the delete screen shows before the user confirms."""
    wallet = Wallet.objects.filter(user=user).first()
    return {
        "can_delete": not blockers(user),
        "blockers": blockers(user),
        "coins_forfeited": wallet.available_balance if wallet else 0,
        "grace_days": GRACE_DAYS,
        "requires_password": user.has_usable_password(),
        "scheduled_for": user.deletion_scheduled_for,
    }


def _sign_out_everywhere(user):
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

    from ..models import DeviceRegistration

    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)
    DeviceRegistration.objects.filter(user=user).update(is_active=False)


def request_deletion(user, *, password: str = "", now=None):
    now = now or timezone.now()
    if user.has_usable_password() and not user.check_password(password or ""):
        raise DeletionBlocked("wrong_password", "That password is not right.")

    with transaction.atomic():
        # Lock the wallet so a hold or withdrawal can't start between the check and the request
        wallet_service.lock_wallet(user)
        reasons = blockers(user)
        if reasons:
            raise DeletionBlocked(reasons[0]["code"], reasons[0]["message"])
        user.deletion_requested_at = now
        user.deletion_scheduled_for = now + timedelta(days=GRACE_DAYS)
        user.is_active = False
        user.save(update_fields=["deletion_requested_at", "deletion_scheduled_for", "is_active"])
        transaction.on_commit(lambda: _sign_out_everywhere(user))
    return user


def pending_deletion(user) -> bool:
    return bool(user.deletion_requested_at and not user.deleted_at)


def cancel_deletion(user) -> bool:
    """Called when the user signs in during the grace period. True if one was cancelled."""
    if not pending_deletion(user):
        return False
    user.deletion_requested_at = None
    user.deletion_scheduled_for = None
    user.is_active = True
    user.save(update_fields=["deletion_requested_at", "deletion_scheduled_for", "is_active"])
    return True


def find_for_sign_in(email: str, password: str):
    """The account a correct password is trying to bring back, if it is pending deletion."""
    user = User.objects.filter(email__iexact=email, deletion_requested_at__isnull=False, deleted_at__isnull=True).first()
    if user and user.check_password(password):
        return user
    return None


# ------------------------------------------------------------------- purge

# Personal fields wiped from the user row. Anything not listed keeps its default.
_BLANK_FIELDS = (
    "first_name", "last_name", "pending_email", "phone_number", "location", "address", "city",
    "state", "postal_code", "bio", "deal_breaker", "ethnicity", "education_level", "height",
    "zodiac_sign", "genotype", "relationship_status", "smoking_preference", "drinking_preference",
    "pet_preference", "exercise_frequency", "personality_type", "love_language",
    "communication_style", "marriage_plans", "want_kids", "have_kids", "future_kids",
    "religion_importance", "religion", "dating_type", "open_to_long_distance", "looking_for",
    "job_title", "company_name", "bondmaker_bio", "thought_leadership",
)
_NULL_FIELDS = (
    "date_of_birth", "latitude", "longitude", "profile_picture", "bondmaker_profile_picture",
    "bondmaker_cover_picture", "last_location_update", "last_seen", "last_active", "last_used",
    "no_of_kids", "gender", "preferred_gender",
)
_EMPTY_LIST_FIELDS = ("traits", "partner_qualities", "profile_gallery", "languages", "hobbies", "interests")


def _model_field(name):
    try:
        return User._meta.get_field(name)
    except Exception:
        return None


def _wipe_row(user, now):
    for name in _BLANK_FIELDS + _NULL_FIELDS:
        field = _model_field(name)
        if field is None:
            continue
        if field.null:
            setattr(user, name, None)
        elif field.has_default():
            setattr(user, name, field.get_default())
        else:
            setattr(user, name, "")
    for name in _EMPTY_LIST_FIELDS:
        if _model_field(name) is not None:
            setattr(user, name, [])
    user.name = "Deleted user"
    user.email = f"deleted-{user.pk}@deleted.bondah.invalid"
    user.username = None
    user.is_matchmaker = False
    user.is_active = False
    user.push_notifications_enabled = False
    user.email_notifications_enabled = False
    user.set_unusable_password()
    user.deleted_at = now
    user.save()


def _delete_personal_records(user):
    from .. import models as m

    # Identity, security and tracking records: nobody else needs these.
    for model, field in (
        ("DeviceRegistration", "user"), ("LocationHistory", "user"), ("LocationPermission", "user"),
        ("SearchQuery", "user"), ("FeedSearch", "user"), ("UserSocialHandle", "user"),
        ("UserSecurityQuestion", "user"), ("DocumentVerification", "user"),
        ("SelfieVerification", "user"), ("LivenessVerification", "user"),
        ("PhoneVerification", "user"), ("EmailVerification", "user"), ("SecurityPin", "user"),
        ("TwoFactorAuth", "user"), ("UserProfileView", "viewer"), ("UserProfileView", "viewed_user"),
        ("RecommendationEngine", "user"), ("RecommendationEngine", "recommended_user"),
        ("Notification", "user"), ("Activity", "actor"), ("Activity", "recipient"),
        ("Visibility", "owner"), ("Visibility", "bondmaker"), ("BondmakerSubscription", "user"), ("BondmakerSubscription", "bondmaker"),
        ("SuggestedMatch", "user"), ("SuggestedMatch", "suggested_user"),
        ("BondCircleMember", "user"), ("BondCirclePostLike", "user"), ("BondCirclePostComment", "user"),
        ("BondCirclePost", "author"), ("Story", "author"), ("StoryView", "viewer"),
        ("StoryInteraction", "user"), ("PostShare", "user"),
    ):
        model_cls = getattr(m, model, None)
        if model_cls is not None:
            model_cls.objects.filter(**{field: user}).delete()

    # Allauth and DRF token rows (social logins, legacy tokens)
    for app_label, model in (("socialaccount", "SocialAccount"), ("account", "EmailAddress"), ("authtoken", "Token")):
        try:
            from django.apps import apps

            apps.get_model(app_label, model).objects.filter(user=user).delete()
        except LookupError:
            pass

    # Bond Story: their posts go; their comments and likes on other posts go, with counters fixed.
    m.Post.objects.filter(author=user).delete()
    touched = list(
        m.PostComment.objects.filter(author=user).values_list("post_id", flat=True).distinct()
    ) + list(m.PostInteraction.objects.filter(user=user).values_list("post_id", flat=True).distinct())
    m.CommentInteraction.objects.filter(user=user).delete()
    m.PostComment.objects.filter(author=user).delete()
    m.PostInteraction.objects.filter(user=user).delete()
    for post in m.Post.objects.filter(pk__in=set(touched)).annotate(
        n_comments=Count("comments", filter=Q(comments__is_active=True), distinct=True),
        n_likes=Count("interactions", filter=Q(interactions__interaction_type="like"), distinct=True),
    ):
        m.Post.objects.filter(pk=post.pk).update(comments_count=post.n_comments, likes_count=post.n_likes)

    # Files: everything they uploaded except media inside chats with other people
    m.MediaUpload.objects.filter(owner=user).exclude(purpose__in=KEEP_UPLOAD_PURPOSES).update(status="deleted")


def _settle_money(user):
    """Release anything still held for or by them, then forfeit the balance."""
    from .. import models as m

    for tx_id in WalletTransaction.objects.filter(user=user, status=wallet_service.HOLD_PENDING).values_list("pk", flat=True):
        wallet_service.release(tx_id)
    # Requests waiting on them as the bondmaker give the seekers their coins back
    for request in m.MatchRequest.objects.filter(bondmaker=user, status="pending").exclude(hold_transaction=None):
        wallet_service.release(request.hold_transaction_id)
    m.MatchRequest.objects.filter(Q(bondmaker=user) | Q(requester=user), status="pending").update(status="cancelled")
    # Seekers' private visibility (and renewals) waiting on them as the bondmaker
    for hold_id, renewal_id in m.Visibility.objects.filter(bondmaker=user).values_list(
        "hold_transaction_id", "renewal_hold_transaction_id"
    ):
        for tx_id in (hold_id, renewal_id):
            if tx_id:
                wallet_service.release(tx_id)

    wallet = Wallet.objects.filter(user=user).first()
    if wallet and wallet.available_balance > 0:
        wallet_service.debit(
            user, wallet.available_balance, kind="account_deleted",
            idempotency_key=f"account-deleted:{user.pk}",
        )


def purge(user, now=None):
    now = now or timezone.now()
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)
        if user.deleted_at or not user.deletion_requested_at:
            return False
        _settle_money(user)
        _delete_personal_records(user)
        _wipe_row(user, now)
    logger.info("Deleted account %s after the grace period", user.pk)
    return True


def purge_due_accounts(now=None, batch_size: int = 200) -> int:
    now = now or timezone.now()
    due = User.objects.filter(
        deletion_scheduled_for__lte=now, deleted_at__isnull=True, deletion_requested_at__isnull=False
    ).values_list("pk", flat=True)[:batch_size]
    done = 0
    for pk in list(due):
        try:
            if purge(User(pk=pk), now=now):
                done += 1
        except Exception:
            logger.exception("Could not purge account %s", pk)
    return done
