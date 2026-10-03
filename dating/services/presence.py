"""
Ephemeral presence and typing state, kept only in the cache (Redis in production).

Presence is disposable by design: nothing here is written to the database, every
key expires on its own, and every function swallows cache errors. A cache outage
can make someone look offline; it can never stop a message from being stored or
delivered.
"""

import logging

from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

# A client polls the open chat every few seconds and the inbox every ~15s, so a
# user counts as online while any poll arrived within this window.
ONLINE_TTL_SECONDS = 60
# Long enough to show "last seen" for a month after someone goes quiet.
LAST_SEEN_TTL_SECONDS = 30 * 24 * 60 * 60
# Which chat a user has open; used to skip pushes for a chat they are reading.
VIEWING_TTL_SECONDS = 15
# Typing indicators vanish quickly unless the client keeps refreshing them.
TYPING_TTL_SECONDS = 6


def _online_key(user_id):
    return f"presence:online:{user_id}"


def _last_seen_key(user_id):
    return f"presence:last_seen:{user_id}"


def _viewing_key(user_id):
    return f"presence:viewing:{user_id}"


def _typing_key(chat_id, user_id):
    return f"presence:typing:{chat_id}:{user_id}"


def touch(user_id, viewing_chat_id=None):
    """Heartbeat: mark the user online now, optionally with the chat they have open."""
    try:
        cache.set(_online_key(user_id), 1, ONLINE_TTL_SECONDS)
        cache.set(
            _last_seen_key(user_id), timezone.now().isoformat(), LAST_SEEN_TTL_SECONDS
        )
        if viewing_chat_id is not None:
            cache.set(_viewing_key(user_id), int(viewing_chat_id), VIEWING_TTL_SECONDS)
    except Exception:
        logger.warning("presence.touch failed for user %s", user_id, exc_info=True)


def get_presence(user_ids):
    """Return {user_id: {"online": bool, "last_seen": iso-string or None}}."""
    user_ids = list(user_ids)
    result = {uid: {"online": False, "last_seen": None} for uid in user_ids}
    if not user_ids:
        return result
    try:
        online = cache.get_many([_online_key(uid) for uid in user_ids])
        seen = cache.get_many([_last_seen_key(uid) for uid in user_ids])
        for uid in user_ids:
            result[uid] = {
                "online": bool(online.get(_online_key(uid))),
                "last_seen": seen.get(_last_seen_key(uid)),
            }
    except Exception:
        logger.warning("presence.get_presence failed", exc_info=True)
    return result


def is_viewing(user_id, chat_id):
    """True when the user polled this chat in the last few seconds."""
    try:
        return cache.get(_viewing_key(user_id)) == int(chat_id)
    except Exception:
        logger.warning("presence.is_viewing failed for user %s", user_id, exc_info=True)
        return False


def set_typing(chat_id, user_id, is_typing=True):
    try:
        if is_typing:
            cache.set(_typing_key(chat_id, user_id), 1, TYPING_TTL_SECONDS)
        else:
            cache.delete(_typing_key(chat_id, user_id))
    except Exception:
        logger.warning("presence.set_typing failed for chat %s", chat_id, exc_info=True)


def typing_user_ids(chat_id, user_ids):
    """Which of these users are currently typing in the chat."""
    user_ids = list(user_ids)
    if not user_ids:
        return []
    try:
        found = cache.get_many([_typing_key(chat_id, uid) for uid in user_ids])
        return [uid for uid in user_ids if found.get(_typing_key(chat_id, uid))]
    except Exception:
        logger.warning("presence.typing_user_ids failed for chat %s", chat_id, exc_info=True)
        return []
