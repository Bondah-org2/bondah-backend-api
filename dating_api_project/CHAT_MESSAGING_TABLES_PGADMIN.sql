-- =============================================================================
-- CHAT AND MESSAGING TABLES FOR PGADMIN (Railway PostgreSQL)
-- =============================================================================
-- This script creates all the chat, messaging, and calling tables
-- Run this in pgAdmin connected to your Railway PostgreSQL database

-- =============================================================================
-- 1. CHAT TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS dating_chat (
    id SERIAL PRIMARY KEY,
    chat_type VARCHAR(20) NOT NULL DEFAULT 'direct',
    created_by_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    chat_name VARCHAR(100),
    chat_theme VARCHAR(20) NOT NULL DEFAULT 'default',
    CONSTRAINT fk_chat_created_by FOREIGN KEY (created_by_id) REFERENCES dating_user(id) ON DELETE SET NULL
);

-- =============================================================================
-- 2. MESSAGE TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS dating_message (
    id SERIAL PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    sender_id INTEGER,
    message_type VARCHAR(20) NOT NULL DEFAULT 'text',
    content TEXT,
    voice_note_url VARCHAR(200),
    voice_note_duration INTEGER,
    image_url VARCHAR(200),
    video_url VARCHAR(200),
    document_url VARCHAR(200),
    document_name VARCHAR(255),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    read_at TIMESTAMP WITH TIME ZONE,
    is_edited BOOLEAN NOT NULL DEFAULT FALSE,
    edited_at TIMESTAMP WITH TIME ZONE,
    reply_to_id INTEGER,
    reactions JSONB NOT NULL DEFAULT '{}',
    CONSTRAINT fk_message_chat FOREIGN KEY (chat_id) REFERENCES dating_chat(id) ON DELETE CASCADE,
    CONSTRAINT fk_message_sender FOREIGN KEY (sender_id) REFERENCES dating_user(id) ON DELETE SET NULL,
    CONSTRAINT fk_message_reply_to FOREIGN KEY (reply_to_id) REFERENCES dating_message(id) ON DELETE SET NULL
);

-- =============================================================================
-- 3. VOICE NOTE TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS dating_voicenote (
    id SERIAL PRIMARY KEY,
    message_id INTEGER NOT NULL UNIQUE,
    audio_url VARCHAR(200) NOT NULL,
    duration INTEGER NOT NULL,
    file_size INTEGER NOT NULL,
    transcription TEXT,
    transcription_confidence DOUBLE PRECISION,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_voicenote_message FOREIGN KEY (message_id) REFERENCES dating_message(id) ON DELETE CASCADE
);

-- =============================================================================
-- 4. CALL TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS dating_call (
    id SERIAL PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    caller_id INTEGER NOT NULL,
    callee_id INTEGER NOT NULL,
    call_type VARCHAR(10) NOT NULL DEFAULT 'voice',
    status VARCHAR(20) NOT NULL DEFAULT 'initiated',
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    answered_at TIMESTAMP WITH TIME ZONE,
    ended_at TIMESTAMP WITH TIME ZONE,
    duration INTEGER,
    call_id VARCHAR(100) NOT NULL UNIQUE,
    room_id VARCHAR(100),
    quality_score DOUBLE PRECISION,
    is_recorded BOOLEAN NOT NULL DEFAULT FALSE,
    recording_url VARCHAR(200),
    CONSTRAINT fk_call_chat FOREIGN KEY (chat_id) REFERENCES dating_chat(id) ON DELETE CASCADE,
    CONSTRAINT fk_call_caller FOREIGN KEY (caller_id) REFERENCES dating_user(id) ON DELETE CASCADE,
    CONSTRAINT fk_call_callee FOREIGN KEY (callee_id) REFERENCES dating_user(id) ON DELETE CASCADE
);

-- =============================================================================
-- 5. CHAT PARTICIPANT TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS dating_chatparticipant (
    id SERIAL PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    joined_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    left_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    mute_until TIMESTAMP WITH TIME ZONE,
    custom_nickname VARCHAR(50),
    last_seen_at TIMESTAMP WITH TIME ZONE,
    last_read_message_id INTEGER,
    CONSTRAINT fk_chatparticipant_chat FOREIGN KEY (chat_id) REFERENCES dating_chat(id) ON DELETE CASCADE,
    CONSTRAINT fk_chatparticipant_user FOREIGN KEY (user_id) REFERENCES dating_user(id) ON DELETE CASCADE,
    CONSTRAINT fk_chatparticipant_last_read FOREIGN KEY (last_read_message_id) REFERENCES dating_message(id) ON DELETE SET NULL,
    CONSTRAINT unique_chat_user UNIQUE (chat_id, user_id)
);

-- =============================================================================
-- 6. CHAT REPORT TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS dating_chatreport (
    id SERIAL PRIMARY KEY,
    reporter_id INTEGER NOT NULL,
    reported_user_id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL,
    message_id INTEGER,
    report_type VARCHAR(30) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    moderator_notes TEXT,
    action_taken VARCHAR(100),
    resolved_by_id INTEGER,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_chatreport_reporter FOREIGN KEY (reporter_id) REFERENCES dating_user(id) ON DELETE CASCADE,
    CONSTRAINT fk_chatreport_reported_user FOREIGN KEY (reported_user_id) REFERENCES dating_user(id) ON DELETE CASCADE,
    CONSTRAINT fk_chatreport_chat FOREIGN KEY (chat_id) REFERENCES dating_chat(id) ON DELETE CASCADE,
    CONSTRAINT fk_chatreport_message FOREIGN KEY (message_id) REFERENCES dating_message(id) ON DELETE SET NULL,
    CONSTRAINT fk_chatreport_resolved_by FOREIGN KEY (resolved_by_id) REFERENCES dating_user(id) ON DELETE SET NULL
);

-- =============================================================================
-- 7. CREATE INDEXES FOR PERFORMANCE
-- =============================================================================

-- Chat indexes
CREATE INDEX IF NOT EXISTS idx_chat_type_active ON dating_chat(chat_type, is_active);
CREATE INDEX IF NOT EXISTS idx_chat_last_message ON dating_chat(last_message_at);

-- Message indexes
CREATE INDEX IF NOT EXISTS idx_message_chat_timestamp ON dating_message(chat_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_message_sender_timestamp ON dating_message(sender_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_message_type ON dating_message(message_type);

-- Call indexes
CREATE INDEX IF NOT EXISTS idx_call_caller_status ON dating_call(caller_id, status);
CREATE INDEX IF NOT EXISTS idx_call_callee_status ON dating_call(callee_id, status);
CREATE INDEX IF NOT EXISTS idx_call_id ON dating_call(call_id);

-- Chat participant indexes
CREATE INDEX IF NOT EXISTS idx_chatparticipant_user ON dating_chatparticipant(user_id);
CREATE INDEX IF NOT EXISTS idx_chatparticipant_chat ON dating_chatparticipant(chat_id);

-- Chat report indexes
CREATE INDEX IF NOT EXISTS idx_chatreport_status_type ON dating_chatreport(status, report_type);
CREATE INDEX IF NOT EXISTS idx_chatreport_reported_user_status ON dating_chatreport(reported_user_id, status);

-- =============================================================================
-- 8. ADD CONSTRAINTS
-- =============================================================================

-- Add check constraints for enum-like fields
DO $$ 
BEGIN
    -- Chat type constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_chat_type') THEN
        ALTER TABLE dating_chat ADD CONSTRAINT check_chat_type 
        CHECK (chat_type IN ('direct', 'matchmaker_intro', 'group'));
    END IF;
    
    -- Message type constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_message_type') THEN
        ALTER TABLE dating_message ADD CONSTRAINT check_message_type 
        CHECK (message_type IN ('text', 'voice_note', 'image', 'video', 'document', 'system', 'matchmaker_intro', 'call_start', 'call_end'));
    END IF;
    
    -- Call type constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_call_type') THEN
        ALTER TABLE dating_call ADD CONSTRAINT check_call_type 
        CHECK (call_type IN ('voice', 'video'));
    END IF;
    
    -- Call status constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_call_status') THEN
        ALTER TABLE dating_call ADD CONSTRAINT check_call_status 
        CHECK (status IN ('initiated', 'ringing', 'active', 'ended', 'missed', 'declined', 'busy'));
    END IF;
    
    -- Report type constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_report_type') THEN
        ALTER TABLE dating_chatreport ADD CONSTRAINT check_report_type 
        CHECK (report_type IN ('spam', 'harassment', 'inappropriate_content', 'fake_profile', 'other'));
    END IF;
    
    -- Report status constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_report_status') THEN
        ALTER TABLE dating_chatreport ADD CONSTRAINT check_report_status 
        CHECK (status IN ('pending', 'reviewed', 'resolved', 'dismissed'));
    END IF;
    
    -- Chat theme constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_chat_theme') THEN
        ALTER TABLE dating_chat ADD CONSTRAINT check_chat_theme 
        CHECK (chat_theme IN ('default', 'dark', 'light', 'colorful'));
    END IF;
END $$;

-- =============================================================================
-- 9. CREATE TRIGGERS FOR UPDATED_AT
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for chat table
DROP TRIGGER IF EXISTS update_chat_updated_at ON dating_chat;
CREATE TRIGGER update_chat_updated_at
    BEFORE UPDATE ON dating_chat
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- 10. VERIFICATION QUERIES
-- =============================================================================

-- Check if all tables were created successfully
SELECT 
    table_name,
    CASE 
        WHEN table_name IN (
            'dating_chat', 'dating_message', 'dating_voicenote', 
            'dating_call', 'dating_chatparticipant', 'dating_chatreport'
        ) THEN '✅ Created'
        ELSE '❌ Missing'
    END as status
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name LIKE 'dating_%'
ORDER BY table_name;

-- Check indexes
SELECT 
    indexname,
    tablename,
    indexdef
FROM pg_indexes 
WHERE tablename IN (
    'dating_chat', 'dating_message', 'dating_voicenote', 
    'dating_call', 'dating_chatparticipant', 'dating_chatreport'
)
ORDER BY tablename, indexname;

-- Check constraints
SELECT 
    tc.table_name,
    tc.constraint_name,
    tc.constraint_type,
    cc.check_clause
FROM information_schema.table_constraints tc
LEFT JOIN information_schema.check_constraints cc 
    ON tc.constraint_name = cc.constraint_name
WHERE tc.table_name IN (
    'dating_chat', 'dating_message', 'dating_voicenote', 
    'dating_call', 'dating_chatparticipant', 'dating_chatreport'
)
ORDER BY tc.table_name, tc.constraint_type;

-- =============================================================================
-- SUCCESS MESSAGE
-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE '🎉 Chat and Messaging tables created successfully!';
    RAISE NOTICE '✅ All 6 tables created: Chat, Message, VoiceNote, Call, ChatParticipant, ChatReport';
    RAISE NOTICE '✅ All indexes created for optimal performance';
    RAISE NOTICE '✅ All constraints added for data integrity';
    RAISE NOTICE '✅ Triggers created for automatic timestamp updates';
    RAISE NOTICE '🚀 Your Bondah Dating App chat system is ready!';
END $$;
