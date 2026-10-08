"""Bond Story rules (rebuild phase 9).

- Only bondmakers post. Authors edit and delete their own posts.
- Audiences, enforced on every read (list, single post, comments, likes,
  reports), and the author always sees their own:
    everyone     anyone signed in
    seekers      love seekers only (other bondmakers can't see it)
    followers    people who follow the author (following is free)
- Anyone who can see a post can like it, comment and report it. Commenters
  edit and delete their own comments; the post's author can delete any
  comment on their post.
- Reports go to Team Bondah. Upholding one hides the post or comment, and
  a post report upheld against a bondmaker is a strike (account health).
"""

from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from dating.models import BondmakerSubscription, Post, PostComment, PostReport


def following(user):
    """Bondmakers this user follows. A follow lasts until they unfollow."""
    return BondmakerSubscription.objects.filter(user=user, active=True)


def visible_posts(user):
    """Active posts this user may see."""
    follows = following(user).filter(bondmaker=OuterRef("author"))
    audience = Q(visibility="everyone") | Q(author=user) | (Q(visibility="followers") & Exists(follows))
    if not user.is_matchmaker:
        audience |= Q(visibility="seekers")
    return Post.objects.filter(is_active=True).filter(audience)


def search(qs, text: str):
    text = (text or "").strip()[:100]
    if not text:
        return qs
    tag = text.lstrip("#")
    return qs.filter(
        Q(content__icontains=text)
        | Q(author__name__icontains=text)
        | Q(author__username__icontains=text)
        | Q(hashtags__icontains=tag)
    )


# ------------------------------------------------------------------ reports


def report(*, reporter, reason: str, description: str, post=None, comment=None) -> tuple[PostReport, bool]:
    """One report per person per post or comment. Returns (report, created)."""
    target_user = comment.author if comment else post.author
    if target_user == reporter:
        raise ValueError("You can't report your own content.")
    with transaction.atomic():
        existing = PostReport.objects.filter(
            reporter=reporter, post=post if comment is None else None, comment=comment
        ).first()
        if existing:
            return existing, False
        created = PostReport.objects.create(
            reporter=reporter,
            reported_user=target_user,
            post=post if comment is None else None,
            comment=comment,
            report_type=reason,
            description=(description or "")[:2000],
        )
        if comment is None:
            Post.objects.filter(pk=post.pk).update(is_reported=True)
    return created, True


def review_report(content_report: PostReport, action: str, admin, note: str = "") -> PostReport:
    """action: review | resolve (upheld: hide it, strike a bondmaker author) | dismiss."""
    from . import health_service

    status_for = {"review": "reviewed", "resolve": "resolved", "dismiss": "dismissed"}
    with transaction.atomic():
        r = (
            PostReport.objects.select_for_update()
            .select_related("reported_user", "post", "comment")
            .get(pk=content_report.pk)
        )
        if r.status in ("resolved", "dismissed"):
            return r
        r.status = status_for[action]
        r.resolved_by = admin
        r.resolved_at = timezone.now()
        r.moderator_notes = note[:1000] or r.moderator_notes
        if action == "resolve":
            if r.comment_id:
                PostComment.objects.filter(pk=r.comment_id).update(is_active=False)
                r.action_taken = "comment_hidden"
            elif r.post_id:
                Post.objects.filter(pk=r.post_id).update(is_active=False)
                r.action_taken = "post_hidden"
        r.save(update_fields=["status", "resolved_by", "resolved_at", "moderator_notes", "action_taken"])

        # Other open reports on the same thing are settled by this decision.
        if action in ("resolve", "dismiss"):
            same = PostReport.objects.filter(status__in=("pending", "reviewed")).exclude(pk=r.pk)
            same = same.filter(comment_id=r.comment_id) if r.comment_id else same.filter(post_id=r.post_id, comment__isnull=True)
            same.update(status=r.status, resolved_by=admin, resolved_at=r.resolved_at)
            if r.post_id and not r.comment_id and action == "dismiss":
                Post.objects.filter(pk=r.post_id).update(is_reported=False)

        if action == "resolve" and r.reported_user.is_matchmaker:
            health_service.add_strike(
                r.reported_user, "report",
                note=f"Bond Story {'comment' if r.comment_id else 'post'} removed: {r.get_report_type_display()}",
                source=f"post_report:{r.pk}", created_by=admin,
            )
    return r
