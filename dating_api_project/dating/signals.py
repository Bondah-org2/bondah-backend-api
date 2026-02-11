# signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Wallet, UserMatch
from django.contrib.auth import get_user_model
from .models import SuggestedMatch
from .notification import notify_user


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

    # 🔔 Notify Subscriber
    notify_user(
        subscriber,
        title="New Match Suggestion 💌",
        message=f"{bondmaker.name} suggested {suggested_user.name} to you.",
        data={
            "type": "match_suggestion",
            "suggestion_id": instance.id,
        },
    )

    # 🔔 Notify Suggested User
    notify_user(
        suggested_user,
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
        notify_user(
            user_a,
            title="It's a Match! 🎉",
            message=f"You have been matched with {user_b.name}",
            data={
                "type": "match_accepted",
                "match_id": instance.id,
            },
        )

        # Notify user B
        notify_user(
            user_b,
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

        notify_user(
            requester,
            title="Match Request Rejected",
            message="Your match request was rejected and coins refunded.",
            data={"type": "match_rejected", "match_id": instance.id},
        )
