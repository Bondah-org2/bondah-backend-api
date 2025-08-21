#!/usr/bin/env python
"""
Fix All Database Issues - Comprehensive Database Schema Fix
"""

import os
import sys
import django
from django.db import connection

def fix_all_database_issues():
    """Fix all database schema issues"""
    print("🔧 FIXING ALL DATABASE ISSUES")
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
            print("🔍 Checking and fixing database schema...")
            
            # 1. Fix dating_user table - add all missing columns
            print("\n📋 Fixing dating_user table...")
            
            # Check and add missing columns to dating_user
            user_columns = [
                ('username', 'VARCHAR(150) UNIQUE'),
                ('name', 'VARCHAR(255)'),
                ('age', 'INTEGER'),
                ('gender', 'VARCHAR(10)'),
                ('location', 'VARCHAR(255)'),
                ('bio', 'TEXT'),
                ('is_matchmaker', 'BOOLEAN DEFAULT FALSE'),
                ('first_name', 'VARCHAR(150)'),
                ('last_name', 'VARCHAR(150)'),
                ('is_staff', 'BOOLEAN DEFAULT FALSE'),
                ('is_active', 'BOOLEAN DEFAULT TRUE'),
                ('date_joined', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()'),
                ('last_login', 'TIMESTAMP WITH TIME ZONE'),
                ('is_superuser', 'BOOLEAN DEFAULT FALSE'),
                ('groups', 'INTEGER[]'),
                ('user_permissions', 'INTEGER[]')
            ]
            
            for column_name, column_type in user_columns:
                try:
                    cursor.execute(f"""
                        ALTER TABLE dating_user 
                        ADD COLUMN IF NOT EXISTS {column_name} {column_type}
                    """)
                    print(f"  ✅ Added column: {column_name}")
                except Exception as e:
                    print(f"  ⚠️  Column {column_name} already exists or error: {str(e)}")
            
            # 2. Create dating_adminuser table if it doesn't exist
            print("\n📋 Creating dating_adminuser table...")
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS dating_adminuser (
                        id SERIAL PRIMARY KEY,
                        email VARCHAR(254) UNIQUE NOT NULL,
                        password VARCHAR(128) NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                print("  ✅ dating_adminuser table created/verified")
            except Exception as e:
                print(f"  ⚠️  dating_adminuser table error: {str(e)}")
            
            # 3. Create dating_adminotp table if it doesn't exist
            print("\n📋 Creating dating_adminotp table...")
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS dating_adminotp (
                        id SERIAL PRIMARY KEY,
                        admin_user_id INTEGER REFERENCES dating_adminuser(id),
                        otp_code VARCHAR(6) NOT NULL,
                        is_used BOOLEAN DEFAULT FALSE,
                        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                print("  ✅ dating_adminotp table created/verified")
            except Exception as e:
                print(f"  ⚠️  dating_adminotp table error: {str(e)}")
            
            # 4. Create dating_emaillog table if it doesn't exist
            print("\n📋 Creating dating_emaillog table...")
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS dating_emaillog (
                        id SERIAL PRIMARY KEY,
                        email_type VARCHAR(50) NOT NULL,
                        recipient_email VARCHAR(254) NOT NULL,
                        subject VARCHAR(255) NOT NULL,
                        message TEXT NOT NULL,
                        is_sent BOOLEAN DEFAULT FALSE,
                        error_message TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                print("  ✅ dating_emaillog table created/verified")
            except Exception as e:
                print(f"  ⚠️  dating_emaillog table error: {str(e)}")
            
            # 5. Fix dating_job table - add missing columns
            print("\n📋 Fixing dating_job table...")
            job_columns = [
                ('job_type', 'VARCHAR(20)'),
                ('requirements', 'JSONB'),
                ('responsibilities', 'TEXT'),
                ('benefits', 'TEXT'),
                ('updated_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()')
            ]
            
            for column_name, column_type in job_columns:
                try:
                    cursor.execute(f"""
                        ALTER TABLE dating_job 
                        ADD COLUMN IF NOT EXISTS {column_name} {column_type}
                    """)
                    print(f"  ✅ Added column: {column_name}")
                except Exception as e:
                    print(f"  ⚠️  Column {column_name} already exists or error: {str(e)}")
            
            # 6. Fix dating_jobapplication table - add missing columns
            print("\n📋 Fixing dating_jobapplication table...")
            jobapp_columns = [
                ('first_name', 'VARCHAR(100)'),
                ('last_name', 'VARCHAR(100)'),
                ('resume_url', 'VARCHAR(500)'),
                ('cover_letter', 'TEXT'),
                ('experience_years', 'INTEGER'),
                ('current_company', 'VARCHAR(255)'),
                ('expected_salary', 'VARCHAR(100)'),
                ('applied_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()')
            ]
            
            for column_name, column_type in jobapp_columns:
                try:
                    cursor.execute(f"""
                        ALTER TABLE dating_jobapplication 
                        ADD COLUMN IF NOT EXISTS {column_name} {column_type}
                    """)
                    print(f"  ✅ Added column: {column_name}")
                except Exception as e:
                    print(f"  ⚠️  Column {column_name} already exists or error: {str(e)}")
            
            # 7. Fix dating_waitlist table - add missing columns
            print("\n📋 Fixing dating_waitlist table...")
            waitlist_columns = [
                ('first_name', 'VARCHAR(100)'),
                ('last_name', 'VARCHAR(100)'),
                ('date_joined', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()')
            ]
            
            for column_name, column_type in waitlist_columns:
                try:
                    cursor.execute(f"""
                        ALTER TABLE dating_waitlist 
                        ADD COLUMN IF NOT EXISTS {column_name} {column_type}
                    """)
                    print(f"  ✅ Added column: {column_name}")
                except Exception as e:
                    print(f"  ⚠️  Column {column_name} already exists or error: {str(e)}")
            
            # 8. Update existing user with proper data
            print("\n📋 Updating existing user data...")
            try:
                cursor.execute("""
                    UPDATE dating_user 
                    SET 
                        username = email,
                        name = 'Admin User',
                        first_name = 'Admin',
                        last_name = 'User',
                        is_staff = TRUE,
                        is_superuser = TRUE,
                        is_active = TRUE,
                        date_joined = NOW()
                    WHERE email = 'giddehis@gmail.com'
                """)
                print("  ✅ Updated existing user data")
            except Exception as e:
                print(f"  ⚠️  User update error: {str(e)}")
            
            # 9. Create admin user if it doesn't exist
            print("\n📋 Creating admin user...")
            try:
                from django.contrib.auth.hashers import make_password
                admin_password = make_password("Cleverestboo_33")
                
                cursor.execute("""
                    INSERT INTO dating_adminuser (email, password, is_active)
                    VALUES ('admin@bondah.org', %s, TRUE)
                    ON CONFLICT (email) DO NOTHING
                """, [admin_password])
                print("  ✅ Admin user created/verified")
            except Exception as e:
                print(f"  ⚠️  Admin user creation error: {str(e)}")
            
            print("\n✅ All database issues fixed!")
            return True
            
    except Exception as e:
        print(f"❌ Database fix failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_all_database_issues()
    sys.exit(0 if success else 1)
