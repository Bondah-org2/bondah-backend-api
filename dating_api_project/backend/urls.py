"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

@method_decorator(csrf_exempt, name='dispatch')
class HealthCheckView(View):
    def get(self, request):
        return JsonResponse({
            "status": "healthy",
            "message": "Bondah Dating API is running",
            "version": "1.0.0"
        })

def home(request):
    return JsonResponse({
        "message": "Welcome to Bondah Dating API",
        "endpoints": {
            "health": "/health/",
            "api": "/api/",
            "admin": "/admin/"
        }
    })

urlpatterns = [
    path('', home),
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('admin/', admin.site.urls),
    path('api/', include('dating.urls')),  # Include the dating app URLs
    
    # API Documentation URLs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Serve static files in production
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    # In production, WhiteNoise will handle static files
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
