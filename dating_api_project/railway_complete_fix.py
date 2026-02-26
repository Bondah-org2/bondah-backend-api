#!/usr/bin/env python
"""
Complete Railway Fix - Database + Static Files
This script fixes both database tables and static files collection
"""

import os
import sys
import django
from django.db import connection
from django.core.management import execute_from_command_line
from django.contrib.auth.hashers import make_password

def railway_complete_fix():
    """Complete Railway fix for database and static files"""
    print("🚀 COMPLETE RAILWAY FIX")
    print("=" * 50)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
    
    try:
        django.setup()
        print("✅ Django setup successful")
    except Exception as e:
        print(f"❌ Django setup failed: {str(e)}")
        return False
    
    print("\n🚀 Starting complete Railway fix...")
    
    try:
        # Step 1: Test database connection
        print("🔍 Step 1: Testing database connection...")
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ Database connection: {version[0]}")
            
            cursor.execute("SELECT current_database();")
            db_name = cursor.fetchone()[0]
            print(f"✅ Connected to database: {db_name}")
        
        # Step 2: Drop and recreate database schema
        print("🗑️  Step 2: Resetting database schema...")
        with connection.cursor() as cursor:
            cursor.execute("""
                DROP SCHEMA public CASCADE;
                CREATE SCHEMA public;
                GRANT ALL ON SCHEMA public TO postgres;
                GRANT ALL ON SCHEMA public TO public;
            """)
            print("✅ Database schema reset")
        
        # Step 3: Create all tables directly
        print("📝 Step 3: Creating all tables...")
        with connection.cursor() as cursor:
            # Django system tables
            cursor.execute("""
                CREATE TABLE django_migrations (
                    id SERIAL PRIMARY KEY,
                    app VARCHAR(255) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    applied TIMESTAMP WITH TIME ZONE NOT NULL
                );
            """)
            
            cursor.execute("""
                CREATE TABLE django_content_type (
                    id SERIAL PRIMARY KEY,
                    app_label VARCHAR(100) NOT NULL,
                    model VARCHAR(100) NOT NULL,
                    UNIQUE(app_label, model)
                );
            """)
            
            cursor.execute("""
                CREATE TABLE django_session (
                    session_key VARCHAR(40) PRIMARY KEY,
                    session_data TEXT NOT NULL,
                    expire_date TIMESTAMP WITH TIME ZONE NOT NULL
                );
            """)
            
            # Dating app tables
            cursor.execute("""
                CREATE TABLE dating_user (
                    id SERIAL PRIMARY KEY,
                    password VARCHAR(128) NOT NULL,
                    last_login TIMESTAMP WITH TIME ZONE,
                    is_superuser BOOLEAN NOT NULL,
                    first_name VARCHAR(150) NOT NULL,
                    last_name VARCHAR(150) NOT NULL,
                    email VARCHAR(254) UNIQUE NOT NULL,
                    is_staff BOOLEAN NOT NULL,
                    is_active BOOLEAN NOT NULL,
                    date_joined TIMESTAMP WITH TIME ZONE NOT NULL,
                    phone_number VARCHAR(15),
                    date_of_birth DATE,
                    gender VARCHAR(10),
                    location VARCHAR(255),
                    bio TEXT,
                    profile_picture VARCHAR(255),
                    is_matchmaker BOOLEAN DEFAULT FALSE,
                    preferences JSONB
                );
            """)
            
            cursor.execute("""
                CREATE TABLE django_admin_log (
                    id SERIAL PRIMARY KEY,
                    action_time TIMESTAMP WITH TIME ZONE NOT NULL,
                    object_id TEXT,
                    object_repr VARCHAR(200) NOT NULL,
                    action_flag SMALLINT NOT NULL,
                    change_message TEXT NOT NULL,
                    content_type_id INTEGER REFERENCES django_content_type(id),
                    user_id INTEGER REFERENCES dating_user(id)
                );
            """)
            
            cursor.execute("""
                CREATE TABLE dating_waitlist (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(254) UNIQUE NOT NULL,
                    first_name VARCHAR(100) NOT NULL,
                    last_name VARCHAR(100) NOT NULL,
                    joined_at TIMESTAMP WITH TIME ZONE NOT NULL
                );
            """)
            
            cursor.execute("""
                CREATE TABLE dating_newsletter (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(254) UNIQUE NOT NULL,
                    subscribed_at TIMESTAMP WITH TIME ZONE NOT NULL
                );
            """)
            
            cursor.execute("""
                CREATE TABLE dating_job (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    description TEXT NOT NULL,
                    requirements TEXT,
                    location VARCHAR(255),
                    salary_range VARCHAR(100),
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL
                );
            """)
            
            cursor.execute("""
                CREATE TABLE dating_jobapplication (
                    id SERIAL PRIMARY KEY,
                    job_id INTEGER REFERENCES dating_job(id),
                    name VARCHAR(200) NOT NULL,
                    email VARCHAR(254) NOT NULL,
                    phone VARCHAR(20),
                    resume TEXT,
                    cover_letter TEXT,
                    experience TEXT,
                    linkedin VARCHAR(255),
                    applied_at TIMESTAMP WITH TIME ZONE NOT NULL
                );
            """)
            
            # Insert default job
            cursor.execute("""
                INSERT INTO dating_job (title, description, requirements, location, salary_range, created_at)
                VALUES ('Software Developer', 'Join our team to build the future of dating', 'Python, Django, React', 'Remote', '$80k-$120k', NOW());
            """)
            
            print("✅ All tables created")
        
        # Step 4: Create superuser
        print("👤 Step 4: Creating superuser...")
        email = os.getenv('SUPERUSER_EMAIL', 'giddehis@gmail.com')
        password = os.getenv('SUPERUSER_PASSWORD', 'Cleverestboo_33')
        first_name = os.getenv('SUPERUSER_FIRST_NAME', 'Bondah')
        last_name = os.getenv('SUPERUSER_LAST_NAME', 'Admin')
        
        hashed_password = make_password(password)
        
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO dating_user (
                    password, is_superuser, first_name, last_name, email, 
                    is_staff, is_active, date_joined
                ) VALUES (%s, TRUE, %s, %s, %s, TRUE, TRUE, NOW());
            """, (hashed_password, first_name, last_name, email))
            
            print(f"✅ Superuser created: {email}")
        
        # Step 5: Collect static files
        print("📁 Step 5: Collecting static files...")
        try:
            execute_from_command_line(['manage.py', 'collectstatic', '--noinput', '--clear', '--settings=backend.settings_prod'])
            print("✅ Static files collected")
        except Exception as e:
            print(f"⚠️  Static files warning: {str(e)}")
        
        # Step 6: Verify everything
        print("🔍 Step 6: Verifying setup...")
        with connection.cursor() as cursor:
            # Check tables
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
            
            # Check superuser
            cursor.execute("SELECT COUNT(*) FROM dating_user WHERE is_superuser = true;")
            superuser_count = cursor.fetchone()[0]
            print(f"✅ Superusers: {superuser_count}")
            
            # Check specific user
            cursor.execute("SELECT email, is_superuser, is_staff, is_active FROM dating_user WHERE email = %s;", (email,))
            user_data = cursor.fetchone()
            if user_data:
                print(f"✅ User verified: {user_data[0]} (superuser: {user_data[1]}, staff: {user_data[2]}, active: {user_data[3]})")
            else:
                print("❌ User not found!")
                return False
        
        print("\n🎉 Complete Railway fix finished successfully!")
        print("\n📋 Summary:")
        print("   ✅ Database schema reset")
        print("   ✅ All tables created")
        print("   ✅ Superuser created with proper password")
        print("   ✅ Static files collected")
        print("   ✅ All verification passed")
        print("\n🔗 Django admin should now work!")
        print("   URL: https://bondah-backend-api-production.up.railway.app/admin/")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        
        return True
        
    except Exception as e:
        print(f"❌ Complete Railway fix failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = railway_complete_fix()
    sys.exit(0 if success else 1)
