# signals.py
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import (
    SuggestedMatch,
    MatchRequest,
    Visibility,
    Chat,
    Message,
    UserMatch,
    Wallet,
    PostComment,
    Post,
)
from dating.tasks import notify_user
from django.core.cache import cache
from .services.dashboard import BondmakerDashboardService
from .services.analytics import BondmakerAnalyticsService
from django.db import transaction
from django.db.models import F


User = get_user_model()


@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance)


@receiver(post_save, sender=SuggestedMatch)
def suggested_match_notification(sender, instance, created, **kwargs):
    if not created:
        return

    bondmaker = instance.bondmaker
    subscriber = instance.user
    suggested_user = instance.suggested_user

    # Notify Subscriber
    notify_user.delay(
        subscriber.id,
        title="New Match Suggestion 💌",
        message=f"{bondmaker.name} suggested {suggested_user.name} to you.",
        data={
            "type": "match_suggestion",
            "suggestion_id": instance.id,
        },
    )

    # Notify Suggested User
    notify_user.delay(
        suggested_user.id,
        title="You’ve Been Suggested 💘",
        message=f"{bondmaker.name} suggested you to {subscriber.name}.",
        data={
            "type": "match_suggestion",
            "suggestion_id": instance.id,
        },
    )


@receiver(pre_save, sender=UserMatch)
def usermatch_status_notification(sender, instance, **kwargs):
    if not instance.pk:
        return

    previous = UserMatch.objects.get(pk=instance.pk)

    # Fire ONLY when status changes to "matched"
    if previous.status != "matched" and instance.status == "matched":
        user_a = instance.user1
        user_b = instance.user2

        # Notify user A
        notify_user.delay(
            user_a.id,
            title="It's a Match! 🎉",
            message=f"You have been matched with {user_b.name}",
            data={
                "type": "match_accepted",
                "match_id": instance.id,
            },
        )

        # Notify user B
        notify_user.delay(
            user_b.id,
            title="It's a Match! 🎉",
            message=f"You have been matched with {user_a.name}",
            data={
                "type": "match_accepted",
                "match_id": instance.id,
            },
        )
    # -------------------------------
    # REJECTED / DISLIKED
    # -------------------------------
    if previous.status != "disliked" and instance.status == "disliked":
        requester = instance.user1

        notify_user.delay(
            requester.id,
            title="Match Request Rejected",
            message="Your match request was rejected and coins refunded.",
            data={"type": "match_rejected", "match_id": instance.id},
        )


@receiver(post_save, sender=User)
def clear_static_profile_cache(sender, instance, **kwargs):
    cache.delete(f"user_static_profile:{instance.id}")


@receiver(post_save, sender=User)
def clear_profile_caches(sender, instance, **kwargs):
    cache.delete(f"my_profile:{instance.id}")
    cache.delete(f"user_static_profile:{instance.id}")


# Signals for Dashbord
@receiver(post_save, sender=MatchRequest)
def clear_dashboard_cache_on_match(sender, instance, **kwargs):
    if instance.status == "accepted":
        service = BondmakerDashboardService(instance.bondmaker)
        service.clear_cache()


def _delete_dashboard_cache(user_id):
    cache_key = f"bondmaker_dashboard_{user_id}"
    cache.delete(cache_key)


# @receiver(post_save, sender=BondmakerSubscription)
# def update_dashboard_on_subscription(sender, instance, **kwargs):

#     if instance.active:
#         _delete_dashboard_cache(instance.bondmaker_id)


@receiver(post_save, sender=Visibility)
def update_dashboard_on_visibility(sender, instance, **kwargs):

    if instance.status == "approved":
        _delete_dashboard_cache(instance.bondmaker_id)


@receiver(post_save, sender=MatchRequest)
def clear_analytics_on_match(sender, instance, **kwargs):
    if instance.status == "accepted":
        BondmakerAnalyticsService(instance.bondmaker).clear_cache()


# @receiver(post_save, sender=BondmakerTaskCompletion)
# def clear_analytics_on_task(sender, instance, **kwargs):
#     BondmakerAnalyticsService(instance.bondmaker).clear_cache()


@receiver(post_save, sender=Visibility)
def clear_analytics_on_visibility(sender, instance, **kwargs):
    BondmakerAnalyticsService(instance.bondmaker).clear_cache()


# -----------------------------------------
# Signal to Create Chat when a match is Initiated
# 1️ Detect status transition safely
# -----------------------------------------
@receiver(pre_save, sender=UserMatch)
def detect_match_transition(sender, instance, **kwargs):
    """
    Detect when status changes from anything -> matched
    """

    if not instance.pk:
        return  # New object, ignore

    try:
        previous = UserMatch.objects.get(pk=instance.pk)
    except UserMatch.DoesNotExist:
        return

    if previous.status != "matched" and instance.status == "matched":
        instance._create_chat = True

# -----------------------------------------
# Create chat after save (side effect)
# -----------------------------------------
@receiver(post_save, sender=UserMatch)
def create_chat_on_match(sender, instance, created, **kwargs):
    """
    Create match intro chat ONLY when transition to matched occurs
    """

    if not getattr(instance, "_create_chat", False):
        return

    # Double safety check (DB level)
    if hasattr(instance, "chat"):
        return

    bondmaker = None
    if instance.match_request:
        bondmaker = getattr(instance.match_request, "bondmaker", None)

    with transaction.atomic():

        # Lock row to prevent race conditions
        match = UserMatch.objects.select_for_update().get(pk=instance.pk)

        if hasattr(match, "chat"):
            return

        chat = Chat.objects.create(
            chat_type="matchmaker_intro",
            created_by=bondmaker,
            user_match=match,
        )

        participants = [match.user1, match.user2]
        if bondmaker:
            participants.append(bondmaker)

        chat.participants.add(*participants)

        # -------------------------
        # System Messages
        # -------------------------
        if bondmaker:
            Message.objects.create(
                chat=chat,
                message_type="system",
                content=f"{bondmaker.name} made the match",
            )

        Message.objects.create(
            chat=chat,
            message_type="system",
            content="You were added to this match",
        )

        # if bondmaker:
        #     Message.objects.create(
        #         chat=chat,
        #         sender=bondmaker,
        #         message_type="matchmaker_intro",
        #         content=(
        #             "Hi I’ve matched you because I see a good fit. "
        #             "Please introduce yourselves and get to know each other."
        #         ),
        #     )


# @receiver(post_save, sender=PostComment)
# def increase_comment_count(sender, instance, created, **kwargs):
#     if created and instance.is_active:
#         Post.objects.filter(pk=instance.post_id).update(
#             comment_count=F("comment_count") + 1
#         )


# @receiver(post_delete, sender=PostComment)
# def decrease_comment_count(sender, instance, **kwargs):
#     if instance.is_active:
#         Post.objects.filter(pk=instance.post_id).update(
#             comment_count=F("comment_count") - 1
#         )


# @receiver(post_save, sender=PostComment)
# def adjust_comment_count_on_status_change(sender, instance, **kwargs):
#     if not instance.pk:
#         return

#     try:
#         old = PostComment.objects.get(pk=instance.pk)
#     except PostComment.DoesNotExist:
#         return

#     if old.is_active and not instance.is_active:
#         Post.objects.filter(pk=instance.post_id).update(
#             comment_count=F("comment_count") - 1
#         )

#     if not old.is_active and instance.is_active:
#         Post.objects.filter(pk=instance.post_id).update(
#             comment_count=F("comment_count") + 1
#         )
