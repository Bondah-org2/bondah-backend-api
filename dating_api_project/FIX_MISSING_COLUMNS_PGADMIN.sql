-- Fix Missing Columns in Existing Tables for Bondah Dating API
-- Execute this script in pgAdmin to add missing columns

-- Fix account_emailaddress table - add missing 'primary' column
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'account_emailaddress' AND column_name = 'primary'
    ) THEN
        ALTER TABLE account_emailaddress ADD COLUMN "primary" BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END $$;

-- Fix dating_deviceregistration table - add missing 'push_token' and 'updated_at' columns
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'dating_deviceregistration' AND column_name = 'push_token'
    ) THEN
        ALTER TABLE dating_deviceregistration ADD COLUMN push_token VARCHAR(255) NULL;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'dating_deviceregistration' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE dating_deviceregistration ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
    END IF;
END $$;

-- Fix dating_locationhistory table - add missing 'timestamp' and 'source' columns
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'dating_locationhistory' AND column_name = 'timestamp'
    ) THEN
        ALTER TABLE dating_locationhistory ADD COLUMN timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW();
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'dating_locationhistory' AND column_name = 'source'
    ) THEN
        ALTER TABLE dating_locationhistory ADD COLUMN source VARCHAR(20) NOT NULL DEFAULT 'gps';
    END IF;
END $$;

-- Fix dating_locationpermission table - add missing columns
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'dating_locationpermission' AND column_name = 'location_enabled'
    ) THEN
        ALTER TABLE dating_locationpermission ADD COLUMN location_enabled BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'dating_locationpermission' AND column_name = 'background_location_enabled'
    ) THEN
        ALTER TABLE dating_locationpermission ADD COLUMN background_location_enabled BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'dating_locationpermission' AND column_name = 'precise_location_enabled'
    ) THEN
        ALTER TABLE dating_locationpermission ADD COLUMN precise_location_enabled BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'dating_locationpermission' AND column_name = 'location_services_consent'
    ) THEN
        ALTER TABLE dating_locationpermission ADD COLUMN location_services_consent BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'dating_locationpermission' AND column_name = 'location_data_sharing'
    ) THEN
        ALTER TABLE dating_locationpermission ADD COLUMN location_data_sharing BOOLEAN NOT NULL DEFAULT TRUE;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'dating_locationpermission' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE dating_locationpermission ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
    END IF;
END $$;

-- Fix dating_message table - add missing 'tip_amount' and 'tip_gift' columns
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'dating_message' AND column_name = 'tip_amount'
    ) THEN
        ALTER TABLE dating_message ADD COLUMN tip_amount INTEGER NOT NULL DEFAULT 0;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'dating_message' AND column_name = 'tip_gift_id'
    ) THEN
        ALTER TABLE dating_message ADD COLUMN tip_gift_id INTEGER NULL;
        -- Add foreign key constraint if virtualgift table exists
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'dating_virtualgift') THEN
            ALTER TABLE dating_message ADD CONSTRAINT dating_message_tip_gift_id_fkey 
            FOREIGN KEY (tip_gift_id) REFERENCES dating_virtualgift(id) ON DELETE SET NULL;
        END IF;
    END IF;
END $$;

-- Fix dating_socialaccount table - add missing 'provider_user_id' column
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'dating_socialaccount' AND column_name = 'provider_user_id'
    ) THEN
        ALTER TABLE dating_socialaccount ADD COLUMN provider_user_id VARCHAR(191) NOT NULL DEFAULT '';
    END IF;
END $$;

-- Fix dating_usermatch table - add missing 'distance' column
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'dating_usermatch' AND column_name = 'distance'
    ) THEN
        ALTER TABLE dating_usermatch ADD COLUMN distance DECIMAL(10,2) NULL;
    END IF;
END $$;

-- Fix socialaccount_socialapp table - add missing 'provider_id' and 'settings' columns
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'socialaccount_socialapp' AND column_name = 'provider_id'
    ) THEN
        ALTER TABLE socialaccount_socialapp ADD COLUMN provider_id VARCHAR(30) NOT NULL DEFAULT '';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'socialaccount_socialapp' AND column_name = 'settings'
    ) THEN
        ALTER TABLE socialaccount_socialapp ADD COLUMN settings JSONB NOT NULL DEFAULT '{}';
    END IF;
END $$;

-- Fix dating_user table - add missing 'bondcoin_balance' column
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'dating_user' AND column_name = 'bondcoin_balance'
    ) THEN
        ALTER TABLE dating_user ADD COLUMN bondcoin_balance INTEGER NOT NULL DEFAULT 0;
    END IF;
END $$;

-- Update message_type constraint to include 'tip' choice
DO $$ 
BEGIN
    -- Drop existing constraint if it exists
    IF EXISTS (
        SELECT 1 FROM information_schema.check_constraints 
        WHERE constraint_name LIKE '%message_type%'
    ) THEN
        ALTER TABLE dating_message DROP CONSTRAINT IF EXISTS dating_message_message_type_check;
    END IF;
    
    -- Add new constraint with tip choice
    ALTER TABLE dating_message ADD CONSTRAINT dating_message_message_type_check 
    CHECK (message_type IN ('text', 'voice_note', 'image', 'video', 'document', 'system', 'matchmaker_intro', 'call_start', 'call_end', 'tip'));
END $$;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS dating_message_tip_amount_idx ON dating_message (tip_amount);
CREATE INDEX IF NOT EXISTS dating_message_tip_gift_id_idx ON dating_message (tip_gift_id);
CREATE INDEX IF NOT EXISTS dating_deviceregistration_push_token_idx ON dating_deviceregistration (push_token);
CREATE INDEX IF NOT EXISTS dating_deviceregistration_updated_at_idx ON dating_deviceregistration (updated_at);
CREATE INDEX IF NOT EXISTS dating_locationhistory_timestamp_idx ON dating_locationhistory (timestamp);
CREATE INDEX IF NOT EXISTS dating_locationhistory_source_idx ON dating_locationhistory (source);
CREATE INDEX IF NOT EXISTS dating_locationpermission_location_enabled_idx ON dating_locationpermission (location_enabled);
CREATE INDEX IF NOT EXISTS dating_locationpermission_background_location_enabled_idx ON dating_locationpermission (background_location_enabled);
CREATE INDEX IF NOT EXISTS dating_locationpermission_updated_at_idx ON dating_locationpermission (updated_at);
CREATE INDEX IF NOT EXISTS dating_socialaccount_provider_user_id_idx ON dating_socialaccount (provider_user_id);
CREATE INDEX IF NOT EXISTS dating_usermatch_distance_idx ON dating_usermatch (distance);
CREATE INDEX IF NOT EXISTS socialaccount_socialapp_provider_id_idx ON socialaccount_socialapp (provider_id);
CREATE INDEX IF NOT EXISTS socialaccount_socialapp_settings_idx ON socialaccount_socialapp USING GIN (settings);
CREATE INDEX IF NOT EXISTS dating_user_bondcoin_balance_idx ON dating_user (bondcoin_balance);

-- Add comments for documentation
COMMENT ON COLUMN account_emailaddress."primary" IS 'Primary email address flag (django-allauth)';
COMMENT ON COLUMN dating_deviceregistration.push_token IS 'Push notification token for device';
COMMENT ON COLUMN dating_deviceregistration.updated_at IS 'Last update timestamp for device registration';
COMMENT ON COLUMN dating_locationhistory.timestamp IS 'Location update timestamp';
COMMENT ON COLUMN dating_locationhistory.source IS 'Location source (GPS, network, manual, IP)';
COMMENT ON COLUMN dating_locationpermission.location_enabled IS 'User location sharing permission';
COMMENT ON COLUMN dating_locationpermission.background_location_enabled IS 'Background location permission';
COMMENT ON COLUMN dating_locationpermission.precise_location_enabled IS 'Precise location permission';
COMMENT ON COLUMN dating_locationpermission.location_services_consent IS 'Location services consent';
COMMENT ON COLUMN dating_locationpermission.location_data_sharing IS 'Location data sharing permission';
COMMENT ON COLUMN dating_locationpermission.updated_at IS 'Last update timestamp for location permissions';
COMMENT ON COLUMN dating_message.tip_amount IS 'Tip amount in Bondcoins';
COMMENT ON COLUMN dating_message.tip_gift_id IS 'Gift sent with message';
COMMENT ON COLUMN dating_socialaccount.provider_user_id IS 'Provider-specific user ID';
COMMENT ON COLUMN dating_usermatch.distance IS 'Distance between matched users';
COMMENT ON COLUMN socialaccount_socialapp.provider_id IS 'Provider identifier';
COMMENT ON COLUMN socialaccount_socialapp.settings IS 'Provider-specific settings (JSON)';
COMMENT ON COLUMN dating_user.bondcoin_balance IS 'User balance in Bondcoins (virtual currency)';

-- Success message
SELECT 'Missing columns added successfully!' as status;
