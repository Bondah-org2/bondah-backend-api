#!/usr/bin/env python
"""
Fix Waitlist Database Issues
"""
import os
import sys
import django
from django.db import connection

def fix_waitlist_database():
    """Fix waitlist database column issues"""
    print("🔧 FIXING WAITLIST DATABASE ISSUES")
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
        
        # Check if joined_at column exists (wrong name)
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'dating_waitlist' 
            AND column_name = 'joined_at';
        """)
        
        if cursor.fetchone():
            print("\n🔧 Found 'joined_at' column (wrong name), renaming to 'date_joined'...")
            cursor.execute("""
                ALTER TABLE dating_waitlist 
                RENAME COLUMN joined_at TO date_joined;
            """)
            print("✅ Column renamed successfully")
        else:
            print("\n✅ 'date_joined' column already exists")
        
        # Check if date_joined column exists and has correct properties
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'dating_waitlist' 
            AND column_name = 'date_joined';
        """)
        
        date_joined_info = cursor.fetchone()
        if date_joined_info:
            print(f"✅ date_joined column: {date_joined_info}")
            
            # Make sure it's not nullable and has default
            if date_joined_info[2] == 'YES':  # is_nullable
                print("🔧 Making date_joined NOT NULL...")
                cursor.execute("""
                    ALTER TABLE dating_waitlist 
                    ALTER COLUMN date_joined SET NOT NULL;
                """)
                print("✅ date_joined is now NOT NULL")
            
            if not date_joined_info[3]:  # no default
                print("🔧 Adding default to date_joined...")
                cursor.execute("""
                    ALTER TABLE dating_waitlist 
                    ALTER COLUMN date_joined SET DEFAULT CURRENT_TIMESTAMP;
                """)
                print("✅ date_joined now has default")
        else:
            print("❌ date_joined column not found!")
        
        # Update any existing records with null date_joined
        print("\n🔧 Updating existing records with null date_joined...")
        cursor.execute("""
            UPDATE dating_waitlist 
            SET date_joined = CURRENT_TIMESTAMP 
            WHERE date_joined IS NULL;
        """)
        updated_count = cursor.rowcount
        print(f"✅ Updated {updated_count} records")
        
        # Show current waitlist entries
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
        
        print(f"\n✅ Total waitlist entries: {len(entries)}")
        
        # Test creating a new entry
        print("\n🧪 Testing new waitlist entry creation...")
        try:
            from dating.models import Waitlist
            test_entry = Waitlist.objects.create(
                email=f"test{int(time.time())}@example.com",
                first_name="Test",
                last_name="User"
            )
            print(f"✅ Test entry created: {test_entry}")
            
            # Clean up test entry
            test_entry.delete()
            print("✅ Test entry cleaned up")
            
        except Exception as e:
            print(f"❌ Test entry creation failed: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    import time
    fix_waitlist_database()
