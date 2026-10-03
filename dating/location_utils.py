"""
Location utilities for dating app - GPS, geocoding, and distance calculations
NO GeoDjango. NO GDAL. Pure Python implementation.
"""

import math
import requests
from typing import Tuple, Optional, Dict, List
from django.conf import settings
from django.utils import timezone
from django.db.models import Q


# =========================================================
# DISTANCE CALCULATION (HAVERSINE)
# =========================================================
def calculate_distance(
    coord1: Tuple[float, float], coord2: Tuple[float, float]
) -> Optional[float]:
    """
    Calculate distance between two GPS coordinates using Haversine formula
    Returns distance in kilometers
    """
    if not coord1 or not coord2:
        return None

    lat1, lon1 = coord1
    lat2, lon2 = coord2

    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    earth_radius = 6371  # KM
    return earth_radius * c


# =========================================================
# GEOCODING
# =========================================================
def geocode_address(address: str) -> Optional[Dict]:
    """
    Convert address to GPS coordinates using Google Geocoding API
    """
    try:
        api_key = getattr(settings, "GOOGLE_MAPS_API_KEY", "")

        if not api_key:
            # Mock response for development
            return {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "address": address,
                "formatted_address": f"{address}, New York, NY, USA",
                "accuracy": "APPROXIMATE",
            }

        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": address, "key": api_key}

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data.get("status") == "OK" and data.get("results"):
            result = data["results"][0]
            location = result["geometry"]["location"]

            return {
                "latitude": location["lat"],
                "longitude": location["lng"],
                "address": address,
                "formatted_address": result["formatted_address"],
                "accuracy": result["geometry"]["location_type"],
            }

        return None

    except Exception as e:
        print(f"Geocoding error: {e}")
        return None


def reverse_geocode(latitude: float, longitude: float) -> Optional[Dict]:
    """
    Convert GPS coordinates to address using reverse geocoding
    """
    try:
        api_key = getattr(settings, "GOOGLE_MAPS_API_KEY", "")

        if not api_key:
            return {
                "address": f"{latitude}, {longitude}",
                "formatted_address": f"Mock Address for {latitude}, {longitude}",
                "city": "Mock City",
                "state": "Mock State",
                "country": "Mock Country",
                "postal_code": "12345",
            }

        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"latlng": f"{latitude},{longitude}", "key": api_key}

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data.get("status") == "OK" and data.get("results"):
            result = data["results"][0]

            address_components = {}
            for component in result.get("address_components", []):
                types = component.get("types", [])
                if "locality" in types:
                    address_components["city"] = component["long_name"]
                elif "administrative_area_level_1" in types:
                    address_components["state"] = component["long_name"]
                elif "country" in types:
                    address_components["country"] = component["long_name"]
                elif "postal_code" in types:
                    address_components["postal_code"] = component["long_name"]

            return {
                "address": result["formatted_address"],
                "formatted_address": result["formatted_address"],
                "city": address_components.get("city", ""),
                "state": address_components.get("state", ""),
                "country": address_components.get("country", ""),
                "postal_code": address_components.get("postal_code", ""),
            }

        return None

    except Exception as e:
        print(f"Reverse geocoding error: {e}")
        return None


# =========================================================
# NEARBY USER SEARCH
# =========================================================
def find_nearby_users(user, max_distance: Optional[int] = None) -> List[Dict]:
    from .models import User, UserMatch
    from django.db.models import Q, F
    from django.db.models.functions import ACos, Cos, Radians, Sin

    if not getattr(user, "has_location", False):
        return []

    max_distance = max_distance or getattr(user, "max_distance", 50)

    # Get matched user IDs to evaluate private settings without N+1 queries
    matched_user_ids = list(
        UserMatch.objects.filter(
            Q(user1=user) | Q(user2=user),
            status="matched"
        ).values_list('user1_id', 'user2_id')
    )
    matched_ids = {uid for pair in matched_user_ids for uid in pair if uid != user.id}

    # Query active users with location sharing enabled, using only() to limit fields loaded into memory
    users = User.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False,
        is_active=True,
        location_sharing_enabled=True,
    ).exclude(id=user.id).only(
        "id", "name", "gender", "city", "bio", "date_of_birth",
        "latitude", "longitude", "location_privacy", "location_sharing_enabled"
    )

    # Filter based on privacy settings
    users = users.filter(
        Q(location_privacy="public") |
        Q(location_privacy="private", id__in=matched_ids)
    )

    # Calculate distance using database-level math
    lat_rad = float(user.latitude) * 3.14159265359 / 180
    lon_rad = float(user.longitude) * 3.14159265359 / 180

    # HAversine formula in database
    users = users.annotate(
        distance_km=6371
        * ACos(
            Cos(Radians(F("latitude")))
            * Cos(lat_rad)
            * Cos(Radians(F("longitude")) - lon_rad)
            + Sin(Radians(F("latitude"))) * Sin(lat_rad)
        )
    )

    # Filter by max_distance
    users = users.filter(distance_km__lte=float(max_distance))

    # Order by distance
    users = users.order_by("distance_km")

    results = []
    for u in users:
        try:
            dist = float(u.distance_km)
        except (TypeError, ValueError):
            dist = 0.0

        results.append(
            {
                "user": u,
                "distance": dist,
                "coordinates": (u.latitude, u.longitude),
            }
        )

    return results



# =========================================================
# LOCATION PRIVACY
# =========================================================
def can_view_location(viewer, target) -> bool:
    from .models import UserMatch  # LOCAL import

    if not getattr(target, "location_sharing_enabled", True):
        return False

    privacy = getattr(target, "location_privacy", "public")
    if privacy == "public":
        return True
    elif privacy == "private":
        return UserMatch.objects.filter(
            Q(user1=viewer, user2=target) | Q(user1=target, user2=viewer),
            status="matched",
        ).exists()

    return False


# =========================================================
# UPDATE LOCATION
# =========================================================
def update_user_location(
    user, latitude, longitude, accuracy=None, source="gps"
) -> bool:
    from .models import LocationHistory  # LOCAL import

    try:
        user.latitude = latitude
        user.longitude = longitude
        user.last_location_update = timezone.now()

        address_data = reverse_geocode(latitude, longitude)
        if address_data:
            user.address = address_data.get("address", "")
            user.city = address_data.get("city", "")
            user.state = address_data.get("state", "")
            user.country = address_data.get("country", "")
            user.postal_code = address_data.get("postal_code", "")

        user.save()

        LocationHistory.objects.create(
            user=user,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            address=user.address,
            city=user.city,
            state=user.state,
            country=user.country,
            source=source,
        )

        return True

    except Exception as e:
        print(f"Location update error: {e}")
        return False


# =========================================================
# MATCH SCORE
# =========================================================
def calculate_match_score(user1, user2) -> float:
    """
    Calculate compatibility score between two users (0 - 100)
    """
    score = 0.0

    # Distance factor (0 - 30)
    if hasattr(user1, "get_distance_to"):
        distance = user1.get_distance_to(user2)
        if distance is not None and getattr(user1, "max_distance", 0) > 0:
            distance_score = max(0, 30 - (distance / user1.max_distance * 40))
            score += distance_score

    # Age factor (0 - 40)
    if getattr(user1, "age", None) and getattr(user2, "age", None):
        age_diff = abs(user1.age - user2.age)
        age_score = max(0, 40 - (age_diff * 2))
        score += age_score

    # Gender preference (0 - 30)
    if getattr(user1, "preferred_gender", None) and user1.preferred_gender == getattr(
        user2, "gender", None
    ):
        score += 15
    if getattr(user2, "preferred_gender", None) and user2.preferred_gender == getattr(
        user1, "gender", None
    ):
        score += 15

    return min(100.0, score)


# =========================================================
# VALIDATION
# =========================================================
def validate_coordinates(latitude: float, longitude: float) -> bool:
    return (-90 <= latitude <= 90) and (-180 <= longitude <= 180)


def get_approximate_location_from_ip(ip_address: str) -> Optional[Dict]:
    try:
        url = f"http://ip-api.com/json/{ip_address}"
        response = requests.get(url, timeout=5)
        data = response.json()

        if data.get("status") == "success":
            return {
                "latitude": data.get("lat"),
                "longitude": data.get("lon"),
                "city": data.get("city", ""),
                "state": data.get("regionName", ""),
                "country": data.get("country", ""),
                "accuracy": "low",
            }

        return None

    except Exception as e:
        print(f"IP geolocation error: {e}")
        return None


def get_location_statistics() -> Dict:
    from datetime import timedelta
    from .models import User, LocationHistory

    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    stats = {
        "total_users_with_location": User.objects.filter(
            latitude__isnull=False, longitude__isnull=False
        ).count(),
        "location_updates_24h": LocationHistory.objects.filter(
            timestamp__gte=last_24h
        ).count(),
        "location_updates_7d": LocationHistory.objects.filter(
            timestamp__gte=last_7d
        ).count(),
        "active_users_with_location": User.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False,
            last_location_update__gte=last_24h,
        ).count(),
        "privacy_distribution": {
            "public": User.objects.filter(location_privacy="public").count(),
            "friends": User.objects.filter(location_privacy="friends").count(),
            "private": User.objects.filter(location_privacy="private").count(),
            "hidden": User.objects.filter(location_privacy="hidden").count(),
        },
    }

    return stats


def is_user_visible_to(bondmaker, user) -> bool:
    from .models import Visibility  # LOCAL import

    return (
        Visibility.objects.filter(
            owner=user,
            is_active=True,
            status="approved",
            expires_at__gt=timezone.now(),
        )
        .filter(Q(visibility="public") | Q(visibility="private", bondmaker=bondmaker))
        .exists()
    )
