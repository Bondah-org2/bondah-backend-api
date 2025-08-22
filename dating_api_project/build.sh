#!/bin/bash

# Build script for Railway deployment

echo "Starting build process..."

# Install dependencies
pip install -r requirements.txt

# Create staticfiles directory
echo "Creating staticfiles directory..."
mkdir -p staticfiles

# Run Final Railway fix
echo "Running Final Railway fix..."
python final_railway_fix.py

# Fix all database issues comprehensively
echo "Fixing all database issues..."
python fix_all_database_issues.py

# Fix Django auth tables
echo "Fixing Django auth tables..."
python fix_auth_tables.py

# Collect static files
echo "Collecting static files..."
python force_collect_static.py

# Verify static files were collected
echo "Verifying static files..."
ls -la staticfiles/
ls -la staticfiles/admin/css/ || echo "Admin CSS directory not found"
ls -la staticfiles/admin/js/ || echo "Admin JS directory not found"

# Check static files
echo "Checking static files..."
python check_static_build.py

# Fallback: Try direct Django command if script failed
if [ ! -f "staticfiles/admin/css/base.css" ]; then
    echo "⚠️  Static files missing, trying fallback..."
    python manage.py collectstatic --noinput --clear --settings=backend.settings_prod
    python check_static_build.py
fi

# Test static files
echo "Testing static files..."
python test_static_files.py

# Test static files serving
echo "Testing static files serving..."
python test_static_serving.py

# Debug current status
echo "Debugging current status..."
python debug_railway.py

# Test static files configuration
echo "Testing static files configuration..."
python test_static.py

# Test CSRF configuration
echo "Testing CSRF configuration..."
python test_csrf.py

echo "Build completed successfully!"
