-- Fix database schema for Django admin
-- Add missing columns to dating_user table

-- Add username column (Django expects this)
ALTER TABLE dating_user ADD COLUMN username VARCHAR(150) UNIQUE;

-- Update existing user to have username
UPDATE dating_user SET username = email WHERE email = 'giddehis@gmail.com';

-- Add any other missing columns that Django might expect
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS groups_id INTEGER;
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS user_permissions_id INTEGER;

-- Verify the user
SELECT email, username, is_superuser, is_staff, is_active FROM dating_user WHERE email = 'giddehis@gmail.com';
