#!/usr/bin/env python
"""
Create superuser with proper Django password hash
"""

import os
import sys
import django
from django.contrib.auth.hashers import make_password

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')

try:
    django.setup()
    print("✅ Django setup successful")
except Exception as e:
    print(f"❌ Django setup failed: {str(e)}")
    sys.exit(1)

# Generate password hash
password = 'Cleverestboo_33'
hashed_password = make_password(password)

print(f"✅ Password hash generated for: {password}")
print(f"Hash: {hashed_password}")

# Create the SQL insert statement
sql = f"""
INSERT INTO dating_user (
    password, is_superuser, first_name, last_name, email, 
    is_staff, is_active, date_joined
) VALUES (
    '{hashed_password}', 
    TRUE, 'Bondah', 'Admin', 'giddehis@gmail.com', TRUE, TRUE, NOW()
);
"""

print("\n📋 SQL to run in pgAdmin:")
print("=" * 50)
print(sql)
print("=" * 50)

print("\n🎯 Instructions:")
print("1. Copy the SQL above")
print("2. Open pgAdmin Query Tool")
print("3. Paste and execute the SQL")
print("4. Test Django admin login")
