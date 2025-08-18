#!/bin/bash

# Build script for Railway deployment

echo "Starting build process..."

# Install dependencies
pip install -r requirements.txt

# Run DIRECT table creation
echo "Running DIRECT table creation..."
python create_tables.py

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
