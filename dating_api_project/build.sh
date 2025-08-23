#!/bin/bash

echo "🚀 Starting Bondah Dating API deployment..."

# Run database fixes
echo "📋 Running database fixes..."
python fix_all_database_issues.py
python fix_auth_tables.py
python fix_admin_login.py
python fix_job_application_schema.py
python fix_waitlist_database.py
python fix_waitlist_railway_db.py

# Run migrations
echo "📋 Running migrations..."
python manage.py migrate --settings=backend.settings_prod

# Collect static files
echo "📋 Collecting static files..."
python force_collect_static.py

# Verify static files
echo "📋 Verifying static files..."
ls -la staticfiles/
python check_static_build.py

# Fallback if static files are missing
if [ ! -f "staticfiles/admin/css/base.css" ]; then
    echo "⚠️  Static files missing, running collectstatic directly..."
    python manage.py collectstatic --noinput --settings=backend.settings_prod
    ls -la staticfiles/
fi

# Test static serving
echo "📋 Testing static file serving..."
python test_static_serving.py

# Test waitlist functionality
echo "📋 Testing waitlist functionality..."
python test_waitlist_bulletproof.py

echo "✅ Deployment setup complete!"
