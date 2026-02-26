-- =====================================================
-- FIX LOCATIONHISTORY INDEX - Run in pgAdmin
-- =====================================================
-- This script fixes the index creation for the existing locationhistory table

-- First, let's check what columns exist in the locationhistory table
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'dating_locationhistory' 
ORDER BY column_name;

-- Drop the problematic index if it exists
DROP INDEX IF EXISTS idx_location_timestamp;

-- Create the correct index based on the actual column name
-- (This will be updated after we see the actual column names)
