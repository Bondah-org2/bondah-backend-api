-- =====================================================
-- ADVANCED PROFILE TABLES - Run in pgAdmin
-- =====================================================
-- This script creates the new advanced profile tables for mobile app
-- Run this in pgAdmin after the previous database fixes

-- =====================================================
-- SECTION 1: Add New Columns to Existing User Table
-- =====================================================

-- Add profile picture fields
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS profile_picture VARCHAR(200);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS profile_gallery JSONB DEFAULT '[]';

-- Add personal information fields
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS education_level VARCHAR(50);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS height VARCHAR(10);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS zodiac_sign VARCHAR(20);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS languages JSONB DEFAULT '[]';
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS relationship_status VARCHAR(20);

-- Add lifestyle & preferences fields
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS smoking_preference VARCHAR(20);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS drinking_preference VARCHAR(20);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS pet_preference VARCHAR(20);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS exercise_frequency VARCHAR(20);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS kids_preference VARCHAR(20);

-- Add personality & communication fields
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS personality_type VARCHAR(10);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS love_language VARCHAR(20);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS communication_style VARCHAR(20);

-- Add interests & hobbies fields
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS hobbies JSONB DEFAULT '[]';
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS interests JSONB DEFAULT '[]';

-- Add future plans & values fields
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS marriage_plans VARCHAR(20);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS kids_plans VARCHAR(20);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS religion_importance VARCHAR(20);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS religion VARCHAR(50);

-- Add dating preferences fields
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS dating_type VARCHAR(20);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS open_to_long_distance VARCHAR(20);

-- =====================================================
-- SECTION 2: Create UserInterest Table
-- =====================================================

CREATE TABLE IF NOT EXISTS dating_userinterest (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50) NOT NULL CHECK (category IN (
        'sports', 'music', 'travel', 'food', 'art', 'technology', 
        'fitness', 'reading', 'movies', 'gaming', 'outdoor', 'other'
    )),
    icon VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for UserInterest
CREATE INDEX IF NOT EXISTS idx_userinterest_category ON dating_userinterest(category);
CREATE INDEX IF NOT EXISTS idx_userinterest_active ON dating_userinterest(is_active);
CREATE INDEX IF NOT EXISTS idx_userinterest_name ON dating_userinterest(name);

-- =====================================================
-- SECTION 3: Create UserProfileView Table
-- =====================================================

CREATE TABLE IF NOT EXISTS dating_userprofileview (
    id SERIAL PRIMARY KEY,
    viewer_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    viewed_user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    source VARCHAR(20) NOT NULL CHECK (source IN (
        'search', 'discover', 'nearby', 'recommended', 'direct'
    )),
    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(viewer_id, viewed_user_id)
);

-- Create indexes for UserProfileView
CREATE INDEX IF NOT EXISTS idx_profileview_viewer ON dating_userprofileview(viewer_id);
CREATE INDEX IF NOT EXISTS idx_profileview_viewed ON dating_userprofileview(viewed_user_id);
CREATE INDEX IF NOT EXISTS idx_profileview_source ON dating_userprofileview(source);
CREATE INDEX IF NOT EXISTS idx_profileview_viewed_at ON dating_userprofileview(viewed_at);

-- =====================================================
-- SECTION 4: Create UserInteraction Table
-- =====================================================

CREATE TABLE IF NOT EXISTS dating_userinteraction (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    target_user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    interaction_type VARCHAR(20) NOT NULL CHECK (interaction_type IN (
        'like', 'dislike', 'super_like', 'pass', 'block', 'report', 
        'request_live', 'share_profile'
    )),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    UNIQUE(user_id, target_user_id, interaction_type)
);

-- Create indexes for UserInteraction
CREATE INDEX IF NOT EXISTS idx_interaction_user ON dating_userinteraction(user_id);
CREATE INDEX IF NOT EXISTS idx_interaction_target ON dating_userinteraction(target_user_id);
CREATE INDEX IF NOT EXISTS idx_interaction_type ON dating_userinteraction(interaction_type);
CREATE INDEX IF NOT EXISTS idx_interaction_created ON dating_userinteraction(created_at);

-- =====================================================
-- SECTION 5: Create SearchQuery Table
-- =====================================================

CREATE TABLE IF NOT EXISTS dating_searchquery (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    query VARCHAR(255) NOT NULL,
    filters JSONB DEFAULT '{}',
    results_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for SearchQuery
CREATE INDEX IF NOT EXISTS idx_searchquery_user ON dating_searchquery(user_id);
CREATE INDEX IF NOT EXISTS idx_searchquery_created ON dating_searchquery(created_at);
CREATE INDEX IF NOT EXISTS idx_searchquery_query ON dating_searchquery(query);

-- =====================================================
-- SECTION 6: Create RecommendationEngine Table
-- =====================================================

CREATE TABLE IF NOT EXISTS dating_recommendationengine (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    recommended_user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    score DOUBLE PRECISION NOT NULL CHECK (score >= 0 AND score <= 100),
    algorithm VARCHAR(50) NOT NULL CHECK (algorithm IN (
        'location_based', 'interest_based', 'compatibility', 'hybrid'
    )),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(user_id, recommended_user_id)
);

-- Create indexes for RecommendationEngine
CREATE INDEX IF NOT EXISTS idx_recommendation_user ON dating_recommendationengine(user_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_recommended ON dating_recommendationengine(recommended_user_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_score ON dating_recommendationengine(score);
CREATE INDEX IF NOT EXISTS idx_recommendation_algorithm ON dating_recommendationengine(algorithm);
CREATE INDEX IF NOT EXISTS idx_recommendation_active ON dating_recommendationengine(is_active);

-- =====================================================
-- SECTION 7: Add Constraints to User Table
-- =====================================================

-- Add check constraints for choice fields (with error handling)
DO $$
BEGIN
    -- Education level constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_education_level') THEN
        ALTER TABLE dating_user ADD CONSTRAINT check_education_level 
            CHECK (education_level IS NULL OR education_level IN (
                'high_school', 'undergrad', 'bachelors', 'masters', 'phd', 'other'
            ));
    END IF;

    -- Zodiac sign constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_zodiac_sign') THEN
        ALTER TABLE dating_user ADD CONSTRAINT check_zodiac_sign 
            CHECK (zodiac_sign IS NULL OR zodiac_sign IN (
                'aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 
                'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces'
            ));
    END IF;

    -- Relationship status constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_relationship_status') THEN
        ALTER TABLE dating_user ADD CONSTRAINT check_relationship_status 
            CHECK (relationship_status IS NULL OR relationship_status IN (
                'single', 'divorced', 'widowed', 'separated'
            ));
    END IF;

    -- Smoking preference constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_smoking_preference') THEN
        ALTER TABLE dating_user ADD CONSTRAINT check_smoking_preference 
            CHECK (smoking_preference IS NULL OR smoking_preference IN (
                'never', 'occasionally', 'regularly', 'quit'
            ));
    END IF;

    -- Drinking preference constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_drinking_preference') THEN
        ALTER TABLE dating_user ADD CONSTRAINT check_drinking_preference 
            CHECK (drinking_preference IS NULL OR drinking_preference IN (
                'never', 'occasionally', 'regularly', 'quit'
            ));
    END IF;

    -- Pet preference constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_pet_preference') THEN
        ALTER TABLE dating_user ADD CONSTRAINT check_pet_preference 
            CHECK (pet_preference IS NULL OR pet_preference IN (
                'dog', 'cat', 'both', 'none', 'other'
            ));
    END IF;

    -- Exercise frequency constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_exercise_frequency') THEN
        ALTER TABLE dating_user ADD CONSTRAINT check_exercise_frequency 
            CHECK (exercise_frequency IS NULL OR exercise_frequency IN (
                'never', '1x_week', '2x_week', '3x_week', '4x_week', '5x_week', 'daily'
            ));
    END IF;

    -- Kids preference constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_kids_preference') THEN
        ALTER TABLE dating_user ADD CONSTRAINT check_kids_preference 
            CHECK (kids_preference IS NULL OR kids_preference IN (
                'want', 'dont_want', 'have_kids', 'open'
            ));
    END IF;

    -- Personality type constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_personality_type') THEN
        ALTER TABLE dating_user ADD CONSTRAINT check_personality_type 
            CHECK (personality_type IS NULL OR personality_type IN (
                'INTJ', 'INTP', 'ENTJ', 'ENTP', 'INFJ', 'INFP', 'ENFJ', 'ENFP',
                'ISTJ', 'ISFJ', 'ESTJ', 'ESFJ', 'ISTP', 'ISFP', 'ESTP', 'ESFP'
            ));
    END IF;

    -- Love language constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_love_language') THEN
        ALTER TABLE dating_user ADD CONSTRAINT check_love_language 
            CHECK (love_language IS NULL OR love_language IN (
                'physical_touch', 'gifts', 'quality_time', 'words_of_affirmation', 'acts_of_service'
            ));
    END IF;

    -- Communication style constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_communication_style') THEN
        ALTER TABLE dating_user ADD CONSTRAINT check_communication_style 
            CHECK (communication_style IS NULL OR communication_style IN (
                'direct', 'romantic', 'playful', 'reserved'
            ));
    END IF;

    -- Marriage plans constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_marriage_plans') THEN
        ALTER TABLE dating_user ADD CONSTRAINT check_marriage_plans 
            CHECK (marriage_plans IS NULL OR marriage_plans IN ('yes', 'no', 'maybe'));
    END IF;

    -- Kids plans constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_kids_plans') THEN
        ALTER TABLE dating_user ADD CONSTRAINT check_kids_plans 
            CHECK (kids_plans IS NULL OR kids_plans IN ('yes', 'no', 'maybe'));
    END IF;

    -- Religion importance constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_religion_importance') THEN
        ALTER TABLE dating_user ADD CONSTRAINT check_religion_importance 
            CHECK (religion_importance IS NULL OR religion_importance IN (
                'very', 'somewhat', 'not_important'
            ));
    END IF;

    -- Dating type constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_dating_type') THEN
        ALTER TABLE dating_user ADD CONSTRAINT check_dating_type 
            CHECK (dating_type IS NULL OR dating_type IN (
                'casual', 'serious', 'marriage', 'sugar', 'friends'
            ));
    END IF;

    -- Open to long distance constraint
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_open_to_long_distance') THEN
        ALTER TABLE dating_user ADD CONSTRAINT check_open_to_long_distance 
            CHECK (open_to_long_distance IS NULL OR open_to_long_distance IN ('yes', 'no', 'maybe'));
    END IF;

END $$;

-- =====================================================
-- SECTION 8: Insert Sample Interests
-- =====================================================

INSERT INTO dating_userinterest (name, category, icon, is_active) VALUES
-- Sports
('Football', 'sports', '⚽', true),
('Basketball', 'sports', '🏀', true),
('Tennis', 'sports', '🎾', true),
('Swimming', 'sports', '🏊', true),
('Running', 'sports', '🏃', true),
('Gym', 'fitness', '💪', true),
('Yoga', 'fitness', '🧘', true),
('Hiking', 'outdoor', '🥾', true),
('Cycling', 'sports', '🚴', true),

-- Music
('Pop Music', 'music', '🎵', true),
('Rock', 'music', '🎸', true),
('Jazz', 'music', '🎷', true),
('Classical', 'music', '🎼', true),
('Hip Hop', 'music', '🎤', true),
('Electronic', 'music', '🎧', true),

-- Travel
('Adventure Travel', 'travel', '🗺️', true),
('City Breaks', 'travel', '🏙️', true),
('Beach Holidays', 'travel', '🏖️', true),
('Mountain Climbing', 'outdoor', '⛰️', true),
('Road Trips', 'travel', '🚗', true),
('Backpacking', 'travel', '🎒', true),

-- Food
('Cooking', 'food', '👨‍🍳', true),
('Fine Dining', 'food', '🍽️', true),
('Street Food', 'food', '🌮', true),
('Wine Tasting', 'food', '🍷', true),
('Coffee', 'food', '☕', true),
('Baking', 'food', '🧁', true),

-- Art
('Painting', 'art', '🎨', true),
('Photography', 'art', '📸', true),
('Sculpture', 'art', '🗿', true),
('Digital Art', 'art', '💻', true),
('Museums', 'art', '🏛️', true),
('Galleries', 'art', '🖼️', true),

-- Technology
('Programming', 'technology', '💻', true),
('Gaming', 'gaming', '🎮', true),
('AI/ML', 'technology', '🤖', true),
('Cryptocurrency', 'technology', '₿', true),
('Robotics', 'technology', '🤖', true),
('VR/AR', 'technology', '🥽', true),

-- Reading
('Fiction', 'reading', '📚', true),
('Non-fiction', 'reading', '📖', true),
('Poetry', 'reading', '📝', true),
('Biographies', 'reading', '👤', true),
('Self-help', 'reading', '💡', true),
('Science Fiction', 'reading', '🚀', true),

-- Movies
('Action Movies', 'movies', '💥', true),
('Comedy', 'movies', '😂', true),
('Drama', 'movies', '🎭', true),
('Horror', 'movies', '👻', true),
('Documentaries', 'movies', '📽️', true),
('Independent Films', 'movies', '🎬', true),

-- Outdoor Activities
('Camping', 'outdoor', '⛺', true),
('Fishing', 'outdoor', '🎣', true),
('Skiing', 'outdoor', '⛷️', true),
('Surfing', 'outdoor', '🏄', true),
('Rock Climbing', 'outdoor', '🧗', true),
('Gardening', 'outdoor', '🌱', true)

ON CONFLICT (name) DO NOTHING;

-- =====================================================
-- SECTION 9: Verify All Tables Exist
-- =====================================================

-- Check if all advanced profile tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
    'dating_userinterest',
    'dating_userprofileview',
    'dating_userinteraction',
    'dating_searchquery',
    'dating_recommendationengine'
)
ORDER BY table_name;

-- Check if new user columns exist
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'dating_user' 
AND column_name IN (
    'profile_picture', 'profile_gallery', 'education_level', 'height', 
    'zodiac_sign', 'languages', 'relationship_status', 'smoking_preference',
    'drinking_preference', 'pet_preference', 'exercise_frequency', 'kids_preference',
    'personality_type', 'love_language', 'communication_style', 'hobbies',
    'interests', 'marriage_plans', 'kids_plans', 'religion_importance',
    'religion', 'dating_type', 'open_to_long_distance'
)
ORDER BY column_name;

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================
-- If you see all 5 tables listed above and all 23 user columns,
-- then the advanced profile tables were created successfully!
-- Your mobile app backend is now fully operational with all Figma features.
