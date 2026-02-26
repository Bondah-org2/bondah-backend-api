-- Create Admin User SQL Script
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
    'pbkdf2_sha256$600000$ulQwzpoLItk8T3NV7bAeMq$W+g74RtHz1bJEjiRuoioTL1NOTijnsC07+fjIEH7QO4=',
    true,
    NOW(),
    NULL
);

-- Verify the user was created
SELECT id, email, is_active, created_at FROM dating_adminuser WHERE email = 'admin@bondah.org';
