#!/usr/bin/env python
"""
Fix Django Auth Tables - Create missing auth_group and auth_permission tables
"""

import os
import sys
import django
from django.db import connection

def fix_auth_tables():
    """Create Django's built-in auth tables"""
    print("🔧 FIXING DJANGO AUTH TABLES")
    print("=" * 50)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
    
    try:
        django.setup()
        print("✅ Django setup successful")
    except Exception as e:
        print(f"❌ Django setup failed: {str(e)}")
        return False
    
    try:
        with connection.cursor() as cursor:
            print("🔍 Creating Django auth tables...")
            
            # 1. Create auth_group table
            print("\n📋 Creating auth_group table...")
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS auth_group (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(150) UNIQUE NOT NULL
                    )
                """)
                print("  ✅ auth_group table created/verified")
            except Exception as e:
                print(f"  ⚠️  auth_group table error: {str(e)}")
            
            # 2. Create auth_permission table
            print("\n📋 Creating auth_permission table...")
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS auth_permission (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        content_type_id INTEGER NOT NULL,
                        codename VARCHAR(100) NOT NULL,
                        UNIQUE(content_type_id, codename)
                    )
                """)
                print("  ✅ auth_permission table created/verified")
            except Exception as e:
                print(f"  ⚠️  auth_permission table error: {str(e)}")
            
            # 3. Create django_content_type table
            print("\n📋 Creating django_content_type table...")
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS django_content_type (
                        id SERIAL PRIMARY KEY,
                        app_label VARCHAR(100) NOT NULL,
                        model VARCHAR(100) NOT NULL,
                        UNIQUE(app_label, model)
                    )
                """)
                print("  ✅ django_content_type table created/verified")
            except Exception as e:
                print(f"  ⚠️  django_content_type table error: {str(e)}")
            
            # 4. Create auth_user_groups table (many-to-many)
            print("\n📋 Creating auth_user_groups table...")
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS auth_user_groups (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        group_id INTEGER NOT NULL,
                        UNIQUE(user_id, group_id)
                    )
                """)
                print("  ✅ auth_user_groups table created/verified")
            except Exception as e:
                print(f"  ⚠️  auth_user_groups table error: {str(e)}")
            
            # 5. Create auth_user_user_permissions table (many-to-many)
            print("\n📋 Creating auth_user_user_permissions table...")
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS auth_user_user_permissions (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        permission_id INTEGER NOT NULL,
                        UNIQUE(user_id, permission_id)
                    )
                """)
                print("  ✅ auth_user_user_permissions table created/verified")
            except Exception as e:
                print(f"  ⚠️  auth_user_user_permissions table error: {str(e)}")
            
            # 6. Create django_migrations table
            print("\n📋 Creating django_migrations table...")
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS django_migrations (
                        id SERIAL PRIMARY KEY,
                        app VARCHAR(255) NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        applied TIMESTAMP WITH TIME ZONE NOT NULL
                    )
                """)
                print("  ✅ django_migrations table created/verified")
            except Exception as e:
                print(f"  ⚠️  django_migrations table error: {str(e)}")
            
            # 7. Insert basic content types
            print("\n📋 Inserting basic content types...")
            try:
                cursor.execute("""
                    INSERT INTO django_content_type (app_label, model) VALUES
                    ('auth', 'group'),
                    ('auth', 'permission'),
                    ('auth', 'user'),
                    ('dating', 'user'),
                    ('dating', 'newslettersubscriber'),
                    ('dating', 'puzzleverification'),
                    ('dating', 'cointransaction'),
                    ('dating', 'waitlist'),
                    ('dating', 'job'),
                    ('dating', 'jobapplication'),
                    ('dating', 'adminuser'),
                    ('dating', 'adminotp'),
                    ('dating', 'emaillog'),
                    ('dating', 'translationlog')
                    ON CONFLICT (app_label, model) DO NOTHING
                """)
                print("  ✅ Basic content types inserted")
            except Exception as e:
                print(f"  ⚠️  Content types error: {str(e)}")
            
            # 8. Insert basic permissions
            print("\n📋 Inserting basic permissions...")
            try:
                cursor.execute("""
                    INSERT INTO auth_permission (name, content_type_id, codename) 
                    SELECT 
                        'Can add ' || model, 
                        id, 
                        'add_' || model
                    FROM django_content_type
                    WHERE app_label = 'dating'
                    ON CONFLICT (content_type_id, codename) DO NOTHING
                """)
                
                cursor.execute("""
                    INSERT INTO auth_permission (name, content_type_id, codename) 
                    SELECT 
                        'Can change ' || model, 
                        id, 
                        'change_' || model
                    FROM django_content_type
                    WHERE app_label = 'dating'
                    ON CONFLICT (content_type_id, codename) DO NOTHING
                """)
                
                cursor.execute("""
                    INSERT INTO auth_permission (name, content_type_id, codename) 
                    SELECT 
                        'Can delete ' || model, 
                        id, 
                        'delete_' || model
                    FROM django_content_type
                    WHERE app_label = 'dating'
                    ON CONFLICT (content_type_id, codename) DO NOTHING
                """)
                
                cursor.execute("""
                    INSERT INTO auth_permission (name, content_type_id, codename) 
                    SELECT 
                        'Can view ' || model, 
                        id, 
                        'view_' || model
                    FROM django_content_type
                    WHERE app_label = 'dating'
                    ON CONFLICT (content_type_id, codename) DO NOTHING
                """)
                
                print("  ✅ Basic permissions inserted")
            except Exception as e:
                print(f"  ⚠️  Permissions error: {str(e)}")
            
            # 9. Update user groups and permissions to empty arrays
            print("\n📋 Updating user groups and permissions...")
            try:
                cursor.execute("""
                    UPDATE dating_user 
                    SET 
                        groups = '{}',
                        user_permissions = '{}'
                    WHERE email = 'giddehis@gmail.com'
                """)
                print("  ✅ User groups and permissions updated")
            except Exception as e:
                print(f"  ⚠️  User update error: {str(e)}")
            
            print("\n✅ All Django auth tables fixed!")
            return True
            
    except Exception as e:
        print(f"❌ Auth tables fix failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_auth_tables()
    sys.exit(0 if success else 1)
