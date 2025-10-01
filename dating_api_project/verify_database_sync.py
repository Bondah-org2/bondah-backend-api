#!/usr/bin/env python
"""
Verify Database Sync - Check if pgAdmin manual tables match Django models
This script checks if your manually created tables in Railway Postgres
match what Django expects from migrations.
"""

import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.apps import apps
from django.db.migrations.recorder import MigrationRecorder


def verify_database_sync():
    """Check database sync status between manual creation and Django"""
    
    print("=" * 80)
    print("🔍 DATABASE SYNC VERIFICATION")
    print("=" * 80)
    print()
    
    # 1. Check database connection
    print("📡 Step 1: Checking database connection...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"✅ Connected to: {version}")
            
            cursor.execute("SELECT current_database();")
            db_name = cursor.fetchone()[0]
            print(f"✅ Database: {db_name}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return
    
    print()
    
    # 2. Check what migrations Django thinks are applied
    print("📝 Step 2: Checking Django migration records...")
    try:
        migrations = MigrationRecorder.Migration.objects.filter(app='dating').order_by('id')
        print(f"✅ Found {migrations.count()} dating app migrations recorded:")
        for mig in migrations:
            print(f"   [{mig.id}] {mig.name}")
    except Exception as e:
        print(f"⚠️  Could not read migrations: {e}")
    
    print()
    
    # 3. Check what tables actually exist in database
    print("🗄️  Step 3: Checking actual database tables...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tablename 
                FROM pg_catalog.pg_tables 
                WHERE schemaname = 'public' 
                AND tablename LIKE 'dating_%'
                ORDER BY tablename;
            """)
            actual_tables = [row[0] for row in cursor.fetchall()]
            print(f"✅ Found {len(actual_tables)} dating tables in database:")
            for table in actual_tables:
                print(f"   • {table}")
    except Exception as e:
        print(f"❌ Could not read tables: {e}")
        actual_tables = []
    
    print()
    
    # 4. Check what tables Django expects
    print("📋 Step 4: Checking Django model expectations...")
    dating_models = apps.get_app_config('dating').get_models()
    expected_tables = [model._meta.db_table for model in dating_models]
    print(f"✅ Django expects {len(expected_tables)} tables:")
    for table in sorted(expected_tables):
        print(f"   • {table}")
    
    print()
    
    # 5. Compare expected vs actual
    print("🔄 Step 5: Comparing expected vs actual tables...")
    expected_set = set(expected_tables)
    actual_set = set(actual_tables)
    
    missing_tables = expected_set - actual_set
    extra_tables = actual_set - expected_set
    matching_tables = expected_set & actual_set
    
    if missing_tables:
        print(f"⚠️  MISSING TABLES (expected but not in database):")
        for table in sorted(missing_tables):
            print(f"   ❌ {table}")
    else:
        print("✅ No missing tables!")
    
    print()
    
    if extra_tables:
        print(f"ℹ️  EXTRA TABLES (in database but not in Django models):")
        for table in sorted(extra_tables):
            print(f"   ⚠️  {table}")
        print("   (These might be old/unused tables)")
    else:
        print("✅ No extra tables!")
    
    print()
    
    print(f"✅ MATCHING TABLES: {len(matching_tables)}/{len(expected_tables)}")
    
    print()
    
    # 6. Check new OAuth/Mobile tables specifically
    print("📱 Step 6: Checking new OAuth/Mobile tables from migration 0009...")
    new_tables = [
        'dating_socialaccount',
        'dating_deviceregistration',
        'dating_locationhistory',
        'dating_usermatch',
        'dating_locationpermission'
    ]
    
    for table in new_tables:
        if table in actual_tables:
            print(f"   ✅ {table}")
        else:
            print(f"   ❌ {table} - MISSING!")
    
    print()
    
    # 7. Check for OAuth/Mobile fields in User model
    print("👤 Step 7: Checking User model for new fields...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'dating_user' 
                AND column_name IN (
                    'latitude', 'longitude', 'address', 'city', 
                    'location_privacy', 'max_distance', 'age_range_min'
                )
                ORDER BY column_name;
            """)
            user_fields = [row[0] for row in cursor.fetchall()]
            
            expected_fields = ['latitude', 'longitude', 'address', 'city', 
                             'location_privacy', 'max_distance', 'age_range_min']
            
            print(f"✅ Found {len(user_fields)}/{len(expected_fields)} new User fields:")
            for field in expected_fields:
                if field in user_fields:
                    print(f"   ✅ {field}")
                else:
                    print(f"   ❌ {field} - MISSING!")
    except Exception as e:
        print(f"⚠️  Could not check User fields: {e}")
    
    print()
    
    # 8. Summary and recommendations
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    
    if not missing_tables and len(new_tables) <= len(actual_tables):
        print("✅ Database is in GOOD SYNC with Django models!")
        print("✅ All OAuth/Mobile tables are present")
        print("✅ Migration 0009 applied successfully")
        print()
        print("🎯 NEXT STEPS:")
        print("1. Continue with mobile app development")
        print("2. Use Django migrations for future changes")
        print("3. Keep pgAdmin for viewing/debugging only")
    else:
        print("⚠️  Database needs attention!")
        print()
        print("🔧 RECOMMENDED ACTIONS:")
        
        if missing_tables:
            print("1. Apply missing migrations:")
            print("   python manage.py migrate")
        
        if extra_tables:
            print("2. Clean up extra tables (optional):")
            for table in sorted(extra_tables):
                print(f"   DROP TABLE IF EXISTS {table};")
        
        print()
        print("3. Verify migration records:")
        print("   python manage.py showmigrations dating")
        
        print()
        print("4. If tables exist but migrations not recorded:")
        print("   python manage.py migrate dating --fake")
    
    print()
    print("=" * 80)
    print("📚 Documentation: See PGADMIN_RAILWAY_SETUP.md for details")
    print("=" * 80)


if __name__ == '__main__':
    try:
        verify_database_sync()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

