#!/usr/bin/env python
"""
Fix User-Auth Table Relationships
"""

import os
import sys
import django
from django.db import connection

def fix_user_auth_relationships():
    """Fix user-auth table relationships"""
    print("🔧 FIXING USER-AUTH RELATIONSHIPS")
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
            print("🔍 Fixing user-auth relationships...")
            
            # 1. Get the user ID
            cursor.execute("SELECT id FROM dating_user WHERE email = 'giddehis@gmail.com'")
            user_result = cursor.fetchone()
            if not user_result:
                print("❌ User not found")
                return False
            
            user_id = user_result[0]
            print(f"✅ Found user ID: {user_id}")
            
            # 2. Get content type ID for user
            cursor.execute("SELECT id FROM django_content_type WHERE app_label = 'dating' AND model = 'user'")
            content_type_result = cursor.fetchone()
            if not content_type_result:
                print("❌ Content type not found")
                return False
            
            content_type_id = content_type_result[0]
            print(f"✅ Found content type ID: {content_type_id}")
            
            # 3. Insert user permissions
            print("\n📋 Inserting user permissions...")
            try:
                # Add permissions for the user
                permissions = [
                    ('add_user', 'Can add user'),
                    ('change_user', 'Can change user'),
                    ('delete_user', 'Can delete user'),
                    ('view_user', 'Can view user'),
                    ('add_job', 'Can add job'),
                    ('change_job', 'Can change job'),
                    ('delete_job', 'Can delete job'),
                    ('view_job', 'Can view job'),
                    ('add_jobapplication', 'Can add job application'),
                    ('change_jobapplication', 'Can change job application'),
                    ('delete_jobapplication', 'Can delete job application'),
                    ('view_jobapplication', 'Can view job application'),
                    ('add_waitlist', 'Can add waitlist'),
                    ('change_waitlist', 'Can change waitlist'),
                    ('delete_waitlist', 'Can delete waitlist'),
                    ('view_waitlist', 'Can view waitlist'),
                ]
                
                for codename, name in permissions:
                    # Insert permission if it doesn't exist
                    cursor.execute("""
                        INSERT INTO auth_permission (name, content_type_id, codename)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (content_type_id, codename) DO NOTHING
                    """, [name, content_type_id, codename])
                
                print("  ✅ User permissions inserted")
            except Exception as e:
                print(f"  ⚠️  Permissions error: {str(e)}")
            
            # 4. Clear existing user-group and user-permission relationships
            print("\n📋 Clearing existing relationships...")
            try:
                cursor.execute("DELETE FROM auth_user_groups WHERE user_id = %s", [user_id])
                cursor.execute("DELETE FROM auth_user_user_permissions WHERE user_id = %s", [user_id])
                print("  ✅ Cleared existing relationships")
            except Exception as e:
                print(f"  ⚠️  Clear relationships error: {str(e)}")
            
            # 5. Update user groups and permissions to NULL instead of empty arrays
            print("\n📋 Updating user fields...")
            try:
                cursor.execute("""
                    UPDATE dating_user 
                    SET 
                        groups = NULL,
                        user_permissions = NULL
                    WHERE email = 'giddehis@gmail.com'
                """)
                print("  ✅ User fields updated to NULL")
            except Exception as e:
                print(f"  ⚠️  User update error: {str(e)}")
            
            # 6. Verify the fix
            print("\n📋 Verifying fix...")
            try:
                cursor.execute("""
                    SELECT 
                        u.id, u.email, u.username, u.is_staff, u.is_superuser,
                        COUNT(ug.group_id) as group_count,
                        COUNT(up.permission_id) as permission_count
                    FROM dating_user u
                    LEFT JOIN auth_user_groups ug ON u.id = ug.user_id
                    LEFT JOIN auth_user_user_permissions up ON u.id = up.user_id
                    WHERE u.email = 'giddehis@gmail.com'
                    GROUP BY u.id, u.email, u.username, u.is_staff, u.is_superuser
                """)
                
                result = cursor.fetchone()
                if result:
                    print(f"  ✅ User verification successful:")
                    print(f"     ID: {result[0]}")
                    print(f"     Email: {result[1]}")
                    print(f"     Username: {result[2]}")
                    print(f"     Is Staff: {result[3]}")
                    print(f"     Is Superuser: {result[4]}")
                    print(f"     Groups: {result[5]}")
                    print(f"     Permissions: {result[6]}")
                else:
                    print("  ❌ User verification failed")
                    return False
                    
            except Exception as e:
                print(f"  ⚠️  Verification error: {str(e)}")
            
            print("\n✅ User-auth relationships fixed!")
            return True
            
    except Exception as e:
        print(f"❌ User-auth relationships fix failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_user_auth_relationships()
    sys.exit(0 if success else 1)
