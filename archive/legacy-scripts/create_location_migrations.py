#!/usr/bin/env python
"""
Create migrations for location-related models
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

def create_location_migrations():
    """Create migrations for location-related models"""
    print("🗺️ Creating location migrations...")
    
    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    django.setup()
    
    try:
        # Create migrations
        execute_from_command_line(['manage.py', 'makemigrations', 'dating'])
        print("✅ Location migrations created successfully")
        
        # Show the migration
        execute_from_command_line(['manage.py', 'showmigrations', 'dating'])
        
        return True
    except Exception as e:
        print(f"❌ Migration creation failed: {e}")
        return False

if __name__ == "__main__":
    success = create_location_migrations()
    sys.exit(0 if success else 1)
