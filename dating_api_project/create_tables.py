#!/usr/bin/env python
"""
Direct database table creation script
Creates tables directly using SQL if migrations fail
"""

import os
import sys
import django
from django.db import connection

def create_tables_directly():
    """Create database tables directly using SQL"""
    print("🔨 DIRECT DATABASE TABLE CREATION")
    print("=" * 50)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
    
    try:
        django.setup()
        print("✅ Django setup successful")
    except Exception as e:
        print(f"❌ Django setup failed: {str(e)}")
        return False
    
    print("\n🚀 Creating tables directly...")
    
    try:
        with connection.cursor() as cursor:
            # Test connection
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ Database connection: {version[0]}")
            
            # Create django_migrations table if it doesn't exist
            print("📝 Creating django_migrations table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS django_migrations (
                    id SERIAL PRIMARY KEY,
                    app VARCHAR(255) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    applied TIMESTAMP WITH TIME ZONE NOT NULL
                );
            """)
            
            # Create dating_user table directly
            print("👤 Creating dating_user table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dating_user (
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
            
            # Create django_content_type table
            print("📋 Creating django_content_type table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS django_content_type (
                    id SERIAL PRIMARY KEY,
                    app_label VARCHAR(100) NOT NULL,
                    model VARCHAR(100) NOT NULL,
                    UNIQUE(app_label, model)
                );
            """)
            
            # Create django_admin_log table
            print("📝 Creating django_admin_log table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS django_admin_log (
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
            
            # Create django_session table
            print("🔐 Creating django_session table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS django_session (
                    session_key VARCHAR(40) PRIMARY KEY,
                    session_data TEXT NOT NULL,
                    expire_date TIMESTAMP WITH TIME ZONE NOT NULL
                );
            """)
            
            # Create dating_waitlist table
            print("⏳ Creating dating_waitlist table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dating_waitlist (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(254) UNIQUE NOT NULL,
                    first_name VARCHAR(100) NOT NULL,
                    last_name VARCHAR(100) NOT NULL,
                    joined_at TIMESTAMP WITH TIME ZONE NOT NULL
                );
            """)
            
            # Create dating_newsletter table
            print("📧 Creating dating_newsletter table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dating_newsletter (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(254) UNIQUE NOT NULL,
                    subscribed_at TIMESTAMP WITH TIME ZONE NOT NULL
                );
            """)
            
            # Create dating_job table
            print("💼 Creating dating_job table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dating_job (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    description TEXT NOT NULL,
                    requirements TEXT,
                    location VARCHAR(255),
                    salary_range VARCHAR(100),
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL
                );
            """)
            
            # Create dating_jobapplication table
            print("📄 Creating dating_jobapplication table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dating_jobapplication (
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
            print("💼 Inserting default job...")
            cursor.execute("""
                INSERT INTO dating_job (title, description, requirements, location, salary_range, created_at)
                VALUES ('Software Developer', 'Join our team to build the future of dating', 'Python, Django, React', 'Remote', '$80k-$120k', NOW())
                ON CONFLICT DO NOTHING;
            """)
            
            # Create superuser directly
            print("👤 Creating superuser...")
            email = os.getenv('SUPERUSER_EMAIL', 'giddehis@gmail.com')
            password = os.getenv('SUPERUSER_PASSWORD', 'Cleverestboo_33')
            first_name = os.getenv('SUPERUSER_FIRST_NAME', 'Bondah')
            last_name = os.getenv('SUPERUSER_LAST_NAME', 'Admin')
            
            # Hash the password (simple hash for now)
            import hashlib
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            
            cursor.execute("""
                INSERT INTO dating_user (password, is_superuser, first_name, last_name, email, is_staff, is_active, date_joined)
                VALUES (%s, TRUE, %s, %s, %s, TRUE, TRUE, NOW())
                ON CONFLICT (email) DO UPDATE SET
                    password = EXCLUDED.password,
                    is_superuser = TRUE,
                    is_staff = TRUE,
                    is_active = TRUE;
            """, (hashed_password, first_name, last_name, email))
            
            print(f"✅ Superuser created: {email}")
            
            # Verify tables
            print("\n🔍 Verifying tables...")
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
            
            print("\n🎉 Direct table creation completed successfully!")
            print(f"\n🔗 Django admin should now work!")
            print(f"   URL: https://bondah-backend-api-production.up.railway.app/admin/")
            print(f"   Email: {email}")
            print(f"   Password: {password}")
            
            return True
            
    except Exception as e:
        print(f"❌ Direct table creation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_tables_directly()
    sys.exit(0 if success else 1)
