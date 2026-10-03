-- =====================================================
-- VERIFICATION TABLES - SAFE VERSION
-- =====================================================
-- This script creates ONLY the missing verification tables
-- Run this in pgAdmin after checking existing tables

-- =====================================================
-- SECTION 1: Create EmailVerification Table
-- =====================================================

CREATE TABLE IF NOT EXISTS dating_emailverification (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    email VARCHAR(254) NOT NULL,
    otp_code VARCHAR(4) NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    is_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    verified_at TIMESTAMP NULL
);

-- Create indexes for EmailVerification
CREATE INDEX IF NOT EXISTS idx_email_verification_user ON dating_emailverification(user_id);
CREATE INDEX IF NOT EXISTS idx_email_verification_email ON dating_emailverification(email);
CREATE INDEX IF NOT EXISTS idx_email_verification_otp ON dating_emailverification(otp_code);
CREATE INDEX IF NOT EXISTS idx_email_verification_created ON dating_emailverification(created_at);
CREATE INDEX IF NOT EXISTS idx_email_verification_expires ON dating_emailverification(expires_at);

-- =====================================================
-- SECTION 2: Create PhoneVerification Table
-- =====================================================

CREATE TABLE IF NOT EXISTS dating_phoneverification (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    phone_number VARCHAR(20) NOT NULL,
    country_code VARCHAR(5) DEFAULT '+1',
    otp_code VARCHAR(4) NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    is_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    verified_at TIMESTAMP NULL
);

-- Create indexes for PhoneVerification
CREATE INDEX IF NOT EXISTS idx_phone_verification_user ON dating_phoneverification(user_id);
CREATE INDEX IF NOT EXISTS idx_phone_verification_phone ON dating_phoneverification(phone_number);
CREATE INDEX IF NOT EXISTS idx_phone_verification_country ON dating_phoneverification(country_code);
CREATE INDEX IF NOT EXISTS idx_phone_verification_otp ON dating_phoneverification(otp_code);
CREATE INDEX IF NOT EXISTS idx_phone_verification_created ON dating_phoneverification(created_at);
CREATE INDEX IF NOT EXISTS idx_phone_verification_expires ON dating_phoneverification(expires_at);

-- =====================================================
-- SECTION 3: Create UserRoleSelection Table
-- =====================================================

CREATE TABLE IF NOT EXISTS dating_userroleselection (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES dating_user(id) ON DELETE CASCADE,
    selected_role VARCHAR(20) NOT NULL CHECK (selected_role IN ('looking_for_love', 'bondmaker')),
    selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for UserRoleSelection
CREATE INDEX IF NOT EXISTS idx_role_selection_user ON dating_userroleselection(user_id);
CREATE INDEX IF NOT EXISTS idx_role_selection_role ON dating_userroleselection(selected_role);
CREATE INDEX IF NOT EXISTS idx_role_selection_selected ON dating_userroleselection(selected_at);

-- =====================================================
-- SECTION 4: Create LocationPermission Table (if not exists)
-- =====================================================

CREATE TABLE IF NOT EXISTS dating_locationpermission (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES dating_user(id) ON DELETE CASCADE,
    location_enabled BOOLEAN DEFAULT FALSE,
    background_location_enabled BOOLEAN DEFAULT FALSE,
    precise_location_enabled BOOLEAN DEFAULT FALSE,
    location_services_consent BOOLEAN DEFAULT FALSE,
    location_data_sharing BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for LocationPermission
CREATE INDEX IF NOT EXISTS idx_permission_user ON dating_locationpermission(user_id);

-- =====================================================
-- SECTION 5: Verify All Tables Exist
-- =====================================================

-- Check if all verification tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
    'dating_emailverification',
    'dating_phoneverification',
    'dating_userroleselection',
    'dating_livenessverification',
    'dating_userverificationstatus',
    'dating_socialaccount',
    'dating_deviceregistration',
    'dating_locationhistory',
    'dating_usermatch',
    'dating_locationpermission'
)
ORDER BY table_name;

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================
-- If you see all 10 tables listed above,
-- then the verification tables were created successfully!
-- Your mobile app backend is now fully operational.
