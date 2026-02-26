-- =====================================================
-- VERIFICATION TABLES - Run in pgAdmin
-- =====================================================
-- This script creates the new verification tables for mobile app
-- Run this in pgAdmin after the previous database fix

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
-- SECTION 4: Create LivenessVerification Table (if not exists)
-- =====================================================

CREATE TABLE IF NOT EXISTS dating_livenessverification (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'passed', 'failed', 'expired')),
    actions_required JSONB DEFAULT '[]',
    actions_completed JSONB DEFAULT '[]',
    confidence_score DOUBLE PRECISION DEFAULT 0.0,
    face_quality_score DOUBLE PRECISION DEFAULT 0.0,
    is_live_person BOOLEAN DEFAULT FALSE,
    spoof_detected BOOLEAN DEFAULT FALSE,
    spoof_type VARCHAR(50) NULL,
    video_url TEXT NULL,
    images_data JSONB DEFAULT '{}',
    verification_method VARCHAR(50) DEFAULT 'video',
    provider VARCHAR(50) DEFAULT 'internal',
    provider_response JSONB DEFAULT '{}',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    expires_at TIMESTAMP NULL,
    attempts_count INTEGER DEFAULT 1,
    max_attempts INTEGER DEFAULT 3
);

-- Create indexes for LivenessVerification
CREATE INDEX IF NOT EXISTS idx_liveness_user_status ON dating_livenessverification(user_id, status);
CREATE INDEX IF NOT EXISTS idx_liveness_session ON dating_livenessverification(session_id);
CREATE INDEX IF NOT EXISTS idx_liveness_started ON dating_livenessverification(started_at);

-- =====================================================
-- SECTION 5: Create UserVerificationStatus Table (if not exists)
-- =====================================================

CREATE TABLE IF NOT EXISTS dating_userverificationstatus (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES dating_user(id) ON DELETE CASCADE,
    email_verified BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE,
    liveness_verified BOOLEAN DEFAULT FALSE,
    identity_verified BOOLEAN DEFAULT FALSE,
    verification_level VARCHAR(20) DEFAULT 'none' CHECK (verification_level IN ('none', 'email', 'phone', 'liveness', 'full')),
    verified_badge BOOLEAN DEFAULT FALSE,
    trusted_member BOOLEAN DEFAULT FALSE,
    email_verified_at TIMESTAMP NULL,
    phone_verified_at TIMESTAMP NULL,
    liveness_verified_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for UserVerificationStatus
CREATE INDEX IF NOT EXISTS idx_verification_user ON dating_userverificationstatus(user_id);
CREATE INDEX IF NOT EXISTS idx_verification_level ON dating_userverificationstatus(verification_level);

-- =====================================================
-- SECTION 6: Create SocialAccount Table (if not exists)
-- =====================================================

CREATE TABLE IF NOT EXISTS dating_socialaccount (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    provider VARCHAR(20) NOT NULL CHECK (provider IN ('google', 'apple', 'facebook')),
    provider_user_id VARCHAR(255) NOT NULL,
    provider_data JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider, provider_user_id)
);

-- Create indexes for SocialAccount
CREATE INDEX IF NOT EXISTS idx_social_user ON dating_socialaccount(user_id);
CREATE INDEX IF NOT EXISTS idx_social_provider ON dating_socialaccount(provider);

-- =====================================================
-- SECTION 7: Create DeviceRegistration Table (if not exists)
-- =====================================================

CREATE TABLE IF NOT EXISTS dating_deviceregistration (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    device_id VARCHAR(255) UNIQUE NOT NULL,
    device_type VARCHAR(10) NOT NULL CHECK (device_type IN ('ios', 'android')),
    push_token VARCHAR(500) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for DeviceRegistration
CREATE INDEX IF NOT EXISTS idx_device_user ON dating_deviceregistration(user_id);
CREATE INDEX IF NOT EXISTS idx_device_active ON dating_deviceregistration(is_active);

-- =====================================================
-- SECTION 8: Create LocationHistory Table (if not exists)
-- =====================================================

CREATE TABLE IF NOT EXISTS dating_locationhistory (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    latitude DECIMAL(10,8) NOT NULL,
    longitude DECIMAL(11,8) NOT NULL,
    accuracy DOUBLE PRECISION NULL,
    address TEXT NULL,
    city VARCHAR(100) NULL,
    state VARCHAR(100) NULL,
    country VARCHAR(100) NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(20) DEFAULT 'gps' CHECK (source IN ('gps', 'network', 'manual', 'ip'))
);

-- Create indexes for LocationHistory
CREATE INDEX IF NOT EXISTS idx_location_user ON dating_locationhistory(user_id);
CREATE INDEX IF NOT EXISTS idx_location_timestamp ON dating_locationhistory(timestamp);

-- =====================================================
-- SECTION 9: Create UserMatch Table (if not exists)
-- =====================================================

CREATE TABLE IF NOT EXISTS dating_usermatch (
    id SERIAL PRIMARY KEY,
    user1_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    user2_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    distance DOUBLE PRECISION NOT NULL,
    match_score DOUBLE PRECISION DEFAULT 0.0,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'liked', 'disliked', 'matched', 'blocked')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user1_id, user2_id)
);

-- Create indexes for UserMatch
CREATE INDEX IF NOT EXISTS idx_match_user1 ON dating_usermatch(user1_id);
CREATE INDEX IF NOT EXISTS idx_match_user2 ON dating_usermatch(user2_id);
CREATE INDEX IF NOT EXISTS idx_match_status ON dating_usermatch(status);

-- =====================================================
-- SECTION 10: Create LocationPermission Table (if not exists)
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
-- SECTION 11: Verify All Tables Exist
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
