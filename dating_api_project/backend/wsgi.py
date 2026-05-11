"""
WSGI config for backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Use production settings if DJANGO_SETTINGS_MODULE is not set
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')

env = os.getenv("ENVIRONMENT", "dev")

if env == "prod":
    default_settings = "backend.settings_prod"
else:
    default_settings = "backend.settings_dev"

os.environ.setdefault("DJANGO_SETTINGS_MODULE", default_settings)

application = get_wsgi_application()
