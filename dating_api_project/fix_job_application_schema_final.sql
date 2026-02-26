-- Fix Job Application Table Schema - FINAL VERSION
-- Run this in pgAdmin connected to Railway database

-- 1. Check current table structure
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'dating_jobapplication' 
ORDER BY ordinal_position;

-- 2. Add missing columns if they don't exist
ALTER TABLE dating_jobapplication 
ADD COLUMN IF NOT EXISTS first_name VARCHAR(100),
ADD COLUMN IF NOT EXISTS last_name VARCHAR(100);

-- 3. Update any NULL values in first_name and last_name
UPDATE dating_jobapplication 
SET 
    first_name = COALESCE(first_name, 'Unknown'),
    last_name = COALESCE(last_name, 'User')
WHERE first_name IS NULL OR last_name IS NULL;

-- 4. Make first_name and last_name NOT NULL
ALTER TABLE dating_jobapplication 
ALTER COLUMN first_name SET NOT NULL,
ALTER COLUMN last_name SET NOT NULL;

-- 5. Verify the final table structure
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'dating_jobapplication' 
ORDER BY ordinal_position;

-- 6. Show sample data to verify
SELECT id, first_name, last_name, email, job_id, status 
FROM dating_jobapplication 
LIMIT 5;
