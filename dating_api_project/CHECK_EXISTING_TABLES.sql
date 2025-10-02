-- =====================================================
-- CHECK EXISTING TABLES - Run in pgAdmin
-- =====================================================
-- This script checks what tables and columns already exist

-- Check what tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name LIKE 'dating_%'
ORDER BY table_name;

-- Check columns in usermatch table
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'dating_usermatch' 
ORDER BY column_name;

-- Check columns in locationhistory table
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'dating_locationhistory' 
ORDER BY column_name;
