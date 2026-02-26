-- =============================================================================
-- NEW FIGMA FEATURES TABLES FOR PGADMIN
-- =============================================================================
-- This script creates the new tables for Social Media Handles, Security Questions,
-- and Document Verification features based on the uploaded Figma designs.
-- Run this script in pgAdmin to manually apply the database changes to Railway PostgreSQL.

-- =============================================================================
-- SOCIAL MEDIA HANDLES TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS dating_usersocialhandle (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    platform VARCHAR(50) NOT NULL,
    handle VARCHAR(100) NOT NULL,
    url TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Platform choices
    CONSTRAINT dating_usersocialhandle_platform_check 
        CHECK (platform IN ('instagram', 'twitter', 'facebook', 'linkedin', 'tiktok', 'snapchat', 'youtube', 'pinterest', 'website', 'other'))
);

-- Add foreign key constraint for user
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'dating_usersocialhandle_user_id_fkey'
    ) THEN
        ALTER TABLE dating_usersocialhandle 
        ADD CONSTRAINT dating_usersocialhandle_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES dating_user(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Add unique constraint for user-platform combination
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'dating_usersocialhandle_user_id_platform_key'
    ) THEN
        ALTER TABLE dating_usersocialhandle 
        ADD CONSTRAINT dating_usersocialhandle_user_id_platform_key 
        UNIQUE (user_id, platform);
    END IF;
END $$;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_dating_usersocialhandle_user_platform 
    ON dating_usersocialhandle(user_id, platform);
CREATE INDEX IF NOT EXISTS idx_dating_usersocialhandle_platform 
    ON dating_usersocialhandle(platform);

-- Create trigger for updated_at
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.triggers 
        WHERE trigger_name = 'update_dating_usersocialhandle_updated_at'
    ) THEN
        CREATE TRIGGER update_dating_usersocialhandle_updated_at
            BEFORE UPDATE ON dating_usersocialhandle
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- =============================================================================
-- SECURITY QUESTIONS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS dating_usersecurityquestion (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    question_type VARCHAR(50) NOT NULL,
    response TEXT NOT NULL,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Question type choices
    CONSTRAINT dating_usersecurityquestion_question_type_check 
        CHECK (question_type IN ('data_protection', 'scam_prevention', 'relationship_guidance', 'matchmaking_evolution', 'unique_skills', 'business_service'))
);

-- Add foreign key constraint for user
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'dating_usersecurityquestion_user_id_fkey'
    ) THEN
        ALTER TABLE dating_usersecurityquestion 
        ADD CONSTRAINT dating_usersecurityquestion_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES dating_user(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Add unique constraint for user-question_type combination
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'dating_usersecurityquestion_user_id_question_type_key'
    ) THEN
        ALTER TABLE dating_usersecurityquestion 
        ADD CONSTRAINT dating_usersecurityquestion_user_id_question_type_key 
        UNIQUE (user_id, question_type);
    END IF;
END $$;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_dating_usersecurityquestion_user_question_type 
    ON dating_usersecurityquestion(user_id, question_type);
CREATE INDEX IF NOT EXISTS idx_dating_usersecurityquestion_question_type 
    ON dating_usersecurityquestion(question_type);

-- Create trigger for updated_at
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.triggers 
        WHERE trigger_name = 'update_dating_usersecurityquestion_updated_at'
    ) THEN
        CREATE TRIGGER update_dating_usersecurityquestion_updated_at
            BEFORE UPDATE ON dating_usersecurityquestion
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- =============================================================================
-- DOCUMENT VERIFICATION TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS dating_documentverification (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    document_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    front_image_url TEXT,
    back_image_url TEXT,
    extracted_data JSONB DEFAULT '{}',
    verification_score DOUBLE PRECISION DEFAULT 0.0,
    is_authentic BOOLEAN DEFAULT FALSE,
    rejection_reason TEXT,
    verification_service VARCHAR(50) DEFAULT 'internal',
    service_response JSONB DEFAULT '{}',
    uploaded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    verified_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Document type choices
    CONSTRAINT dating_documentverification_document_type_check 
        CHECK (document_type IN ('passport', 'national_id', 'drivers_license')),
    
    -- Status choices
    CONSTRAINT dating_documentverification_status_check 
        CHECK (status IN ('pending', 'processing', 'approved', 'rejected', 'failed'))
);

-- Add foreign key constraint for user
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'dating_documentverification_user_id_fkey'
    ) THEN
        ALTER TABLE dating_documentverification 
        ADD CONSTRAINT dating_documentverification_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES dating_user(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_dating_documentverification_user_status 
    ON dating_documentverification(user_id, status);
CREATE INDEX IF NOT EXISTS idx_dating_documentverification_status_uploaded_at 
    ON dating_documentverification(status, uploaded_at);
CREATE INDEX IF NOT EXISTS idx_dating_documentverification_document_type 
    ON dating_documentverification(document_type);

-- Create trigger for updated_at
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.triggers 
        WHERE trigger_name = 'update_dating_documentverification_updated_at'
    ) THEN
        CREATE TRIGGER update_dating_documentverification_updated_at
            BEFORE UPDATE ON dating_documentverification
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- =============================================================================
-- SUCCESS MESSAGE
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '=============================================================================';
    RAISE NOTICE 'NEW FIGMA FEATURES TABLES CREATED SUCCESSFULLY!';
    RAISE NOTICE '=============================================================================';
    RAISE NOTICE 'New tables created:';
    RAISE NOTICE '- dating_usersocialhandle (Social media handles for user profiles)';
    RAISE NOTICE '- dating_usersecurityquestion (Security and data responsibility questions)';
    RAISE NOTICE '- dating_documentverification (Document verification for identity)';
    RAISE NOTICE '';
    RAISE NOTICE 'Features implemented:';
    RAISE NOTICE '- Social Media Handles: Instagram, Twitter, Facebook, LinkedIn, TikTok, etc.';
    RAISE NOTICE '- Security Questions: Data protection, scam prevention, relationship guidance';
    RAISE NOTICE '- Document Verification: Passport, National ID, Driver''s License scanning';
    RAISE NOTICE '- Username Validation: Format checking and availability suggestions';
    RAISE NOTICE '';
    RAISE NOTICE 'All indexes, constraints, and triggers created successfully!';
    RAISE NOTICE 'Ready for Bondah Dating App new Figma features!';
    RAISE NOTICE '=============================================================================';
END $$;
