#!/usr/bin/env python
"""
Fix Job Application Schema - Add missing columns
"""

import os
import sys
import django

def fix_job_application_schema():
    """Fix job application table schema"""
    print("🔧 FIXING JOB APPLICATION SCHEMA")
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
        from django.db import connection
        
        with connection.cursor() as cursor:
            # 1. Add missing columns
            print("\n📋 Adding missing columns...")
            cursor.execute("""
                ALTER TABLE dating_jobapplication 
                ADD COLUMN IF NOT EXISTS first_name VARCHAR(100),
                ADD COLUMN IF NOT EXISTS last_name VARCHAR(100);
            """)
            print("✅ Added first_name and last_name columns")
            
            # 2. Update existing records
            print("\n📋 Updating existing records...")
            cursor.execute("""
                UPDATE dating_jobapplication 
                SET 
                    first_name = COALESCE(first_name, 'Unknown'),
                    last_name = COALESCE(last_name, 'User')
                WHERE first_name IS NULL OR last_name IS NULL;
            """)
            print("✅ Updated existing records")
            
            # 3. Make columns NOT NULL
            print("\n📋 Making columns NOT NULL...")
            cursor.execute("""
                ALTER TABLE dating_jobapplication 
                ALTER COLUMN first_name SET NOT NULL,
                ALTER COLUMN last_name SET NOT NULL;
            """)
            print("✅ Made first_name and last_name NOT NULL")
            
            # 4. Drop old name column (if it exists)
            print("\n📋 Checking for old name column...")
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'dating_jobapplication' 
                AND column_name = 'name';
            """)
            
            if cursor.fetchone():
                cursor.execute("""
                    ALTER TABLE dating_jobapplication 
                    DROP COLUMN name;
                """)
                print("✅ Dropped old name column")
            else:
                print("✅ No old name column found")
            
            # 5. Verify the fix
            print("\n📋 Verifying the fix...")
            cursor.execute("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'dating_jobapplication' 
                AND column_name IN ('first_name', 'last_name')
                ORDER BY column_name;
            """)
            
            columns = cursor.fetchall()
            print("✅ Table structure:")
            for column in columns:
                print(f"   - {column[0]}: {column[1]} ({'NULL' if column[2] == 'YES' else 'NOT NULL'})")
            
            # 6. Test with sample data
            cursor.execute("""
                SELECT id, first_name, last_name, email, job_id, status 
                FROM dating_jobapplication 
                LIMIT 3;
            """)
            
            records = cursor.fetchall()
            print("\n✅ Sample data:")
            for record in records:
                print(f"   - ID {record[0]}: {record[1]} {record[2]} ({record[3]})")
            
            print("\n🎉 JOB APPLICATION SCHEMA FIXED SUCCESSFULLY!")
            return True
            
    except Exception as e:
        print(f"❌ Schema fix failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_job_application_schema()
    sys.exit(0 if success else 1)
