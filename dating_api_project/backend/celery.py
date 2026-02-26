import os
from celery import Celery

# --- 1. Decide which settings to use ---
if os.environ.get("DJANGO_ENV") == "prod":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings_prod")
else:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

# --- 2. Create Celery app ---
app = Celery("dating_api_project")

# Load settings from Django settings.py
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks.py in installed apps
app.autodiscover_tasks()
