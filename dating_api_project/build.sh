#!/bin/bash

# Build script for Railway deployment

echo "Starting build process..."

# Install dependencies
pip install -r requirements.txt

# Run production setup (migrations + superuser creation)
python manage.py setup_production

echo "Build completed successfully!"
