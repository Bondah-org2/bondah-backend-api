-- =============================================================================
-- SOCIAL FEED AND STORY TABLES FOR PGADMIN (NEW)
-- =============================================================================
-- This script creates all the social feed and story related tables
-- for the Bondah Dating App backend
-- Run this in pgAdmin to manually create the tables if migrations fail

-- =============================================================================
-- POST TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS dating_post (
    id SERIAL PRIMARY KEY,
    author_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    post_type VARCHAR(20) NOT NULL DEFAULT 'post' CHECK (post_type IN ('story', 'post', 'announcement')),
    content TEXT NOT NULL,
    image_urls JSONB DEFAULT '[]'::jsonb,
    video_url TEXT,
    video_thumbnail TEXT,
    visibility VARCHAR(20) NOT NULL DEFAULT 'public' CHECK (visibility IN ('public', 'friends', 'private')),
    location VARCHAR(255),
    hashtags JSONB DEFAULT '[]'::jsonb,
    mentions JSONB DEFAULT '[]'::jsonb,
    likes_count INTEGER NOT NULL DEFAULT 0,
    comments_count INTEGER NOT NULL DEFAULT 0,
    shares_count INTEGER NOT NULL DEFAULT 0,
    bonds_count INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_featured BOOLEAN NOT NULL DEFAULT false,
    is_reported BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- POST COMMENT TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS dating_postcomment (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES dating_post(id) ON DELETE CASCADE,
    author_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    parent_comment_id INTEGER REFERENCES dating_postcomment(id) ON DELETE CASCADE,
    likes_count INTEGER NOT NULL DEFAULT 0,
    replies_count INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_edited BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- POST INTERACTION TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS dating_postinteraction (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    post_id INTEGER NOT NULL REFERENCES dating_post(id) ON DELETE CASCADE,
    interaction_type VARCHAR(20) NOT NULL CHECK (interaction_type IN ('like', 'share', 'bond', 'save')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, post_id, interaction_type)
);

-- =============================================================================
-- COMMENT INTERACTION TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS dating_commentinteraction (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    comment_id INTEGER NOT NULL REFERENCES dating_postcomment(id) ON DELETE CASCADE,
    interaction_type VARCHAR(20) NOT NULL DEFAULT 'like' CHECK (interaction_type IN ('like')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, comment_id)
);

-- =============================================================================
-- POST REPORT TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS dating_postreport (
    id SERIAL PRIMARY KEY,
    reporter_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    reported_user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    post_id INTEGER REFERENCES dating_post(id) ON DELETE CASCADE,
    comment_id INTEGER REFERENCES dating_postcomment(id) ON DELETE CASCADE,
    report_type VARCHAR(30) NOT NULL CHECK (report_type IN ('spam', 'inappropriate', 'harassment', 'misinformation', 'fake', 'other')),
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'resolved', 'dismissed')),
    moderator_notes TEXT,
    action_taken VARCHAR(100),
    resolved_by_id INTEGER REFERENCES dating_user(id) ON DELETE SET NULL,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- STORY TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS dating_story (
    id SERIAL PRIMARY KEY,
    author_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    story_type VARCHAR(20) NOT NULL DEFAULT 'image' CHECK (story_type IN ('image', 'video', 'text')),
    content TEXT,
    image_url TEXT,
    video_url TEXT,
    video_duration INTEGER,
    background_color VARCHAR(7),
    text_color VARCHAR(7),
    font_size INTEGER NOT NULL DEFAULT 16,
    views_count INTEGER NOT NULL DEFAULT 0,
    reactions_count INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- STORY VIEW TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS dating_storyview (
    id SERIAL PRIMARY KEY,
    story_id INTEGER NOT NULL REFERENCES dating_story(id) ON DELETE CASCADE,
    viewer_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    viewed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(story_id, viewer_id)
);

-- =============================================================================
-- STORY REACTION TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS dating_storyreaction (
    id SERIAL PRIMARY KEY,
    story_id INTEGER NOT NULL REFERENCES dating_story(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    reaction_type VARCHAR(20) NOT NULL DEFAULT 'like' CHECK (reaction_type IN ('like', 'love', 'laugh', 'wow', 'sad', 'angry')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(story_id, user_id)
);

-- =============================================================================
-- POST SHARE TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS dating_postshare (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES dating_post(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('whatsapp', 'facebook', 'twitter', 'instagram', 'threads', 'copy_link')),
    shared_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- FEED SEARCH TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS dating_feedsearch (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES dating_user(id) ON DELETE SET NULL,
    query VARCHAR(255) NOT NULL,
    results_count INTEGER NOT NULL DEFAULT 0,
    filters_applied JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- Post indexes
CREATE INDEX IF NOT EXISTS dating_post_author_id_created_at_idx ON dating_post(author_id, created_at);
CREATE INDEX IF NOT EXISTS dating_post_post_type_is_active_idx ON dating_post(post_type, is_active);
CREATE INDEX IF NOT EXISTS dating_post_visibility_created_at_idx ON dating_post(visibility, created_at);
CREATE INDEX IF NOT EXISTS dating_post_is_featured_created_at_idx ON dating_post(is_featured, created_at);

-- Post comment indexes
CREATE INDEX IF NOT EXISTS dating_postcomment_post_id_created_at_idx ON dating_postcomment(post_id, created_at);
CREATE INDEX IF NOT EXISTS dating_postcomment_author_id_created_at_idx ON dating_postcomment(author_id, created_at);
CREATE INDEX IF NOT EXISTS dating_postcomment_parent_comment_id_created_at_idx ON dating_postcomment(parent_comment_id, created_at);

-- Post interaction indexes
CREATE INDEX IF NOT EXISTS dating_postinteraction_post_id_interaction_type_idx ON dating_postinteraction(post_id, interaction_type);
CREATE INDEX IF NOT EXISTS dating_postinteraction_user_id_interaction_type_idx ON dating_postinteraction(user_id, interaction_type);

-- Post report indexes
CREATE INDEX IF NOT EXISTS dating_postreport_status_report_type_idx ON dating_postreport(status, report_type);
CREATE INDEX IF NOT EXISTS dating_postreport_reported_user_id_status_idx ON dating_postreport(reported_user_id, status);
CREATE INDEX IF NOT EXISTS dating_postreport_post_id_status_idx ON dating_postreport(post_id, status);
CREATE INDEX IF NOT EXISTS dating_postreport_comment_id_status_idx ON dating_postreport(comment_id, status);

-- Story indexes
CREATE INDEX IF NOT EXISTS dating_story_author_id_created_at_idx ON dating_story(author_id, created_at);
CREATE INDEX IF NOT EXISTS dating_story_expires_at_is_active_idx ON dating_story(expires_at, is_active);
CREATE INDEX IF NOT EXISTS dating_story_story_type_is_active_idx ON dating_story(story_type, is_active);

-- Post share indexes
CREATE INDEX IF NOT EXISTS dating_postshare_post_id_platform_idx ON dating_postshare(post_id, platform);
CREATE INDEX IF NOT EXISTS dating_postshare_user_id_shared_at_idx ON dating_postshare(user_id, shared_at);

-- Feed search indexes
CREATE INDEX IF NOT EXISTS dating_feedsearch_query_created_at_idx ON dating_feedsearch(query, created_at);
CREATE INDEX IF NOT EXISTS dating_feedsearch_user_id_created_at_idx ON dating_feedsearch(user_id, created_at);

-- =============================================================================
-- TRIGGERS FOR UPDATED_AT FIELDS
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at fields
DROP TRIGGER IF EXISTS update_dating_post_updated_at ON dating_post;
CREATE TRIGGER update_dating_post_updated_at
    BEFORE UPDATE ON dating_post
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_dating_postcomment_updated_at ON dating_postcomment;
CREATE TRIGGER update_dating_postcomment_updated_at
    BEFORE UPDATE ON dating_postcomment
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================

-- Check if all tables were created successfully
SELECT 
    table_name,
    CASE 
        WHEN table_name IN (
            'dating_post', 'dating_postcomment', 'dating_postinteraction',
            'dating_commentinteraction', 'dating_postreport', 'dating_story',
            'dating_storyview', 'dating_storyreaction', 'dating_postshare',
            'dating_feedsearch'
        ) THEN '✅ CREATED'
        ELSE '❌ MISSING'
    END as status
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name LIKE 'dating_%'
AND table_name IN (
    'dating_post', 'dating_postcomment', 'dating_postinteraction',
    'dating_commentinteraction', 'dating_postreport', 'dating_story',
    'dating_storyview', 'dating_storyreaction', 'dating_postshare',
    'dating_feedsearch'
)
ORDER BY table_name;

-- Check indexes
SELECT 
    indexname,
    tablename,
    CASE 
        WHEN indexname LIKE '%_idx' THEN '✅ INDEX CREATED'
        ELSE '❌ INDEX MISSING'
    END as status
FROM pg_indexes 
WHERE schemaname = 'public' 
AND tablename IN (
    'dating_post', 'dating_postcomment', 'dating_postinteraction',
    'dating_commentinteraction', 'dating_postreport', 'dating_story',
    'dating_storyview', 'dating_storyreaction', 'dating_postshare',
    'dating_feedsearch'
)
ORDER BY tablename, indexname;

-- =============================================================================
-- SUCCESS MESSAGE
-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE '=============================================================================';
    RAISE NOTICE 'SOCIAL FEED AND STORY TABLES CREATED SUCCESSFULLY!';
    RAISE NOTICE '=============================================================================';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '- dating_post (Posts in Bond Story feed)';
    RAISE NOTICE '- dating_postcomment (Comments on posts)';
    RAISE NOTICE '- dating_postinteraction (Post likes, shares, bonds)';
    RAISE NOTICE '- dating_commentinteraction (Comment likes)';
    RAISE NOTICE '- dating_postreport (Post/comment reports)';
    RAISE NOTICE '- dating_story (User stories - 24hr content)';
    RAISE NOTICE '- dating_storyview (Story view tracking)';
    RAISE NOTICE '- dating_storyreaction (Story reactions)';
    RAISE NOTICE '- dating_postshare (Post sharing to external platforms)';
    RAISE NOTICE '- dating_feedsearch (Feed search queries)';
    RAISE NOTICE '=============================================================================';
    RAISE NOTICE 'All indexes and constraints created successfully!';
    RAISE NOTICE 'Ready for Bondah Dating App social feed features!';
    RAISE NOTICE '=============================================================================';
END $$;

