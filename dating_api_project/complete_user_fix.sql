-- Complete User Fix for Django Admin
-- Run this in pgAdmin to fix all user-related issues

-- 1. Create the missing many-to-many relationship tables
CREATE TABLE IF NOT EXISTS dating_user_groups (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    group_id INTEGER NOT NULL,
    UNIQUE(user_id, group_id)
);

CREATE TABLE IF NOT EXISTS dating_user_user_permissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    UNIQUE(user_id, permission_id)
);

-- 2. Remove problematic fields from dating_user table
ALTER TABLE dating_user DROP COLUMN IF EXISTS groups;
ALTER TABLE dating_user DROP COLUMN IF EXISTS user_permissions;

-- 3. Ensure all required columns exist in dating_user
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS username VARCHAR(150) UNIQUE;
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS name VARCHAR(255);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS age INTEGER;
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS gender VARCHAR(10);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS location VARCHAR(255);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS bio TEXT;
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS is_matchmaker BOOLEAN DEFAULT FALSE;
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS first_name VARCHAR(150);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS last_name VARCHAR(150);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS is_staff BOOLEAN DEFAULT FALSE;
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS date_joined TIMESTAMP WITH TIME ZONE DEFAULT NOW();
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS last_login TIMESTAMP WITH TIME ZONE;
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS is_superuser BOOLEAN DEFAULT FALSE;

-- 4. Update user with proper data
UPDATE dating_user 
SET 
    username = email,
    name = 'Admin User',
    first_name = 'Admin',
    last_name = 'User',
    is_staff = TRUE,
    is_superuser = TRUE,
    is_active = TRUE,
    date_joined = NOW()
WHERE email = 'giddehis@gmail.com';

-- 5. Verify the fix
SELECT 
    'User Data' as check_type,
    u.id, u.email, u.username, u.is_staff, u.is_superuser, u.is_active
FROM dating_user u
WHERE u.email = 'giddehis@gmail.com'

UNION ALL

SELECT 
    'Table Counts' as check_type,
    (SELECT COUNT(*) FROM dating_user_groups)::INTEGER,
    (SELECT COUNT(*) FROM dating_user_user_permissions)::INTEGER,
    (SELECT COUNT(*) FROM auth_group)::INTEGER,
    (SELECT COUNT(*) FROM auth_permission)::INTEGER,
    (SELECT COUNT(*) FROM django_content_type)::INTEGER;
