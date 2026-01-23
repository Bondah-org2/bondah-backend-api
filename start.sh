#!/bin/bash

echo "🚀 Starting Bondah Dating API..."

# Run database migrations
echo "📋 Running migrations..."
python dating_api_project/backend/manage.py migrate --settings=backend.settings_prod

# Collect static files
echo "📋 Collecting static files..."
python dating_api_project/backend/manage.py collectstatic --noinput --settings=backend.settings_prod

# Start Gunicorn server
echo "🚀 Starting Gunicorn..."
gunicorn dating_api_project.backend.wsgi:application --bind 0.0.0.0:$PORT
