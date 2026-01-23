#!/usr/bin/env python
"""
Railway Database Schema Fix Script
Fixes missing columns and tables in Railway PostgreSQL database
"""

import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
django.setup()

from django.db import connection
from django.core.management import execute_from_command_line

def fix_database_schema():
    """Fix missing database schema issues on Railway"""
    print("🔧 Fixing Railway Database Schema...")
    
    with connection.cursor() as cursor:
        try:
            # 1. Check if latitude column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='dating_user' AND column_name='latitude'
            """)
            latitude_exists = cursor.fetchone()
            
            if not latitude_exists:
                print("➕ Adding missing latitude column to dating_user table...")
                cursor.execute("""
                    ALTER TABLE dating_user 
                    ADD COLUMN latitude DECIMAL(10,8) NULL
                """)
                print("✅ latitude column added")
            else:
                print("✅ latitude column already exists")
            
            # 2. Check if longitude column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='dating_user' AND column_name='longitude'
            """)
            longitude_exists = cursor.fetchone()
            
            if not longitude_exists:
                print("➕ Adding missing longitude column to dating_user table...")
                cursor.execute("""
                    ALTER TABLE dating_user 
                    ADD COLUMN longitude DECIMAL(11,8) NULL
                """)
                print("✅ longitude column added")
            else:
                print("✅ longitude column already exists")
            
            # 3. Check if address column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='dating_user' AND column_name='address'
            """)
            address_exists = cursor.fetchone()
            
            if not address_exists:
                print("➕ Adding missing address column to dating_user table...")
                cursor.execute("""
                    ALTER TABLE dating_user 
                    ADD COLUMN address TEXT NULL
                """)
                print("✅ address column added")
            else:
                print("✅ address column already exists")
            
            # 4. Check if city column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='dating_user' AND column_name='city'
            """)
            city_exists = cursor.fetchone()
            
            if not city_exists:
                print("➕ Adding missing city column to dating_user table...")
                cursor.execute("""
                    ALTER TABLE dating_user 
                    ADD COLUMN city VARCHAR(100) NULL
                """)
                print("✅ city column added")
            else:
                print("✅ city column already exists")
            
            # 5. Check if state column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='dating_user' AND column_name='state'
            """)
            state_exists = cursor.fetchone()
            
            if not state_exists:
                print("➕ Adding missing state column to dating_user table...")
                cursor.execute("""
                    ALTER TABLE dating_user 
                    ADD COLUMN state VARCHAR(100) NULL
                """)
                print("✅ state column added")
            else:
                print("✅ state column already exists")
            
            # 6. Check if country column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='dating_user' AND column_name='country'
            """)
            country_exists = cursor.fetchone()
            
            if not country_exists:
                print("➕ Adding missing country column to dating_user table...")
                cursor.execute("""
                    ALTER TABLE dating_user 
                    ADD COLUMN country VARCHAR(100) NULL
                """)
                print("✅ country column added")
            else:
                print("✅ country column already exists")
            
            # 7. Check if postal_code column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='dating_user' AND column_name='postal_code'
            """)
            postal_code_exists = cursor.fetchone()
            
            if not postal_code_exists:
                print("➕ Adding missing postal_code column to dating_user table...")
                cursor.execute("""
                    ALTER TABLE dating_user 
                    ADD COLUMN postal_code VARCHAR(20) NULL
                """)
                print("✅ postal_code column added")
            else:
                print("✅ postal_code column already exists")
            
            # 8. Check if location_privacy column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='dating_user' AND column_name='location_privacy'
            """)
            location_privacy_exists = cursor.fetchone()
            
            if not location_privacy_exists:
                print("➕ Adding missing location_privacy column to dating_user table...")
                cursor.execute("""
                    ALTER TABLE dating_user 
                    ADD COLUMN location_privacy VARCHAR(20) DEFAULT 'public'
                """)
                print("✅ location_privacy column added")
            else:
                print("✅ location_privacy column already exists")
            
            # 9. Check if location_sharing_enabled column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='dating_user' AND column_name='location_sharing_enabled'
            """)
            location_sharing_exists = cursor.fetchone()
            
            if not location_sharing_exists:
                print("➕ Adding missing location_sharing_enabled column to dating_user table...")
                cursor.execute("""
                    ALTER TABLE dating_user 
                    ADD COLUMN location_sharing_enabled BOOLEAN DEFAULT TRUE
                """)
                print("✅ location_sharing_enabled column added")
            else:
                print("✅ location_sharing_enabled column already exists")
            
            # 10. Check if location_update_frequency column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='dating_user' AND column_name='location_update_frequency'
            """)
            location_update_freq_exists = cursor.fetchone()
            
            if not location_update_freq_exists:
                print("➕ Adding missing location_update_frequency column to dating_user table...")
                cursor.execute("""
                    ALTER TABLE dating_user 
                    ADD COLUMN location_update_frequency VARCHAR(20) DEFAULT 'manual'
                """)
                print("✅ location_update_frequency column added")
            else:
                print("✅ location_update_frequency column already exists")
            
            # 11. Check if is_matchmaker column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='dating_user' AND column_name='is_matchmaker'
            """)
            is_matchmaker_exists = cursor.fetchone()
            
            if not is_matchmaker_exists:
                print("➕ Adding missing is_matchmaker column to dating_user table...")
                cursor.execute("""
                    ALTER TABLE dating_user 
                    ADD COLUMN is_matchmaker BOOLEAN DEFAULT FALSE
                """)
                print("✅ is_matchmaker column added")
            else:
                print("✅ is_matchmaker column already exists")
            
            # 12. Check if bio column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='dating_user' AND column_name='bio'
            """)
            bio_exists = cursor.fetchone()
            
            if not bio_exists:
                print("➕ Adding missing bio column to dating_user table...")
                cursor.execute("""
                    ALTER TABLE dating_user 
                    ADD COLUMN bio TEXT DEFAULT ''
                """)
                print("✅ bio column added")
            else:
                print("✅ bio column already exists")
            
            # 13. Check if last_location_update column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='dating_user' AND column_name='last_location_update'
            """)
            last_location_update_exists = cursor.fetchone()
            
            if not last_location_update_exists:
                print("➕ Adding missing last_location_update column to dating_user table...")
                cursor.execute("""
                    ALTER TABLE dating_user 
                    ADD COLUMN last_location_update TIMESTAMP NULL
                """)
                print("✅ last_location_update column added")
            else:
                print("✅ last_location_update column already exists")
            
            # 14. Check if max_distance column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='dating_user' AND column_name='max_distance'
            """)
            max_distance_exists = cursor.fetchone()
            
            if not max_distance_exists:
                print("➕ Adding missing max_distance column to dating_user table...")
                cursor.execute("""
                    ALTER TABLE dating_user 
                    ADD COLUMN max_distance INTEGER DEFAULT 50
                """)
                print("✅ max_distance column added")
            else:
                print("✅ max_distance column already exists")
            
            # 15. Check if age_range_min column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='dating_user' AND column_name='age_range_min'
            """)
            age_range_min_exists = cursor.fetchone()
            
            if not age_range_min_exists:
                print("➕ Adding missing age_range_min column to dating_user table...")
                cursor.execute("""
                    ALTER TABLE dating_user 
                    ADD COLUMN age_range_min INTEGER DEFAULT 18
                """)
                print("✅ age_range_min column added")
            else:
                print("✅ age_range_min column already exists")
            
            # 16. Check if age_range_max column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='dating_user' AND column_name='age_range_max'
            """)
            age_range_max_exists = cursor.fetchone()
            
            if not age_range_max_exists:
                print("➕ Adding missing age_range_max column to dating_user table...")
                cursor.execute("""
                    ALTER TABLE dating_user 
                    ADD COLUMN age_range_max INTEGER DEFAULT 100
                """)
                print("✅ age_range_max column added")
            else:
                print("✅ age_range_max column already exists")
            
            # 17. Check if preferred_gender column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='dating_user' AND column_name='preferred_gender'
            """)
            preferred_gender_exists = cursor.fetchone()
            
            if not preferred_gender_exists:
                print("➕ Adding missing preferred_gender column to dating_user table...")
                cursor.execute("""
                    ALTER TABLE dating_user 
                    ADD COLUMN preferred_gender VARCHAR(10) NULL
                """)
                print("✅ preferred_gender column added")
            else:
                print("✅ preferred_gender column already exists")
            
            # 18. Check if django_site table exists
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name='django_site'
            """)
            django_site_exists = cursor.fetchone()
            
            if not django_site_exists:
                print("➕ Creating missing django_site table...")
                cursor.execute("""
                    CREATE TABLE django_site (
                        id SERIAL PRIMARY KEY,
                        domain VARCHAR(100) NOT NULL UNIQUE,
                        name VARCHAR(50) NOT NULL
                    )
                """)
                # Insert default site
                cursor.execute("""
                    INSERT INTO django_site (domain, name) 
                    VALUES ('bondah.org', 'Bondah Dating')
                """)
                print("✅ django_site table created with default site")
            else:
                print("✅ django_site table already exists")
            
            print("\n🎉 Database schema fix completed successfully!")
            
        except Exception as e:
            print(f"❌ Error fixing database schema: {e}")
            return False
    
    return True

if __name__ == "__main__":
    success = fix_database_schema()
    if success:
        print("\n✅ Railway database schema is now fixed!")
        print("🚀 You can now access Django admin without errors.")
    else:
        print("\n❌ Database schema fix failed!")
        sys.exit(1)
