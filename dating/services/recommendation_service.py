"""Recommended profiles for a love seeker ("Explore more profile").

People who match what the seeker is looking for and none of their
dealbreakers.

Hard filters (never shown otherwise):
- publicly visible right now, same country, not a bondmaker, not already
  liked or passed;
- the seeker's preferred gender and age range;
- dealbreakers. These are free text ("Smoking, Long-distance"), so known
  words map to profile fields: smoking, drinking, kids, pets, long distance.

Ranking (soft): the qualities the seeker wants against the other person's
own traits, the same relationship goal, whether the other person is looking
for someone like the seeker, shared hobbies and interests, and the same
religion.

Only seekers who are visible themselves get recommendations.
"""

import re
from dataclasses import dataclass, field
from datetime import date

from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from dating.models import User, UserInteraction, Visibility

RESULT_SIZE = 20
CANDIDATE_POOL = 300  # most recently active matches that get scored

# Wanted quality -> own traits that show it. The sign-up lists differ
# (wanted: Humor, Kindness...; own: Friendly, Calm...), so this bridges them.
QUALITY_TRAITS = {
    "humor": {"humor", "funny", "outgoing", "friendly"},
    "kindness": {"kindness", "kind", "friendly", "calm"},
    "ambition": {"ambition", "ambitious"},
    "loyalty": {"loyalty", "loyal"},
    "supportive": {"supportive", "friendly", "calm"},
    "reliable": {"reliable", "calm"},
}

# Dealbreaker words -> the profiles they rule out.
ACTIVE_HABIT = ("occasionally", "regularly")
DEALBREAKER_RULES = [
    (re.compile(r"smok|cigar|vap"), Q(smoking_preference__in=ACTIVE_HABIT)),
    (re.compile(r"drink|alcohol|booze"), Q(drinking_preference__in=ACTIVE_HABIT)),
    (re.compile(r"\bkids?\b|child|baby|babies"), Q(have_kids="yes")),
    (re.compile(r"\bpets?\b|\bdogs?\b|\bcats?\b"), Q(pet_preference__in=("dog", "cat", "both", "other"))),
]
LONG_DISTANCE = re.compile(r"long[\s-]*distance")


@dataclass
class Recommendation:
    user: User
    score: int
    shared_qualities: list = field(default_factory=list)
    same_goal: bool = False
    shared_hobbies: int = 0


def _years_ago(years: int) -> date:
    today = date.today()
    try:
        return today.replace(year=today.year - years)
    except ValueError:
        return today.replace(year=today.year - years, day=28)


def is_visible(user) -> bool:
    return Visibility.objects.filter(
        owner=user, status="approved", expires_at__gt=timezone.now()
    ).exists()


def _words(values) -> set:
    return {str(v).strip().lower() for v in (values or []) if str(v).strip()}


def dealbreaker_filter(seeker, qs):
    text = (seeker.deal_breaker or "").lower()
    if not text:
        return qs
    for pattern, rule in DEALBREAKER_RULES:
        if pattern.search(text):
            qs = qs.exclude(rule)
    if LONG_DISTANCE.search(text) and seeker.city:
        qs = qs.filter(city__iexact=seeker.city)
    return qs


def candidates(seeker):
    if not seeker.country:
        return User.objects.none()

    public_now = Visibility.objects.filter(
        owner=OuterRef("pk"), visibility="public", status="approved", expires_at__gt=timezone.now()
    )
    qs = (
        User.objects.filter(is_active=True, is_matchmaker=False, country=seeker.country)
        .exclude(pk=seeker.pk)
        .filter(Exists(public_now))
        .exclude(Exists(UserInteraction.objects.filter(user=seeker, target_user=OuterRef("pk"))))
    )

    if seeker.preferred_gender in ("male", "female"):
        qs = qs.filter(gender__iexact=seeker.preferred_gender)

    low = max(18, seeker.age_range_min or 18)
    high = min(100, seeker.age_range_max or 100)
    if low > 18:
        qs = qs.filter(date_of_birth__lte=_years_ago(low))
    if high < 100:
        qs = qs.filter(date_of_birth__gt=_years_ago(high + 1))

    return dealbreaker_filter(seeker, qs)


def _score(seeker, other, wanted, seeker_hobbies) -> Recommendation:
    rec = Recommendation(user=other, score=0)

    traits = _words(other.traits)
    for quality in wanted:
        if QUALITY_TRAITS.get(quality, {quality}) & traits:
            rec.shared_qualities.append(quality)
    rec.score += 15 * len(rec.shared_qualities)

    if seeker.dating_type and seeker.dating_type == other.dating_type:
        rec.same_goal = True
        rec.score += 20

    if other.preferred_gender and seeker.gender and other.preferred_gender.lower() == seeker.gender.lower():
        rec.score += 10

    rec.shared_hobbies = len(seeker_hobbies & (_words(other.hobbies) | _words(other.interests)))
    rec.score += min(20, 5 * rec.shared_hobbies)

    if seeker.religion and other.religion and seeker.religion.lower() == other.religion.lower():
        rec.score += 5

    seeker_age = seeker.age
    if seeker_age and (other.age_range_min or 18) <= seeker_age <= (other.age_range_max or 100):
        rec.score += 5

    return rec


def recommend(seeker, limit: int = RESULT_SIZE) -> list[Recommendation]:
    pool = list(
        candidates(seeker)
        .only(
            "id", "name", "gender", "bio", "profile_picture", "date_of_birth", "traits",
            "hobbies", "interests", "dating_type", "preferred_gender", "religion",
            "age_range_min", "age_range_max", "last_seen",
        )
        .order_by("-last_seen", "-id")[:CANDIDATE_POOL]
    )
    wanted = [q.lower() for q in (seeker.partner_qualities or []) if isinstance(q, str)]
    seeker_hobbies = _words(seeker.hobbies) | _words(seeker.interests)

    scored = [_score(seeker, other, wanted, seeker_hobbies) for other in pool]
    scored.sort(key=lambda r: r.score, reverse=True)  # stable: recent activity breaks ties
    return scored[:limit]
