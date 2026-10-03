#!/usr/bin/env python
"""
Fix Database Columns - Add Missing Columns to Match Django Model
"""

import os
import sys
import django
from django.db import connection

def fix_database_columns():
    """Fix missing columns in database"""
    print("🔧 FIXING DATABASE COLUMNS")
    print("=" * 50)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
    
    try:
        django.setup()
        print("✅ Django setup successful")
    except Exception as e:
        print(f"❌ Django setup failed: {str(e)}")
        return False
    
    print("\n🔧 Fixing database columns...")
    
    try:
        with connection.cursor() as cursor:
            # Add missing columns if they don't exist
            columns_to_add = [
                ('name', 'VARCHAR(100)'),
                ('age', 'INTEGER'),
                ('gender', 'VARCHAR(10)'),
                ('location', 'VARCHAR(100)'),
                ('bio', 'TEXT'),
                ('is_matchmaker', 'BOOLEAN DEFAULT FALSE'),
            ]
            
            for column_name, column_type in columns_to_add:
                cursor.execute(f"""
                    DO $$ 
                    BEGIN 
                        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                      WHERE table_name='dating_user' AND column_name='{column_name}') THEN
                            ALTER TABLE dating_user ADD COLUMN {column_name} {column_type};
                        END IF;
                    END $$;
                """)
                print(f"✅ Added column: {column_name}")
            
            # Update existing user with name
            cursor.execute("""
                UPDATE dating_user SET name = 'Bondah Admin' 
                WHERE email = 'giddehis@gmail.com' AND (name IS NULL OR name = '');
            """)
            
            # Verify the user
            cursor.execute("""
                SELECT email, username, name, is_superuser, is_staff, is_active 
                FROM dating_user WHERE email = 'giddehis@gmail.com';
            """)
            user_data = cursor.fetchone()
            if user_data:
                print(f"✅ User verified: {user_data[0]} (username: {user_data[1]}, name: {user_data[2]}, superuser: {user_data[3]}, staff: {user_data[4]}, active: {user_data[5]})")
            else:
                print("❌ User not found!")
                return False
            
            # Show all columns in the table
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'dating_user' 
                ORDER BY column_name;
            """)
            columns = cursor.fetchall()
            print(f"\n📋 All columns in dating_user table ({len(columns)} total):")
            for column in columns:
                print(f"   - {column[0]} ({column[1]})")
        
        print("\n🎉 Database columns fixed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database columns fix failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_database_columns()
    sys.exit(0 if success else 1)
