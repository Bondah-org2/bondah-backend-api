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

from .models import User, LocationHistory, UserMatch, Visibility


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
# NEARBY USER SEARCH (PURE PYTHON)
# =========================================================


def find_nearby_users(user: User, max_distance: Optional[int] = None) -> List[Dict]:
    if not user.has_location:
        return []

    max_distance = max_distance or user.max_distance

    users = User.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False,
        is_active=True,
    ).exclude(id=user.id)

    results = []

    for other in users:
        if not can_view_location(user, other):
            continue

        distance = calculate_distance(
            (user.latitude, user.longitude),
            (other.latitude, other.longitude),
        )

        if distance is None:
            continue

        if distance <= max_distance:
            results.append(
                {
                    "user": other,
                    "distance": distance,
                    "coordinates": (other.latitude, other.longitude),
                }
            )

    results.sort(key=lambda x: x["distance"])
    return results


# =========================================================
# LOCATION PRIVACY
# =========================================================


def can_view_location(viewer: User, target: User) -> bool:
    if not target.location_sharing_enabled:
        return False

    if target.location_privacy == "public":
        return True
    elif target.location_privacy == "private":
        return UserMatch.objects.filter(
            Q(user1=viewer, user2=target) | Q(user1=target, user2=viewer),
            status="matched",
        ).exists()

    return False


# =========================================================
# UPDATE LOCATION
# =========================================================


def update_user_location(
    user: User,
    latitude: float,
    longitude: float,
    accuracy: Optional[float] = None,
    source: str = "gps",
) -> bool:
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


def calculate_match_score(user1: User, user2: User) -> float:
    """
    Calculate compatibility score between two users (0 - 100)
    """
    score = 0.0

    # Distance factor (0 - 40)
    distance = user1.get_distance_to(user2)
    if distance is not None and user1.max_distance > 0:
        distance_score = max(0, 40 - (distance / user1.max_distance * 40))
        score += distance_score

    # Age factor (0 - 30)
    if user1.age and user2.age:
        age_diff = abs(user1.age - user2.age)
        age_score = max(0, 30 - (age_diff * 2))
        score += age_score

    # Gender preference (0 - 30)
    if user1.preferred_gender and user1.preferred_gender == user2.gender:
        score += 15
    if user2.preferred_gender and user2.preferred_gender == user1.gender:
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
    """
    Get location-related statistics for admin dashboard
    """
    from django.utils import timezone
    from datetime import timedelta

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


def is_user_visible_to(bondmaker, user):
    """
    Returns True if a user is visible to the bondmaker
    - Public users: visible to all
    - Private users: only visible to specific bondmaker
    """
    return (
        Visibility.objects.filter(
            owner=user,
            is_active=True,
            expires_at__gt=timezone.now(),
        )
        .filter(Q(visibility="public") | Q(visibility="private", bondmaker=bondmaker))
        .exists()
    )
