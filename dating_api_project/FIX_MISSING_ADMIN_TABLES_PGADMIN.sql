-- Fix Missing Django Admin Tables for Bondah Dating API
-- Execute this script in pgAdmin to create missing admin tables

-- Create account_emailaddress table (django-allauth)
CREATE TABLE IF NOT EXISTS account_emailaddress (
    id SERIAL PRIMARY KEY,
    email VARCHAR(254) NOT NULL,
    verified BOOLEAN NOT NULL,
    primary_email BOOLEAN NOT NULL,
    user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create authtoken_token table (django-rest-framework)
CREATE TABLE IF NOT EXISTS authtoken_token (
    key VARCHAR(40) NOT NULL PRIMARY KEY,
    created TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    user_id INTEGER NOT NULL UNIQUE REFERENCES dating_user(id) ON DELETE CASCADE
);

-- Create socialaccount_socialapp table (django-allauth)
CREATE TABLE IF NOT EXISTS socialaccount_socialapp (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(30) NOT NULL,
    name VARCHAR(40) NOT NULL,
    client_id VARCHAR(191) NOT NULL,
    secret VARCHAR(191) NOT NULL,
    key VARCHAR(191) NOT NULL DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create socialaccount_socialaccount table (django-allauth)
CREATE TABLE IF NOT EXISTS socialaccount_socialaccount (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(30) NOT NULL,
    uid VARCHAR(191) NOT NULL,
    last_login TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    date_joined TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    extra_data JSONB NOT NULL DEFAULT '{}',
    user_id INTEGER NOT NULL REFERENCES dating_user(id) ON DELETE CASCADE,
    app_id INTEGER REFERENCES socialaccount_socialapp(id) ON DELETE CASCADE
);

-- Create socialaccount_socialtoken table (django-allauth)
CREATE TABLE IF NOT EXISTS socialaccount_socialtoken (
    id SERIAL PRIMARY KEY,
    token TEXT NOT NULL,
    token_secret TEXT NOT NULL DEFAULT '',
    expires_at TIMESTAMP WITH TIME ZONE,
    account_id INTEGER NOT NULL REFERENCES socialaccount_socialaccount(id) ON DELETE CASCADE,
    app_id INTEGER NOT NULL REFERENCES socialaccount_socialapp(id) ON DELETE CASCADE
);

-- Create sites_site table (django.contrib.sites)
CREATE TABLE IF NOT EXISTS sites_site (
    id SERIAL PRIMARY KEY,
    domain VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(50) NOT NULL
);

-- Insert default site if it doesn't exist
INSERT INTO sites_site (id, domain, name) VALUES (1, 'example.com', 'example.com') 
ON CONFLICT (id) DO NOTHING;

-- Create account_emailconfirmation table (django-allauth)
CREATE TABLE IF NOT EXISTS account_emailconfirmation (
    id SERIAL PRIMARY KEY,
    created TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    sent TIMESTAMP WITH TIME ZONE,
    key VARCHAR(64) NOT NULL UNIQUE,
    email_address_id INTEGER NOT NULL REFERENCES account_emailaddress(id) ON DELETE CASCADE
);

-- Create account_emailconfirmationhmac table (django-allauth)
CREATE TABLE IF NOT EXISTS account_emailconfirmationhmac (
    id SERIAL PRIMARY KEY,
    created TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    sent TIMESTAMP WITH TIME ZONE,
    key VARCHAR(64) NOT NULL UNIQUE,
    email_address_id INTEGER NOT NULL REFERENCES account_emailaddress(id) ON DELETE CASCADE
);

-- Create socialaccount_socialapp_sites table (many-to-many relationship)
CREATE TABLE IF NOT EXISTS socialaccount_socialapp_sites (
    id SERIAL PRIMARY KEY,
    socialapp_id INTEGER NOT NULL REFERENCES socialaccount_socialapp(id) ON DELETE CASCADE,
    site_id INTEGER NOT NULL REFERENCES sites_site(id) ON DELETE CASCADE
);

-- Add constraints using DO blocks (PostgreSQL compatible syntax)
DO $$ 
BEGIN
    -- Add unique constraint for account_emailaddress.email if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'account_emailaddress_email_key'
    ) THEN
        ALTER TABLE account_emailaddress ADD CONSTRAINT account_emailaddress_email_key UNIQUE (email);
    END IF;
END $$;

DO $$ 
BEGIN
    -- Add unique constraint for socialaccount_socialaccount if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'socialaccount_socialaccount_provider_uid_key'
    ) THEN
        ALTER TABLE socialaccount_socialaccount ADD CONSTRAINT socialaccount_socialaccount_provider_uid_key UNIQUE (provider, uid);
    END IF;
END $$;

DO $$ 
BEGIN
    -- Add unique constraint for socialaccount_socialtoken if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'socialaccount_socialtoken_app_id_account_id_key'
    ) THEN
        ALTER TABLE socialaccount_socialtoken ADD CONSTRAINT socialaccount_socialtoken_app_id_account_id_key UNIQUE (app_id, account_id);
    END IF;
END $$;

DO $$ 
BEGIN
    -- Add unique constraint for socialaccount_socialapp_sites if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'socialaccount_socialapp_sites_socialapp_id_site_id_key'
    ) THEN
        ALTER TABLE socialaccount_socialapp_sites ADD CONSTRAINT socialaccount_socialapp_sites_socialapp_id_site_id_key UNIQUE (socialapp_id, site_id);
    END IF;
END $$;

-- Create indexes if they don't exist
CREATE INDEX IF NOT EXISTS account_emailaddress_user_id_idx ON account_emailaddress (user_id);
CREATE INDEX IF NOT EXISTS authtoken_token_user_id_idx ON authtoken_token (user_id);
CREATE INDEX IF NOT EXISTS socialaccount_socialaccount_user_id_idx ON socialaccount_socialaccount (user_id);
CREATE INDEX IF NOT EXISTS socialaccount_socialtoken_account_id_idx ON socialaccount_socialtoken (account_id);
CREATE INDEX IF NOT EXISTS account_emailconfirmation_key_idx ON account_emailconfirmation (key);
CREATE INDEX IF NOT EXISTS account_emailconfirmationhmac_key_idx ON account_emailconfirmationhmac (key);
CREATE INDEX IF NOT EXISTS socialaccount_socialapp_sites_socialapp_id_idx ON socialaccount_socialapp_sites (socialapp_id);
CREATE INDEX IF NOT EXISTS socialaccount_socialapp_sites_site_id_idx ON socialaccount_socialapp_sites (site_id);

-- Add comments for documentation
COMMENT ON TABLE account_emailaddress IS 'Email addresses associated with user accounts (django-allauth)';
COMMENT ON TABLE authtoken_token IS 'Authentication tokens for API access (django-rest-framework)';
COMMENT ON TABLE socialaccount_socialapp IS 'Social authentication applications (django-allauth)';
COMMENT ON TABLE socialaccount_socialaccount IS 'Social media accounts linked to users (django-allauth)';
COMMENT ON TABLE socialaccount_socialtoken IS 'Social authentication tokens (django-allauth)';
COMMENT ON TABLE sites_site IS 'Sites configuration (django.contrib.sites)';
COMMENT ON TABLE account_emailconfirmation IS 'Email confirmation records (django-allauth)';
COMMENT ON TABLE account_emailconfirmationhmac IS 'HMAC email confirmation records (django-allauth)';
COMMENT ON TABLE socialaccount_socialapp_sites IS 'Many-to-many relationship between social apps and sites (django-allauth)';

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON account_emailaddress TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON authtoken_token TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON socialaccount_socialapp TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON socialaccount_socialaccount TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON socialaccount_socialtoken TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON sites_site TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON account_emailconfirmation TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON account_emailconfirmationhmac TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON socialaccount_socialapp_sites TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE account_emailaddress_id_seq TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE authtoken_token_key_seq TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE socialaccount_socialapp_id_seq TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE socialaccount_socialaccount_id_seq TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE socialaccount_socialtoken_id_seq TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE sites_site_id_seq TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE account_emailconfirmation_id_seq TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE account_emailconfirmationhmac_id_seq TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE socialaccount_socialapp_sites_id_seq TO your_app_user;

-- Success message
SELECT 'Missing Django admin tables created successfully!' as status;
