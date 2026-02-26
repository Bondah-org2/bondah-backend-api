-- Complete Database Fix for Bondah Dating
-- Run this in pgAdmin to fix all database issues

-- 1. Fix dating_user table - add all missing columns
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS username VARCHAR(150) UNIQUE;
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS name VARCHAR(255);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS age INTEGER;
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS gender VARCHAR(10);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS location VARCHAR(255);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS bio TEXT;
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS is_matchmaker BOOLEAN DEFAULT FALSE;
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS first_name VARCHAR(150);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS last_name VARCHAR(150);
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS is_staff BOOLEAN DEFAULT FALSE;
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS date_joined TIMESTAMP WITH TIME ZONE DEFAULT NOW();
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS last_login TIMESTAMP WITH TIME ZONE;
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS is_superuser BOOLEAN DEFAULT FALSE;
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS groups INTEGER[];
ALTER TABLE dating_user ADD COLUMN IF NOT EXISTS user_permissions INTEGER[];

-- 2. Create dating_adminuser table
CREATE TABLE IF NOT EXISTS dating_adminuser (
    id SERIAL PRIMARY KEY,
    email VARCHAR(254) UNIQUE NOT NULL,
    password VARCHAR(128) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Create dating_adminotp table
CREATE TABLE IF NOT EXISTS dating_adminotp (
    id SERIAL PRIMARY KEY,
    admin_user_id INTEGER REFERENCES dating_adminuser(id),
    otp_code VARCHAR(6) NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Create dating_emaillog table
CREATE TABLE IF NOT EXISTS dating_emaillog (
    id SERIAL PRIMARY KEY,
    email_type VARCHAR(50) NOT NULL,
    recipient_email VARCHAR(254) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    is_sent BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Fix dating_job table
ALTER TABLE dating_job ADD COLUMN IF NOT EXISTS job_type VARCHAR(20);
ALTER TABLE dating_job ADD COLUMN IF NOT EXISTS requirements JSONB;
ALTER TABLE dating_job ADD COLUMN IF NOT EXISTS responsibilities TEXT;
ALTER TABLE dating_job ADD COLUMN IF NOT EXISTS benefits TEXT;
ALTER TABLE dating_job ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- 6. Fix dating_jobapplication table
ALTER TABLE dating_jobapplication ADD COLUMN IF NOT EXISTS first_name VARCHAR(100);
ALTER TABLE dating_jobapplication ADD COLUMN IF NOT EXISTS last_name VARCHAR(100);
ALTER TABLE dating_jobapplication ADD COLUMN IF NOT EXISTS resume_url VARCHAR(500);
ALTER TABLE dating_jobapplication ADD COLUMN IF NOT EXISTS cover_letter TEXT;
ALTER TABLE dating_jobapplication ADD COLUMN IF NOT EXISTS experience_years INTEGER;
ALTER TABLE dating_jobapplication ADD COLUMN IF NOT EXISTS current_company VARCHAR(255);
ALTER TABLE dating_jobapplication ADD COLUMN IF NOT EXISTS expected_salary VARCHAR(100);
ALTER TABLE dating_jobapplication ADD COLUMN IF NOT EXISTS applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- 7. Fix dating_waitlist table
ALTER TABLE dating_waitlist ADD COLUMN IF NOT EXISTS first_name VARCHAR(100);
ALTER TABLE dating_waitlist ADD COLUMN IF NOT EXISTS last_name VARCHAR(100);
ALTER TABLE dating_waitlist ADD COLUMN IF NOT EXISTS date_joined TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- 8. Update existing user with proper data
UPDATE dating_user 
SET 
    username = email,
    name = 'Admin User',
    first_name = 'Admin',
    last_name = 'User',
    is_staff = TRUE,
    is_superuser = TRUE,
    is_active = TRUE,
    date_joined = NOW()
WHERE email = 'giddehis@gmail.com';

-- 9. Create admin user (password: Cleverestboo_33)
INSERT INTO dating_adminuser (email, password, is_active)
VALUES ('admin@bondah.org', 'pbkdf2_sha256$600000$YourHashedPasswordHere$ActualHashValue', TRUE)
ON CONFLICT (email) DO NOTHING;

-- 10. Create a sample job for testing
INSERT INTO dating_job (title, job_type, category, status, description, location, salary_range, requirements, responsibilities, benefits)
VALUES (
    'Backend Developer',
    'full-time',
    'engineering',
    'open',
    'We are looking for a talented backend developer to join our team.',
    'Remote',
    '$80,000 - $120,000',
    '["Python", "Django", "PostgreSQL", "REST APIs"]',
    'Develop and maintain backend services, work with the team on new features.',
    'Health insurance, flexible hours, remote work'
)
ON CONFLICT DO NOTHING;

-- Verify the fixes
SELECT 'dating_user' as table_name, COUNT(*) as row_count FROM dating_user
UNION ALL
SELECT 'dating_adminuser', COUNT(*) FROM dating_adminuser
UNION ALL
SELECT 'dating_adminotp', COUNT(*) FROM dating_adminotp
UNION ALL
SELECT 'dating_emaillog', COUNT(*) FROM dating_emaillog
UNION ALL
SELECT 'dating_job', COUNT(*) FROM dating_job
UNION ALL
SELECT 'dating_jobapplication', COUNT(*) FROM dating_jobapplication
UNION ALL
SELECT 'dating_waitlist', COUNT(*) FROM dating_waitlist;
