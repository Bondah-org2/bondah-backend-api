-- =====================================================
-- RAILWAY DATABASE FIX - Run in pgAdmin
-- =====================================================
-- This script fixes all missing columns and tables
-- Run each section one by one in pgAdmin

-- =====================================================
-- SECTION 1: Add Missing Columns to dating_user Table
-- =====================================================

-- Add latitude column
ALTER TABLE dating_user 
ADD COLUMN IF NOT EXISTS latitude DECIMAL(10,8) NULL;

-- Add longitude column  
ALTER TABLE dating_user 
ADD COLUMN IF NOT EXISTS longitude DECIMAL(11,8) NULL;

-- Add address column
ALTER TABLE dating_user 
ADD COLUMN IF NOT EXISTS address TEXT NULL;

-- Add city column
ALTER TABLE dating_user 
ADD COLUMN IF NOT EXISTS city VARCHAR(100) NULL;

-- Add state column
ALTER TABLE dating_user 
ADD COLUMN IF NOT EXISTS state VARCHAR(100) NULL;

-- Add country column
ALTER TABLE dating_user 
ADD COLUMN IF NOT EXISTS country VARCHAR(100) NULL;

-- Add postal_code column
ALTER TABLE dating_user 
ADD COLUMN IF NOT EXISTS postal_code VARCHAR(20) NULL;

-- Add location_privacy column
ALTER TABLE dating_user 
ADD COLUMN IF NOT EXISTS location_privacy VARCHAR(20) DEFAULT 'public';

-- Add location_sharing_enabled column
ALTER TABLE dating_user 
ADD COLUMN IF NOT EXISTS location_sharing_enabled BOOLEAN DEFAULT TRUE;

-- Add location_update_frequency column
ALTER TABLE dating_user 
ADD COLUMN IF NOT EXISTS location_update_frequency VARCHAR(20) DEFAULT 'manual';

-- Add is_matchmaker column
ALTER TABLE dating_user 
ADD COLUMN IF NOT EXISTS is_matchmaker BOOLEAN DEFAULT FALSE;

-- Add bio column
ALTER TABLE dating_user 
ADD COLUMN IF NOT EXISTS bio TEXT DEFAULT '';

-- Add last_location_update column
ALTER TABLE dating_user 
ADD COLUMN IF NOT EXISTS last_location_update TIMESTAMP NULL;

-- Add max_distance column
ALTER TABLE dating_user 
ADD COLUMN IF NOT EXISTS max_distance INTEGER DEFAULT 50;

-- Add age_range_min column
ALTER TABLE dating_user 
ADD COLUMN IF NOT EXISTS age_range_min INTEGER DEFAULT 18;

-- Add age_range_max column
ALTER TABLE dating_user 
ADD COLUMN IF NOT EXISTS age_range_max INTEGER DEFAULT 100;

-- Add preferred_gender column
ALTER TABLE dating_user 
ADD COLUMN IF NOT EXISTS preferred_gender VARCHAR(10) NULL;

-- =====================================================
-- SECTION 2: Create django_site Table
-- =====================================================

-- Create django_site table if it doesn't exist
CREATE TABLE IF NOT EXISTS django_site (
    id SERIAL PRIMARY KEY,
    domain VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(50) NOT NULL
);

-- Insert default site if it doesn't exist
INSERT INTO django_site (domain, name) 
VALUES ('bondah.org', 'Bondah Dating')
ON CONFLICT (domain) DO NOTHING;

-- =====================================================
-- SECTION 3: Create Liveness Verification Tables
-- =====================================================

-- Create LivenessVerification table
CREATE TABLE IF NOT EXISTS dating_livenessverification (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
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

-- Create UserVerificationStatus table
CREATE TABLE IF NOT EXISTS dating_userverificationstatus (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES dating_user(id) ON DELETE CASCADE,
    email_verified BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE,
    liveness_verified BOOLEAN DEFAULT FALSE,
    identity_verified BOOLEAN DEFAULT FALSE,
    verification_level VARCHAR(20) DEFAULT 'none',
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
-- SECTION 4: Create OAuth and Social Tables
-- =====================================================

-- Create SocialAccount table
CREATE TABLE IF NOT EXISTS dating_socialaccount (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    provider_id VARCHAR(100) NOT NULL,
    provider_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider, provider_id)
);

-- Create DeviceRegistration table
CREATE TABLE IF NOT EXISTS dating_deviceregistration (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    device_id VARCHAR(255) NOT NULL,
    device_type VARCHAR(20) NOT NULL,
    device_token TEXT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create LocationHistory table
CREATE TABLE IF NOT EXISTS dating_locationhistory (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    latitude DECIMAL(10,8) NOT NULL,
    longitude DECIMAL(11,8) NOT NULL,
    address TEXT NULL,
    city VARCHAR(100) NULL,
    state VARCHAR(100) NULL,
    country VARCHAR(100) NULL,
    accuracy DOUBLE PRECISION NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create UserMatch table
CREATE TABLE IF NOT EXISTS dating_usermatch (
    id SERIAL PRIMARY KEY,
    user1_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    user2_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    match_type VARCHAR(20) DEFAULT 'mutual',
    is_mutual BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user1_id, user2_id)
);

-- Create LocationPermission table
CREATE TABLE IF NOT EXISTS dating_locationpermission (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    permission_type VARCHAR(50) NOT NULL,
    is_granted BOOLEAN DEFAULT FALSE,
    granted_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- SECTION 5: Create Indexes for Performance
-- =====================================================

-- Indexes for SocialAccount
CREATE INDEX IF NOT EXISTS idx_social_user ON dating_socialaccount(user_id);
CREATE INDEX IF NOT EXISTS idx_social_provider ON dating_socialaccount(provider);

-- Indexes for DeviceRegistration
CREATE INDEX IF NOT EXISTS idx_device_user ON dating_deviceregistration(user_id);
CREATE INDEX IF NOT EXISTS idx_device_active ON dating_deviceregistration(is_active);

-- Indexes for LocationHistory
CREATE INDEX IF NOT EXISTS idx_location_user ON dating_locationhistory(user_id);
CREATE INDEX IF NOT EXISTS idx_location_created ON dating_locationhistory(created_at);

-- Indexes for UserMatch
CREATE INDEX IF NOT EXISTS idx_match_user1 ON dating_usermatch(user1_id);
CREATE INDEX IF NOT EXISTS idx_match_user2 ON dating_usermatch(user2_id);
CREATE INDEX IF NOT EXISTS idx_match_mutual ON dating_usermatch(is_mutual);

-- Indexes for LocationPermission
CREATE INDEX IF NOT EXISTS idx_permission_user ON dating_locationpermission(user_id);
CREATE INDEX IF NOT EXISTS idx_permission_type ON dating_locationpermission(permission_type);

-- =====================================================
-- SECTION 6: Verify Tables Exist
-- =====================================================

-- Check if all tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
    'dating_user',
    'django_site',
    'dating_livenessverification',
    'dating_userverificationstatus',
    'dating_socialaccount',
    'dating_deviceregistration',
    'dating_locationhistory',
    'dating_usermatch',
    'dating_locationpermission'
)
ORDER BY table_name;

-- Check if all columns exist in dating_user
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'dating_user' 
AND column_name IN (
    'latitude', 'longitude', 'address', 'city', 'state', 'country',
    'postal_code', 'location_privacy', 'location_sharing_enabled',
    'location_update_frequency', 'is_matchmaker', 'bio',
    'last_location_update', 'max_distance', 'age_range_min',
    'age_range_max', 'preferred_gender'
)
ORDER BY column_name;

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================
-- If you see all tables and columns listed above,
-- then the database fix was successful!
-- Your Railway deployment should now work without 500 errors.
