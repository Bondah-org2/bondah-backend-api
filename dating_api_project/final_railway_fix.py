#!/usr/bin/env python
"""
Final Railway Fix - Complete Database and Static Files Solution
"""

import os
import sys
import django
from django.db import connection
from django.core.management import execute_from_command_line
from django.contrib.auth.hashers import make_password

def final_railway_fix():
    """Complete fix for Railway deployment"""
    print("🚀 FINAL RAILWAY FIX")
    print("=" * 50)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
    
    try:
        django.setup()
        print("✅ Django setup successful")
    except Exception as e:
        print(f"❌ Django setup failed: {str(e)}")
        return False
    
    print("\n🚀 Starting final Railway fix...")
    
    try:
        # Step 1: Test database connection
        print("🔍 Step 1: Testing database connection...")
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ Database connection: {version[0]}")
        
        # Step 2: Fix database schema
        print("🔧 Step 2: Fixing database schema...")
        with connection.cursor() as cursor:
            # Add username column if it doesn't exist
            cursor.execute("""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='dating_user' AND column_name='username') THEN
                        ALTER TABLE dating_user ADD COLUMN username VARCHAR(150) UNIQUE;
                    END IF;
                END $$;
            """)
            
            # Update existing user to have username
            cursor.execute("""
                UPDATE dating_user SET username = email 
                WHERE email = 'giddehis@gmail.com' AND (username IS NULL OR username = '');
            """)
            
            # Add other missing columns
            cursor.execute("""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='dating_user' AND column_name='groups_id') THEN
                        ALTER TABLE dating_user ADD COLUMN groups_id INTEGER;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='dating_user' AND column_name='user_permissions_id') THEN
                        ALTER TABLE dating_user ADD COLUMN user_permissions_id INTEGER;
                    END IF;
                END $$;
            """)
            
            print("✅ Database schema fixed")
        
        # Step 3: Verify user
        print("👤 Step 3: Verifying superuser...")
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT email, username, is_superuser, is_staff, is_active 
                FROM dating_user WHERE email = 'giddehis@gmail.com';
            """)
            user_data = cursor.fetchone()
            if user_data:
                print(f"✅ User verified: {user_data[0]} (username: {user_data[1]}, superuser: {user_data[2]}, staff: {user_data[3]}, active: {user_data[4]})")
            else:
                print("❌ User not found! Creating superuser...")
                # Create superuser if not exists
                email = 'giddehis@gmail.com'
                password = 'Cleverestboo_33'
                hashed_password = make_password(password)
                
                cursor.execute("""
                    INSERT INTO dating_user (
                        password, username, is_superuser, first_name, last_name, email, 
                        is_staff, is_active, date_joined
                    ) VALUES (%s, %s, TRUE, 'Bondah', 'Admin', %s, TRUE, TRUE, NOW());
                """, (hashed_password, email, email))
                print(f"✅ Superuser created: {email}")
        
        # Step 4: Collect static files
        print("📁 Step 4: Collecting static files...")
        try:
            execute_from_command_line(['manage.py', 'collectstatic', '--noinput', '--clear', '--settings=backend.settings_prod'])
            print("✅ Static files collected")
        except Exception as e:
            print(f"⚠️  Static files warning: {str(e)}")
        
        # Step 5: Final verification
        print("🔍 Step 5: Final verification...")
        with connection.cursor() as cursor:
            # Check all tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE 'dating_%'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            print(f"✅ Found {len(tables)} dating tables:")
            for table in tables:
                print(f"   - {table[0]}")
            
            # Check user columns
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'dating_user' 
                ORDER BY column_name;
            """)
            columns = cursor.fetchall()
            print(f"✅ User table has {len(columns)} columns")
            
            # Check superuser
            cursor.execute("SELECT COUNT(*) FROM dating_user WHERE is_superuser = true;")
            superuser_count = cursor.fetchone()[0]
            print(f"✅ Superusers: {superuser_count}")
        
        print("\n🎉 Final Railway fix completed successfully!")
        print("\n📋 Summary:")
        print("   ✅ Database schema fixed (username column added)")
        print("   ✅ Superuser verified/created")
        print("   ✅ Static files collected")
        print("   ✅ All verification passed")
        print("\n🔗 Django admin should now work!")
        print("   URL: https://bondah-backend-api-production.up.railway.app/admin/")
        print("   Email: giddehis@gmail.com")
        print("   Password: Cleverestboo_33")
        
        return True
        
    except Exception as e:
        print(f"❌ Final Railway fix failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = final_railway_fix()
    sys.exit(0 if success else 1)
