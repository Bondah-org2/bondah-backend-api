-- =============================================================================
-- PROFILE SETTINGS AND LIVE SESSION TABLES FOR PGADMIN
-- =============================================================================
-- This script adds the new profile fields and live session tables to the 
-- Bondah Dating App database via pgAdmin.
-- Run this script in pgAdmin to update your Railway PostgreSQL database.
-- =============================================================================

-- Add new fields to the existing dating_user table
DO $$ 
BEGIN
    -- Add looking_for field
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'dating_user' AND column_name = 'looking_for') THEN
        ALTER TABLE dating_user ADD COLUMN looking_for TEXT;
        RAISE NOTICE 'Added looking_for column to dating_user table';
    ELSE
        RAISE NOTICE 'looking_for column already exists in dating_user table';
    END IF;

    -- Add push_notifications_enabled field
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'dating_user' AND column_name = 'push_notifications_enabled') THEN
        ALTER TABLE dating_user ADD COLUMN push_notifications_enabled BOOLEAN DEFAULT TRUE;
        RAISE NOTICE 'Added push_notifications_enabled column to dating_user table';
    ELSE
        RAISE NOTICE 'push_notifications_enabled column already exists in dating_user table';
    END IF;

    -- Add email_notifications_enabled field
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'dating_user' AND column_name = 'email_notifications_enabled') THEN
        ALTER TABLE dating_user ADD COLUMN email_notifications_enabled BOOLEAN DEFAULT TRUE;
        RAISE NOTICE 'Added email_notifications_enabled column to dating_user table';
    ELSE
        RAISE NOTICE 'email_notifications_enabled column already exists in dating_user table';
    END IF;

    -- Add preferred_language field
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'dating_user' AND column_name = 'preferred_language') THEN
        ALTER TABLE dating_user ADD COLUMN preferred_language VARCHAR(10) DEFAULT 'en';
        RAISE NOTICE 'Added preferred_language column to dating_user table';
    ELSE
        RAISE NOTICE 'preferred_language column already exists in dating_user table';
    END IF;
END $$;

-- Create LiveSession table
CREATE TABLE IF NOT EXISTS dating_livesession (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR(255),
    description TEXT,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    end_time TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    duration_limit_minutes INTEGER NOT NULL DEFAULT 60,
    viewers_count INTEGER NOT NULL DEFAULT 0,
    likes_count INTEGER NOT NULL DEFAULT 0,
    stream_url VARCHAR(200),
    thumbnail_url VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create LiveParticipant table
CREATE TABLE IF NOT EXISTS dating_liveparticipant (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    joined_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    left_at TIMESTAMP WITH TIME ZONE,
    role VARCHAR(20) NOT NULL DEFAULT 'viewer'
);

-- Add foreign key constraints for LiveSession
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'dating_livesession_user_id_fkey') THEN
        ALTER TABLE dating_livesession 
        ADD CONSTRAINT dating_livesession_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES dating_user(id) ON DELETE CASCADE;
        RAISE NOTICE 'Added foreign key constraint for dating_livesession.user_id';
    ELSE
        RAISE NOTICE 'Foreign key constraint for dating_livesession.user_id already exists';
    END IF;
END $$;

-- Add foreign key constraints for LiveParticipant
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'dating_liveparticipant_session_id_fkey') THEN
        ALTER TABLE dating_liveparticipant 
        ADD CONSTRAINT dating_liveparticipant_session_id_fkey 
        FOREIGN KEY (session_id) REFERENCES dating_livesession(id) ON DELETE CASCADE;
        RAISE NOTICE 'Added foreign key constraint for dating_liveparticipant.session_id';
    ELSE
        RAISE NOTICE 'Foreign key constraint for dating_liveparticipant.session_id already exists';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'dating_liveparticipant_user_id_fkey') THEN
        ALTER TABLE dating_liveparticipant 
        ADD CONSTRAINT dating_liveparticipant_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES dating_user(id) ON DELETE CASCADE;
        RAISE NOTICE 'Added foreign key constraint for dating_liveparticipant.user_id';
    ELSE
        RAISE NOTICE 'Foreign key constraint for dating_liveparticipant.user_id already exists';
    END IF;
END $$;

-- Add unique constraint for LiveParticipant
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'dating_liveparticipant_session_id_user_id_key') THEN
        ALTER TABLE dating_liveparticipant 
        ADD CONSTRAINT dating_liveparticipant_session_id_user_id_key 
        UNIQUE (session_id, user_id);
        RAISE NOTICE 'Added unique constraint for dating_liveparticipant (session_id, user_id)';
    ELSE
        RAISE NOTICE 'Unique constraint for dating_liveparticipant (session_id, user_id) already exists';
    END IF;
END $$;

-- Create indexes for LiveSession
CREATE INDEX IF NOT EXISTS dating_live_user_id_a1cd68_idx 
ON dating_livesession (user_id, status);

CREATE INDEX IF NOT EXISTS dating_live_status_45205e_idx 
ON dating_livesession (status, start_time);

-- Create indexes for LiveParticipant
CREATE INDEX IF NOT EXISTS dating_live_session_dd8afa_idx 
ON dating_liveparticipant (session_id, user_id);

CREATE INDEX IF NOT EXISTS dating_live_user_id_de63af_idx 
ON dating_liveparticipant (user_id, joined_at);

-- Create trigger function for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at fields
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.triggers 
                   WHERE trigger_name = 'update_dating_livesession_updated_at') THEN
        CREATE TRIGGER update_dating_livesession_updated_at
            BEFORE UPDATE ON dating_livesession
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        RAISE NOTICE 'Created trigger for dating_livesession.updated_at';
    ELSE
        RAISE NOTICE 'Trigger for dating_livesession.updated_at already exists';
    END IF;
END $$;

-- Add check constraints for status fields
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'dating_livesession_status_check') THEN
        ALTER TABLE dating_livesession 
        ADD CONSTRAINT dating_livesession_status_check 
        CHECK (status IN ('active', 'ended', 'scheduled', 'cancelled'));
        RAISE NOTICE 'Added status check constraint for dating_livesession';
    ELSE
        RAISE NOTICE 'Status check constraint for dating_livesession already exists';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'dating_liveparticipant_role_check') THEN
        ALTER TABLE dating_liveparticipant 
        ADD CONSTRAINT dating_liveparticipant_role_check 
        CHECK (role IN ('viewer', 'co_host', 'speaker'));
        RAISE NOTICE 'Added role check constraint for dating_liveparticipant';
    ELSE
        RAISE NOTICE 'Role check constraint for dating_liveparticipant already exists';
    END IF;
END $$;

-- Add comments to tables and columns
COMMENT ON TABLE dating_livesession IS 'Represents an active live session by a user';
COMMENT ON TABLE dating_liveparticipant IS 'Tracks users participating in or viewing a live session';

COMMENT ON COLUMN dating_livesession.user_id IS 'User who created the live session';
COMMENT ON COLUMN dating_livesession.title IS 'Title of the live session';
COMMENT ON COLUMN dating_livesession.description IS 'Description of the live session';
COMMENT ON COLUMN dating_livesession.start_time IS 'When the live session started';
COMMENT ON COLUMN dating_livesession.end_time IS 'When the live session ended';
COMMENT ON COLUMN dating_livesession.status IS 'Session status: active, ended, scheduled, cancelled';
COMMENT ON COLUMN dating_livesession.duration_limit_minutes IS 'Maximum duration in minutes';
COMMENT ON COLUMN dating_livesession.viewers_count IS 'Number of current viewers';
COMMENT ON COLUMN dating_livesession.likes_count IS 'Number of likes/reactions';
COMMENT ON COLUMN dating_livesession.stream_url IS 'URL for the live stream';
COMMENT ON COLUMN dating_livesession.thumbnail_url IS 'Thumbnail URL for the live session';

COMMENT ON COLUMN dating_liveparticipant.session_id IS 'Live session being participated in';
COMMENT ON COLUMN dating_liveparticipant.user_id IS 'User participating in the session';
COMMENT ON COLUMN dating_liveparticipant.joined_at IS 'When the user joined the session';
COMMENT ON COLUMN dating_liveparticipant.left_at IS 'When the user left the session';
COMMENT ON COLUMN dating_liveparticipant.role IS 'Role in session: viewer, co_host, speaker';

COMMENT ON COLUMN dating_user.looking_for IS 'Free text describing what the user is looking for';
COMMENT ON COLUMN dating_user.push_notifications_enabled IS 'Enable push notifications';
COMMENT ON COLUMN dating_user.email_notifications_enabled IS 'Enable email notifications';
COMMENT ON COLUMN dating_user.preferred_language IS 'User''s preferred app language';

-- Final success message
DO $$ 
BEGIN
    RAISE NOTICE '=============================================================================';
    RAISE NOTICE 'PROFILE SETTINGS AND LIVE SESSION TABLES CREATED SUCCESSFULLY!';
    RAISE NOTICE '=============================================================================';
    RAISE NOTICE 'New fields added to dating_user:';
    RAISE NOTICE '- looking_for (TEXT) - Free text for relationship preferences';
    RAISE NOTICE '- push_notifications_enabled (BOOLEAN) - Push notification toggle';
    RAISE NOTICE '- email_notifications_enabled (BOOLEAN) - Email notification toggle';
    RAISE NOTICE '- preferred_language (VARCHAR) - App language preference';
    RAISE NOTICE '';
    RAISE NOTICE 'New tables created:';
    RAISE NOTICE '- dating_livesession (Live streaming sessions)';
    RAISE NOTICE '- dating_liveparticipant (Session participants)';
    RAISE NOTICE '';
    RAISE NOTICE 'All indexes, constraints, and triggers created successfully!';
    RAISE NOTICE 'Ready for Bondah Dating App profile and live session features!';
    RAISE NOTICE '=============================================================================';
END $$;
