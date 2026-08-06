#!/bin/bash

echo "🚀 Starting Bondah Dating API..."

# Go into the Django project folder
cd dating_api_project

echo "📋 Running database migrations..."
python manage.py migrate --settings=backend.settings_prod

echo "📋 Collecting static files..."
python manage.py collectstatic --noinput --settings=backend.settings_prod

echo "👤 Creating superuser if not exists..."
python create_admin_superuser.py


echo "🔄 Starting Celery worker..."
celery -A backend worker --loglevel=info --concurrency=1 --max-tasks-per-child=100 &

gunicorn backend.wsgi:application \
  --bind 0.0.0.0:$PORT \
  --workers 2 \
  --max-requests 500 \
  --max-requests-jitter 50 \
  --env DJANGO_SETTINGS_MODULE=backend.settings_prod