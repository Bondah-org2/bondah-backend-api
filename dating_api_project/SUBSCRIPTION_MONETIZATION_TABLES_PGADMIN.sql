-- =============================================================================
-- SUBSCRIPTION AND MONETIZATION TABLES FOR PGADMIN (NEW FROM FIGMA)
-- =============================================================================
-- This script creates all the new tables for subscription plans, Bondcoin wallet,
-- virtual gifting system, and live streaming enhancements based on the Figma designs.
-- Run this script in pgAdmin to update your Railway PostgreSQL database.

-- =============================================================================
-- 1. ADD NEW FIELDS TO EXISTING TABLES
-- =============================================================================

-- Add bondcoin_balance to User table
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'dating_user' AND column_name = 'bondcoin_balance') THEN
        ALTER TABLE dating_user ADD COLUMN bondcoin_balance INTEGER DEFAULT 0 NOT NULL;
        COMMENT ON COLUMN dating_user.bondcoin_balance IS 'User''s Bondcoin balance';
    END IF;
END $$;

-- Add subject_matter to LiveSession table
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'dating_livesession' AND column_name = 'subject_matter') THEN
        ALTER TABLE dating_livesession ADD COLUMN subject_matter VARCHAR(255);
        COMMENT ON COLUMN dating_livesession.subject_matter IS 'Subject matter like Speed Dating';
    END IF;
END $$;

-- =============================================================================
-- 2. SUBSCRIPTION PLANS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS dating_subscriptionplan (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    duration VARCHAR(20) NOT NULL DEFAULT '1_month',
    price_bondcoins INTEGER NOT NULL,
    price_usd DECIMAL(10,2) NOT NULL,
    unlimited_swipes BOOLEAN DEFAULT FALSE NOT NULL,
    undo_swipes BOOLEAN DEFAULT FALSE NOT NULL,
    unlimited_unwind BOOLEAN DEFAULT FALSE NOT NULL,
    global_access BOOLEAN DEFAULT FALSE NOT NULL,
    read_receipt BOOLEAN DEFAULT FALSE NOT NULL,
    live_hours_days INTEGER DEFAULT 7 NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Add constraints
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'dating_subscriptionplan_name_check') THEN
        ALTER TABLE dating_subscriptionplan ADD CONSTRAINT dating_subscriptionplan_name_check 
        CHECK (name IN ('free', 'basic', 'pro', 'prime'));
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'dating_subscriptionplan_duration_check') THEN
        ALTER TABLE dating_subscriptionplan ADD CONSTRAINT dating_subscriptionplan_duration_check 
        CHECK (duration IN ('1_week', '1_month', '3_months', '6_months', '1_year'));
    END IF;
END $$;

-- Create indexes
CREATE INDEX IF NOT EXISTS dating_subs_name_97bc40_idx ON dating_subscriptionplan (name, is_active);

-- =============================================================================
-- 3. USER SUBSCRIPTIONS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS dating_usersubscription (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    plan_id INTEGER NOT NULL REFERENCES dating_subscriptionplan(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    start_date TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    payment_method VARCHAR(50) DEFAULT 'bondcoin' NOT NULL,
    transaction_id VARCHAR(255),
    auto_renew BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Add constraints
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'dating_usersubscription_status_check') THEN
        ALTER TABLE dating_usersubscription ADD CONSTRAINT dating_usersubscription_status_check 
        CHECK (status IN ('active', 'expired', 'cancelled', 'pending'));
    END IF;
END $$;

-- Create indexes
CREATE INDEX IF NOT EXISTS dating_user_user_id_19e214_idx ON dating_usersubscription (user_id, status);
CREATE INDEX IF NOT EXISTS dating_user_end_dat_e077ed_idx ON dating_usersubscription (end_date);

-- =============================================================================
-- 4. BONDCOIN PACKAGES TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS dating_bondcoinpackage (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    bondcoin_amount INTEGER NOT NULL,
    price_usd DECIMAL(10,2) NOT NULL,
    is_popular BOOLEAN DEFAULT FALSE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create indexes
CREATE INDEX IF NOT EXISTS dating_bond_is_acti_0bfa3a_idx ON dating_bondcoinpackage (is_active, bondcoin_amount);

-- =============================================================================
-- 5. GIFT CATEGORIES TABLE (MOVED UP TO AVOID REFERENCE ISSUES)
-- =============================================================================

CREATE TABLE IF NOT EXISTS dating_giftcategory (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    icon_url TEXT,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- =============================================================================
-- 6. VIRTUAL GIFTS TABLE (MOVED UP TO AVOID REFERENCE ISSUES)
-- =============================================================================

CREATE TABLE IF NOT EXISTS dating_virtualgift (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category_id INTEGER NOT NULL REFERENCES dating_giftcategory(id) ON DELETE CASCADE,
    description TEXT,
    icon_url TEXT NOT NULL,
    cost_bondcoins INTEGER NOT NULL,
    is_popular BOOLEAN DEFAULT FALSE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create indexes for virtual gifts
CREATE INDEX IF NOT EXISTS dating_virt_categor_bd6841_idx ON dating_virtualgift (category_id, is_active);

-- =============================================================================
-- 7. BONDCOIN TRANSACTIONS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS dating_bondcointransaction (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    transaction_type VARCHAR(20) NOT NULL,
    amount INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'completed',
    package_id INTEGER REFERENCES dating_bondcoinpackage(id) ON DELETE SET NULL,
    subscription_id INTEGER REFERENCES dating_usersubscription(id) ON DELETE SET NULL,
    gift_id INTEGER REFERENCES dating_virtualgift(id) ON DELETE SET NULL,
    payment_method VARCHAR(50),
    payment_reference VARCHAR(255),
    description VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Add constraints
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'dating_bondcointransaction_transaction_type_check') THEN
        ALTER TABLE dating_bondcointransaction ADD CONSTRAINT dating_bondcointransaction_transaction_type_check 
        CHECK (transaction_type IN ('purchase', 'earn', 'spend', 'gift_sent', 'gift_received', 'subscription', 'refund'));
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'dating_bondcointransaction_status_check') THEN
        ALTER TABLE dating_bondcointransaction ADD CONSTRAINT dating_bondcointransaction_status_check 
        CHECK (status IN ('pending', 'completed', 'failed', 'cancelled'));
    END IF;
END $$;

-- Create indexes
CREATE INDEX IF NOT EXISTS dating_bond_user_id_310557_idx ON dating_bondcointransaction (user_id, transaction_type);
CREATE INDEX IF NOT EXISTS dating_bond_status_c0aec4_idx ON dating_bondcointransaction (status, created_at);

-- =============================================================================
-- 8. GIFT TRANSACTIONS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS dating_gifttransaction (
    id SERIAL PRIMARY KEY,
    sender_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    recipient_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    gift_id INTEGER NOT NULL REFERENCES dating_virtualgift(id) ON DELETE CASCADE,
    quantity INTEGER DEFAULT 1 NOT NULL,
    total_cost INTEGER NOT NULL,
    bondcoin_transaction_id INTEGER NOT NULL REFERENCES dating_bondcointransaction(id) ON DELETE CASCADE,
    context_type VARCHAR(20) DEFAULT 'general' NOT NULL,
    context_id INTEGER,
    status VARCHAR(20) DEFAULT 'sent' NOT NULL,
    message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Add constraints
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'dating_gifttransaction_context_type_check') THEN
        ALTER TABLE dating_gifttransaction ADD CONSTRAINT dating_gifttransaction_context_type_check 
        CHECK (context_type IN ('chat', 'profile', 'live_session', 'general'));
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'dating_gifttransaction_status_check') THEN
        ALTER TABLE dating_gifttransaction ADD CONSTRAINT dating_gifttransaction_status_check 
        CHECK (status IN ('sent', 'received', 'failed'));
    END IF;
END $$;

-- Create indexes
CREATE INDEX IF NOT EXISTS dating_gift_sender__d41450_idx ON dating_gifttransaction (sender_id, created_at);
CREATE INDEX IF NOT EXISTS dating_gift_recipie_8e3668_idx ON dating_gifttransaction (recipient_id, created_at);
CREATE INDEX IF NOT EXISTS dating_gift_context_f33922_idx ON dating_gifttransaction (context_type, context_id);

-- =============================================================================
-- 9. LIVE GIFTS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS dating_livegift (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES dating_livesession(id) ON DELETE CASCADE,
    sender_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    gift_id INTEGER NOT NULL REFERENCES dating_virtualgift(id) ON DELETE CASCADE,
    quantity INTEGER DEFAULT 1 NOT NULL,
    total_cost INTEGER NOT NULL,
    bondcoin_transaction_id INTEGER NOT NULL REFERENCES dating_bondcointransaction(id) ON DELETE CASCADE,
    chat_message VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create indexes
CREATE INDEX IF NOT EXISTS dating_live_session_41e9e2_idx ON dating_livegift (session_id, created_at);
CREATE INDEX IF NOT EXISTS dating_live_sender__debd9d_idx ON dating_livegift (sender_id, created_at);

-- =============================================================================
-- 10. LIVE JOIN REQUESTS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS dating_livejoinrequest (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES dating_livesession(id) ON DELETE CASCADE,
    requester_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    requested_role VARCHAR(20) DEFAULT 'co_host' NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    message TEXT,
    responded_by_id INTEGER REFERENCES dating_user(id) ON DELETE SET NULL,
    response_message TEXT,
    responded_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    UNIQUE(session_id, requester_id)
);

-- Add constraints
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'dating_livejoinrequest_requested_role_check') THEN
        ALTER TABLE dating_livejoinrequest ADD CONSTRAINT dating_livejoinrequest_requested_role_check 
        CHECK (requested_role IN ('co_host', 'speaker'));
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'dating_livejoinrequest_status_check') THEN
        ALTER TABLE dating_livejoinrequest ADD CONSTRAINT dating_livejoinrequest_status_check 
        CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled'));
    END IF;
END $$;

-- Create indexes
CREATE INDEX IF NOT EXISTS dating_live_session_07706a_idx ON dating_livejoinrequest (session_id, status);
CREATE INDEX IF NOT EXISTS dating_live_request_51f45d_idx ON dating_livejoinrequest (requester_id, status);

-- =============================================================================
-- 11. CREATE TRIGGERS FOR UPDATED_AT FIELDS
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for tables with updated_at fields
DO $$ 
BEGIN
    -- SubscriptionPlan trigger
    IF NOT EXISTS (SELECT 1 FROM information_schema.triggers 
                   WHERE trigger_name = 'dating_subscriptionplan_updated_at') THEN
        CREATE TRIGGER dating_subscriptionplan_updated_at
            BEFORE UPDATE ON dating_subscriptionplan
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    -- UserSubscription trigger
    IF NOT EXISTS (SELECT 1 FROM information_schema.triggers 
                   WHERE trigger_name = 'dating_usersubscription_updated_at') THEN
        CREATE TRIGGER dating_usersubscription_updated_at
            BEFORE UPDATE ON dating_usersubscription
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    -- BondcoinPackage trigger
    IF NOT EXISTS (SELECT 1 FROM information_schema.triggers 
                   WHERE trigger_name = 'dating_bondcoinpackage_updated_at') THEN
        CREATE TRIGGER dating_bondcoinpackage_updated_at
            BEFORE UPDATE ON dating_bondcoinpackage
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    -- BondcoinTransaction trigger
    IF NOT EXISTS (SELECT 1 FROM information_schema.triggers 
                   WHERE trigger_name = 'dating_bondcointransaction_updated_at') THEN
        CREATE TRIGGER dating_bondcointransaction_updated_at
            BEFORE UPDATE ON dating_bondcointransaction
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    -- GiftCategory trigger
    IF NOT EXISTS (SELECT 1 FROM information_schema.triggers 
                   WHERE trigger_name = 'dating_giftcategory_updated_at') THEN
        CREATE TRIGGER dating_giftcategory_updated_at
            BEFORE UPDATE ON dating_giftcategory
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    -- VirtualGift trigger
    IF NOT EXISTS (SELECT 1 FROM information_schema.triggers 
                   WHERE trigger_name = 'dating_virtualgift_updated_at') THEN
        CREATE TRIGGER dating_virtualgift_updated_at
            BEFORE UPDATE ON dating_virtualgift
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    -- GiftTransaction trigger
    IF NOT EXISTS (SELECT 1 FROM information_schema.triggers 
                   WHERE trigger_name = 'dating_gifttransaction_updated_at') THEN
        CREATE TRIGGER dating_gifttransaction_updated_at
            BEFORE UPDATE ON dating_gifttransaction
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    -- LiveJoinRequest trigger
    IF NOT EXISTS (SELECT 1 FROM information_schema.triggers 
                   WHERE trigger_name = 'dating_livejoinrequest_updated_at') THEN
        CREATE TRIGGER dating_livejoinrequest_updated_at
            BEFORE UPDATE ON dating_livejoinrequest
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- =============================================================================
-- 12. INSERT DEFAULT DATA
-- =============================================================================

-- Insert default subscription plans
INSERT INTO dating_subscriptionplan (name, display_name, description, duration, price_bondcoins, price_usd, unlimited_swipes, undo_swipes, unlimited_unwind, global_access, read_receipt, live_hours_days) VALUES
('free', 'Free', 'Basic features for free users', '1_month', 0, 0.00, false, false, false, false, false, 7),
('basic', 'BONDAH Basic', 'Enhanced features for basic users', '1_week', 60, 0.89, true, true, true, false, false, 7),
('pro', 'BONDAH Pro', 'Premium features for pro users', '1_month', 180, 2.67, true, true, true, true, false, 7),
('prime', 'BONDAH Prime', 'Ultimate features for prime users', '3_months', 350, 4.45, true, true, true, true, true, 14)
ON CONFLICT (name) DO NOTHING;

-- Insert default Bondcoin packages
INSERT INTO dating_bondcoinpackage (name, bondcoin_amount, price_usd, is_popular) VALUES
('10 Bondcoins', 10, 0.89, false),
('30 Bondcoins', 30, 2.67, false),
('50 Bondcoins', 50, 4.45, false),
('100 Bondcoins', 100, 8.90, false),
('300 Bondcoins', 300, 26.70, false),
('500 Bondcoins', 500, 44.50, false),
('800 Bondcoins', 800, 71.20, false),
('1,200 Bondcoins', 1200, 106.80, false),
('2,000 Bondcoins', 2000, 178.00, true)
ON CONFLICT DO NOTHING;

-- Insert default gift categories
INSERT INTO dating_giftcategory (name, display_name, description) VALUES
('charm', 'Charm', 'Charming gifts to express affection'),
('treasure', 'Treasure', 'Valuable treasures for special moments'),
('unique', 'Unique', 'Unique and exclusive gifts')
ON CONFLICT (name) DO NOTHING;

-- Insert default virtual gifts
INSERT INTO dating_virtualgift (name, category_id, icon_url, cost_bondcoins, is_popular) VALUES
-- Charm gifts
('Rose Charm', (SELECT id FROM dating_giftcategory WHERE name = 'charm'), 'https://example.com/icons/rose_charm.png', 10, false),
('Heart Charm', (SELECT id FROM dating_giftcategory WHERE name = 'charm'), 'https://example.com/icons/heart_charm.png', 10, false),
('Moon Charm', (SELECT id FROM dating_giftcategory WHERE name = 'charm'), 'https://example.com/icons/moon_charm.png', 10, false),
('Wings Charm', (SELECT id FROM dating_giftcategory WHERE name = 'charm'), 'https://example.com/icons/wings_charm.png', 10, false),
('Champagne Bottle', (SELECT id FROM dating_giftcategory WHERE name = 'charm'), 'https://example.com/icons/champagne.png', 10, false),
('Rose Bouquet', (SELECT id FROM dating_giftcategory WHERE name = 'charm'), 'https://example.com/icons/rose_bouquet.png', 10, false),
('Treasure Chest', (SELECT id FROM dating_giftcategory WHERE name = 'charm'), 'https://example.com/icons/treasure_chest.png', 10, false),
('Royal Chair', (SELECT id FROM dating_giftcategory WHERE name = 'charm'), 'https://example.com/icons/royal_chair.png', 10, false),

-- Treasure gifts
('Gold Bar', (SELECT id FROM dating_giftcategory WHERE name = 'treasure'), 'https://example.com/icons/gold_bar.png', 10, false),
('Pearl', (SELECT id FROM dating_giftcategory WHERE name = 'treasure'), 'https://example.com/icons/pearl.png', 10, false),
('Crown', (SELECT id FROM dating_giftcategory WHERE name = 'treasure'), 'https://example.com/icons/crown.png', 10, false),
('Ruby', (SELECT id FROM dating_giftcategory WHERE name = 'treasure'), 'https://example.com/icons/ruby.png', 10, false),

-- Unique gifts
('Diamond Ring', (SELECT id FROM dating_giftcategory WHERE name = 'unique'), 'https://example.com/icons/diamond_ring.png', 10, false),
('Private Jet', (SELECT id FROM dating_giftcategory WHERE name = 'unique'), 'https://example.com/icons/private_jet.png', 10, false),
('Yacht', (SELECT id FROM dating_giftcategory WHERE name = 'unique'), 'https://example.com/icons/yacht.png', 10, false),
('Black Diamond', (SELECT id FROM dating_giftcategory WHERE name = 'unique'), 'https://example.com/icons/black_diamond.png', 10, false)
ON CONFLICT DO NOTHING;

-- =============================================================================
-- 13. VERIFICATION QUERIES
-- =============================================================================

-- Verify all tables were created
SELECT 
    table_name,
    CASE 
        WHEN table_name IN (
            'dating_subscriptionplan', 'dating_usersubscription', 'dating_bondcoinpackage',
            'dating_bondcointransaction', 'dating_giftcategory', 'dating_virtualgift',
            'dating_gifttransaction', 'dating_livegift', 'dating_livejoinrequest'
        ) THEN '✅ Created'
        ELSE '❌ Missing'
    END as status
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name LIKE 'dating_%'
ORDER BY table_name;

-- Verify new columns were added
SELECT 
    table_name,
    column_name,
    CASE 
        WHEN column_name IN ('bondcoin_balance', 'subject_matter') THEN '✅ Added'
        ELSE '❌ Missing'
    END as status
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name IN ('dating_user', 'dating_livesession')
AND column_name IN ('bondcoin_balance', 'subject_matter')
ORDER BY table_name, column_name;

-- Count records in each new table
SELECT 'dating_subscriptionplan' as table_name, COUNT(*) as record_count FROM dating_subscriptionplan
UNION ALL
SELECT 'dating_bondcoinpackage', COUNT(*) FROM dating_bondcoinpackage
UNION ALL
SELECT 'dating_giftcategory', COUNT(*) FROM dating_giftcategory
UNION ALL
SELECT 'dating_virtualgift', COUNT(*) FROM dating_virtualgift
ORDER BY table_name;

-- =============================================================================
-- SCRIPT COMPLETED SUCCESSFULLY
-- =============================================================================
-- All subscription and monetization features have been implemented:
-- ✅ Subscription Plans (Basic, Pro, Prime) with feature gating
-- ✅ Bondcoin Wallet System with transaction history
-- ✅ Virtual Gifting System with categories and items
-- ✅ Live Streaming Enhancements (gifting, join requests, subject matter)
-- ✅ All tables, indexes, constraints, and triggers created
-- ✅ Default data inserted for testing
-- 
-- The Bondah Dating App backend now supports all monetization features
-- from the Figma designs including subscription management, virtual currency,
-- gifting system, and enhanced live streaming capabilities.
-- =============================================================================
