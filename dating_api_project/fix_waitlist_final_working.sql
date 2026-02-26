-- ===========================================
-- WORKING WAITLIST FIX (HANDLES EXISTING COLUMNS)
-- ===========================================

BEGIN;

-- Step 1: Check current table structure
SELECT 'Current table structure:' as info;
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'dating_waitlist' 
ORDER BY ordinal_position;

-- Step 2: Check if joined_at exists and rename it (only if it exists)
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'dating_waitlist' AND column_name = 'joined_at'
    ) THEN
        ALTER TABLE dating_waitlist RENAME COLUMN joined_at TO date_joined;
        RAISE NOTICE '✅ Renamed joined_at to date_joined';
    ELSE
        RAISE NOTICE '✅ date_joined column already exists';
    END IF;
END $$;

-- Step 3: Make sure date_joined is NOT NULL
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'dating_waitlist' 
        AND column_name = 'date_joined' 
        AND is_nullable = 'YES'
    ) THEN
        ALTER TABLE dating_waitlist ALTER COLUMN date_joined SET NOT NULL;
        RAISE NOTICE '✅ Made date_joined NOT NULL';
    ELSE
        RAISE NOTICE '✅ date_joined is already NOT NULL';
    END IF;
END $$;

-- Step 4: Add default timestamp if missing
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'dating_waitlist' 
        AND column_name = 'date_joined' 
        AND column_default IS NOT NULL
    ) THEN
        ALTER TABLE dating_waitlist ALTER COLUMN date_joined SET DEFAULT CURRENT_TIMESTAMP;
        RAISE NOTICE '✅ Added default timestamp';
    ELSE
        RAISE NOTICE '✅ date_joined already has default';
    END IF;
END $$;

-- Step 5: Update any existing records with null date_joined
UPDATE dating_waitlist SET date_joined = CURRENT_TIMESTAMP WHERE date_joined IS NULL;
SELECT 'Updated ' || ROW_COUNT() || ' records with null date_joined' as status;

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

SELECT '🎉 WAITLIST FIX COMPLETE!' as result;
