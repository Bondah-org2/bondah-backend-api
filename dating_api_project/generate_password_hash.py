#!/usr/bin/env python
"""
Generate Django Password Hash
"""

import os
import sys
import django

def generate_password_hash():
    """Generate Django password hash for admin user"""
    print("🔐 GENERATING PASSWORD HASH")
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
        from django.contrib.auth.hashers import make_password
        
        password = "BondahAdmin2025!"
        hashed_password = make_password(password)
        
        print(f"\n📋 Password: {password}")
        print(f"📋 Hash: {hashed_password}")
        
        # Create SQL script
        sql_script = f"""-- Create Admin User SQL Script
-- Run this in pgAdmin connected to Railway database

-- First, delete any existing admin users
DELETE FROM dating_adminuser WHERE email = 'admin@bondah.org';

-- Create new admin user with Django password hash
-- This hash is for password: BondahAdmin2025!
INSERT INTO dating_adminuser (
    email, 
    password, 
    is_active, 
    created_at, 
    last_login
) VALUES (
    'admin@bondah.org',
    '{hashed_password}',
    true,
    NOW(),
    NULL
);

-- Verify the user was created
SELECT id, email, is_active, created_at FROM dating_adminuser WHERE email = 'admin@bondah.org';
"""
        
        # Write to file
        with open('create_admin_sql.sql', 'w') as f:
            f.write(sql_script)
        
        print(f"\n✅ SQL script written to create_admin_sql.sql")
        print(f"✅ Run this SQL in pgAdmin to create the admin user")
        
        return True
        
    except Exception as e:
        print(f"❌ Hash generation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = generate_password_hash()
    sys.exit(0 if success else 1)
