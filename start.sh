#!/bin/bash

echo "🚀 Starting Bondah Dating API..."

# Go into the Django project folder
cd dating_api_project

echo "📋 Running database migrations..."
python manage.py migrate --settings=backend.settings_prod

echo "📋 Collecting static files..."
python manage.py collectstatic --noinput --settings=backend.settings_prod

echo "🚀 Starting Gunicorn server..."
gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT
