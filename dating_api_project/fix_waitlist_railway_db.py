#!/usr/bin/env python
"""
Fix Waitlist Database in Railway
"""
import os
import sys
import django
from django.db import connection

def fix_waitlist_railway_db():
    """Fix waitlist database issues in Railway"""
    print("🔧 FIXING WAITLIST DATABASE IN RAILWAY")
    print("=" * 50)
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
    django.setup()
    
    with connection.cursor() as cursor:
        # Check current table structure
        print("\n📋 Checking current table structure...")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'dating_waitlist' 
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        print("Current columns:")
        for col in columns:
            print(f"  - {col[0]} ({col[1]}, nullable: {col[2]})")
        
        # Check if joined_at column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'dating_waitlist' 
            AND column_name = 'joined_at';
        """)
        
        if cursor.fetchone():
            print("\n🔧 Found 'joined_at' column, renaming to 'date_joined'...")
            try:
                cursor.execute("""
                    ALTER TABLE dating_waitlist 
                    RENAME COLUMN joined_at TO date_joined;
                """)
                print("✅ Column renamed successfully")
            except Exception as e:
                print(f"❌ Rename failed: {str(e)}")
                # Try dropping and recreating
                print("🔧 Trying alternative fix...")
                cursor.execute("""
                    ALTER TABLE dating_waitlist 
                    DROP COLUMN joined_at;
                """)
                cursor.execute("""
                    ALTER TABLE dating_waitlist 
                    ADD COLUMN date_joined TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL;
                """)
                print("✅ Column recreated successfully")
        else:
            print("\n✅ 'date_joined' column already exists")
        
        # Make sure date_joined is NOT NULL
        cursor.execute("""
            ALTER TABLE dating_waitlist 
            ALTER COLUMN date_joined SET NOT NULL;
        """)
        print("✅ Made date_joined NOT NULL")
        
        # Add default timestamp
        cursor.execute("""
            ALTER TABLE dating_waitlist 
            ALTER COLUMN date_joined SET DEFAULT CURRENT_TIMESTAMP;
        """)
        print("✅ Added default timestamp")
        
        # Update any existing records with null date_joined
        cursor.execute("""
            UPDATE dating_waitlist 
            SET date_joined = CURRENT_TIMESTAMP 
            WHERE date_joined IS NULL;
        """)
        updated_count = cursor.rowcount
        print(f"✅ Updated {updated_count} records")
        
        # Show final results
        print("\n📋 Final table structure:")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'dating_waitlist' 
            ORDER BY ordinal_position;
        """)
        
        final_columns = cursor.fetchall()
        for col in final_columns:
            print(f"  - {col[0]} ({col[1]}, nullable: {col[2]}, default: {col[3]})")
        
        # Show current entries
        print("\n📋 Current waitlist entries:")
        cursor.execute("""
            SELECT id, email, first_name, last_name, date_joined 
            FROM dating_waitlist 
            ORDER BY date_joined DESC 
            LIMIT 10;
        """)
        
        entries = cursor.fetchall()
        for entry in entries:
            print(f"  - ID: {entry[0]}, Email: {entry[1]}, Name: {entry[2]} {entry[3]}, Date: {entry[4]}")
        
        print(f"\n✅ Total entries: {len(entries)}")
        
        # Test creating a new entry
        print("\n🧪 Testing new entry creation...")
        import time
        test_email = f"railway_test_{int(time.time())}@example.com"
        
        try:
            cursor.execute("""
                INSERT INTO dating_waitlist (email, first_name, last_name) 
                VALUES (%s, %s, %s)
            """, (test_email, "Railway", "Test"))
            
            print(f"✅ Test entry created: {test_email}")
            
            # Verify it was created
            cursor.execute("""
                SELECT * FROM dating_waitlist WHERE email = %s
            """, (test_email,))
            
            if cursor.fetchone():
                print("✅ Test entry verified in database")
                
                # Clean up
                cursor.execute("""
                    DELETE FROM dating_waitlist WHERE email = %s
                """, (test_email,))
                print("✅ Test entry cleaned up")
            else:
                print("❌ Test entry not found!")
                
        except Exception as e:
            print(f"❌ Test entry creation failed: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    fix_waitlist_railway_db()
