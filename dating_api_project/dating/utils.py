from django.core.cache import cache
from django.contrib.auth import get_user_model
from .serializers import StaticUserProfileSerializer
from .serializers import UserProfileDetailSerializer

User = get_user_model()


def get_cached_static_profile(user_id):
    key = f"user_static_profile:{user_id}"
    data = cache.get(key)

    if data is None:
        user = User.objects.select_related().get(id=user_id, is_active=True)
        data = StaticUserProfileSerializer(user).data
        cache.set(key, data, timeout=60 * 60)

    return data


def get_cached_my_profile(user):
    key = f"my_profile:{user.id}"
    data = cache.get(key)

    if data is None:
        serializer = UserProfileDetailSerializer(
            user, context={"request": None}  # no viewer logic needed
        )
        data = serializer.data
        cache.set(key, data, timeout=60 * 60)

    return data
