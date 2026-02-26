-- ===========================================
-- FINAL WAITLIST COLUMN FIX
-- ===========================================

BEGIN;

-- Step 1: Check current table structure
SELECT 'Current table structure:' as info;
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'dating_waitlist' 
ORDER BY ordinal_position;

-- Step 2: Rename joined_at to date_joined
ALTER TABLE dating_waitlist RENAME COLUMN joined_at TO date_joined;
SELECT '✅ Renamed joined_at to date_joined' as status;

-- Step 3: Make date_joined NOT NULL
ALTER TABLE dating_waitlist ALTER COLUMN date_joined SET NOT NULL;
SELECT '✅ Made date_joined NOT NULL' as status;

-- Step 4: Add default timestamp
ALTER TABLE dating_waitlist ALTER COLUMN date_joined SET DEFAULT CURRENT_TIMESTAMP;
SELECT '✅ Added default timestamp' as status;

-- Step 5: Update any existing records with null date_joined
UPDATE dating_waitlist SET date_joined = CURRENT_TIMESTAMP WHERE date_joined IS NULL;
SELECT '✅ Updated existing records' as status;

-- Step 6: Show final results
SELECT 'Final table structure:' as info;
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'dating_waitlist' 
ORDER BY ordinal_position;

SELECT 'Final waitlist entries:' as info;
SELECT id, email, first_name, last_name, date_joined 
FROM dating_waitlist 
ORDER BY date_joined DESC;

SELECT 'Total entries: ' || COUNT(*) as summary FROM dating_waitlist;

COMMIT;

SELECT '🎉 WAITLIST COLUMN FIX COMPLETE!' as result;
