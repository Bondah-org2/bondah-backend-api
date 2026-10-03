"""Root URL configuration: health check, admin, /api/v1/ and API docs."""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)


# --------------------------
# Health Check
# --------------------------


@method_decorator(csrf_exempt, name="dispatch")
class HealthCheckView(View):
    def get(self, request):
        return JsonResponse(
            {
                "status": "healthy",
                "message": "Bondah Dating API is running",
                "version": "1.0.0",
            }
        )


# --------------------------
# API Home (for /api/)
# --------------------------
def api_home(request):
    return JsonResponse(
        {
            "message": "Welcome to Bondah Dating API",
            "endpoints": {
                "health": "/health/",
                "admin": "/admin/",
                "api_v1": "/api/v1/",
            },
        }
    )


# --------------------------
# URL Patterns
# --------------------------
urlpatterns = [
    # Root and Health
    path("", api_home),
    path("health/", HealthCheckView.as_view(), name="health-check"),
    # Admin
    path("admin/", admin.site.urls),
    # API v1
    path("api/", api_home),
    path("api/v1/", include("dating.urls")),
    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(),
        name="swagger-ui",

    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# --------------------------
# Serve static files in production
# --------------------------
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
