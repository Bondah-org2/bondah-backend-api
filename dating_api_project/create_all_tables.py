#!/usr/bin/env python
"""
Create All Missing Tables - Complete Database Schema Fix
"""

import os
import sys
import django
from django.db import connection

def create_all_tables():
    """Create all missing tables"""
    print("🏗️  CREATING ALL MISSING TABLES")
    print("=" * 50)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
    
    try:
        django.setup()
        print("✅ Django setup successful")
    except Exception as e:
        print(f"❌ Django setup failed: {str(e)}")
        return False
    
    print("\n🏗️  Creating all missing tables...")
    
    try:
        with connection.cursor() as cursor:
            # Create all missing tables based on Django models
            
            # 1. NewsletterSubscriber table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dating_newslettersubscriber (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(254) UNIQUE NOT NULL,
                    date_subscribed TIMESTAMP WITH TIME ZONE NOT NULL
                );
            """)
            print("✅ Created dating_newslettersubscriber table")
            
            # 2. PuzzleVerification table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dating_puzzleverification (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES dating_user(id),
                    question VARCHAR(255) NOT NULL,
                    answer VARCHAR(50) NOT NULL,
                    user_answer VARCHAR(50) NOT NULL,
                    is_correct BOOLEAN NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL
                );
            """)
            print("✅ Created dating_puzzleverification table")
            
            # 3. CoinTransaction table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dating_cointransaction (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES dating_user(id),
                    transaction_type VARCHAR(10) NOT NULL,
                    amount INTEGER NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL
                );
            """)
            print("✅ Created dating_cointransaction table")
            
            # 4. AdminUser table (this was missing!)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dating_adminuser (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(254) UNIQUE NOT NULL,
                    password VARCHAR(128) NOT NULL,
                    is_active BOOLEAN NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    last_login TIMESTAMP WITH TIME ZONE
                );
            """)
            print("✅ Created dating_adminuser table")
            
            # 5. AdminOTP table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dating_adminotp (
                    id SERIAL PRIMARY KEY,
                    admin_user_id INTEGER REFERENCES dating_adminuser(id),
                    otp_code VARCHAR(6) NOT NULL,
                    is_used BOOLEAN NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
                );
            """)
            print("✅ Created dating_adminotp table")
            
            # 6. TranslationLog table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dating_translationlog (
                    id SERIAL PRIMARY KEY,
                    source_text TEXT NOT NULL,
                    translated_text TEXT NOT NULL,
                    source_language VARCHAR(10) NOT NULL,
                    target_language VARCHAR(10) NOT NULL,
                    character_count INTEGER NOT NULL,
                    translation_time DOUBLE PRECISION NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    ip_address INET,
                    user_agent TEXT NOT NULL
                );
            """)
            print("✅ Created dating_translationlog table")
            
            # 7. Update Job table with missing columns
            cursor.execute("""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='dating_job' AND column_name='job_type') THEN
                        ALTER TABLE dating_job ADD COLUMN job_type VARCHAR(20) NOT NULL DEFAULT 'full-time';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='dating_job' AND column_name='category') THEN
                        ALTER TABLE dating_job ADD COLUMN category VARCHAR(20) NOT NULL DEFAULT 'other';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='dating_job' AND column_name='status') THEN
                        ALTER TABLE dating_job ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'open';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='dating_job' AND column_name='requirements') THEN
                        ALTER TABLE dating_job ADD COLUMN requirements JSONB DEFAULT '[]';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='dating_job' AND column_name='responsibilities') THEN
                        ALTER TABLE dating_job ADD COLUMN responsibilities TEXT;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='dating_job' AND column_name='benefits') THEN
                        ALTER TABLE dating_job ADD COLUMN benefits TEXT;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='dating_job' AND column_name='updated_at') THEN
                        ALTER TABLE dating_job ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW();
                    END IF;
                END $$;
            """)
            print("✅ Updated dating_job table with missing columns")
            
            # 8. Update JobApplication table with missing columns
            cursor.execute("""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='dating_jobapplication' AND column_name='first_name') THEN
                        ALTER TABLE dating_jobapplication ADD COLUMN first_name VARCHAR(100) NOT NULL DEFAULT '';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='dating_jobapplication' AND column_name='last_name') THEN
                        ALTER TABLE dating_jobapplication ADD COLUMN last_name VARCHAR(100) NOT NULL DEFAULT '';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='dating_jobapplication' AND column_name='resume_url') THEN
                        ALTER TABLE dating_jobapplication ADD COLUMN resume_url VARCHAR(200);
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='dating_jobapplication' AND column_name='experience_years') THEN
                        ALTER TABLE dating_jobapplication ADD COLUMN experience_years INTEGER;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='dating_jobapplication' AND column_name='current_company') THEN
                        ALTER TABLE dating_jobapplication ADD COLUMN current_company VARCHAR(100);
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='dating_jobapplication' AND column_name='expected_salary') THEN
                        ALTER TABLE dating_jobapplication ADD COLUMN expected_salary VARCHAR(50);
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='dating_jobapplication' AND column_name='status') THEN
                        ALTER TABLE dating_jobapplication ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='dating_jobapplication' AND column_name='updated_at') THEN
                        ALTER TABLE dating_jobapplication ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW();
                    END IF;
                END $$;
            """)
            print("✅ Updated dating_jobapplication table with missing columns")
            
            # Verify all tables exist
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE 'dating_%'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            print(f"\n📋 All dating tables ({len(tables)} total):")
            for table in tables:
                print(f"   - {table[0]}")
        
        print("\n🎉 All tables created successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Table creation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_all_tables()
    sys.exit(0 if success else 1)
