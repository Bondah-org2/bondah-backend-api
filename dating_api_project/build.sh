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

# Fix database columns
echo "Fixing database columns..."
python fix_database_columns.py

# Create all missing tables
echo "Creating all missing tables..."
python create_all_tables.py

# Collect static files
echo "Collecting static files..."
python collect_static_fix.py

# Test static files
echo "Testing static files..."
python test_static_files.py

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
