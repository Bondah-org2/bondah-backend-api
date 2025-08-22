-- Fix Job Application Table Schema
-- Run this in pgAdmin connected to Railway database

-- 1. Add missing columns to dating_jobapplication table
ALTER TABLE dating_jobapplication 
ADD COLUMN IF NOT EXISTS first_name VARCHAR(100),
ADD COLUMN IF NOT EXISTS last_name VARCHAR(100);

-- 2. Update existing records to have first_name and last_name
-- Split the name field into first_name and last_name
UPDATE dating_jobapplication 
SET 
    first_name = CASE 
        WHEN name IS NOT NULL AND name != '' THEN 
            CASE 
                WHEN position(' ' in name) > 0 THEN 
                    substring(name from 1 for position(' ' in name) - 1)
                ELSE name
            END
        ELSE 'Unknown'
    END,
    last_name = CASE 
        WHEN name IS NOT NULL AND name != '' THEN 
            CASE 
                WHEN position(' ' in name) > 0 THEN 
                    substring(name from position(' ' in name) + 1)
                ELSE ''
            END
        ELSE 'User'
    END
WHERE first_name IS NULL OR last_name IS NULL;

-- 3. Make first_name and last_name NOT NULL after populating them
ALTER TABLE dating_jobapplication 
ALTER COLUMN first_name SET NOT NULL,
ALTER COLUMN last_name SET NOT NULL;

-- 4. Drop the old name column if it exists
ALTER TABLE dating_jobapplication 
DROP COLUMN IF EXISTS name;

-- 5. Verify the table structure
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'dating_jobapplication' 
ORDER BY ordinal_position;

-- 6. Show sample data
SELECT id, first_name, last_name, email, job_id, status 
FROM dating_jobapplication 
LIMIT 5;
