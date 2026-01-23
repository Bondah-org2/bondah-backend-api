#!/bin/bash

echo "🚀 Starting Bondah Dating API..."

# Move into Django project folder
cd dating_api_project

# Run migrations
echo "📋 Running database migrations..."
python backend/manage.py migrate --settings=backend.settings_prod

# Collect static files
echo "📋 Collecting static files..."
python backend/manage.py collectstatic --noinput --settings=backend.settings_prod

# Start Gunicorn
echo "🚀 Starting Gunicorn server..."
gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT
