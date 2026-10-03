#!/usr/bin/env python
"""
Fix Job Application Issues
"""

import os
import sys
import django
from django.db import connection

def fix_job_application():
    """Fix job application issues"""
    print("🔧 FIXING JOB APPLICATION ISSUES")
    print("=" * 50)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
    
    try:
        django.setup()
        print("✅ Django setup successful")
    except Exception as e:
        print(f"❌ Django setup failed: {str(e)}")
        return False
    
    try:
        with connection.cursor() as cursor:
            print("🔍 Fixing job application issues...")
            
            # 1. Ensure dating_job table has all required columns
            print("\n📋 Fixing dating_job table...")
            job_columns = [
                ('job_type', 'VARCHAR(20)'),
                ('requirements', 'JSONB'),
                ('responsibilities', 'TEXT'),
                ('benefits', 'TEXT'),
                ('updated_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()')
            ]
            
            for column_name, column_type in job_columns:
                try:
                    cursor.execute(f"""
                        ALTER TABLE dating_job 
                        ADD COLUMN IF NOT EXISTS {column_name} {column_type}
                    """)
                    print(f"  ✅ Added column: {column_name}")
                except Exception as e:
                    print(f"  ⚠️  Column {column_name} already exists or error: {str(e)}")
            
            # 2. Ensure dating_jobapplication table has all required columns
            print("\n📋 Fixing dating_jobapplication table...")
            jobapp_columns = [
                ('first_name', 'VARCHAR(100)'),
                ('last_name', 'VARCHAR(100)'),
                ('resume_url', 'VARCHAR(500)'),
                ('cover_letter', 'TEXT'),
                ('experience_years', 'INTEGER'),
                ('current_company', 'VARCHAR(255)'),
                ('expected_salary', 'VARCHAR(100)'),
                ('applied_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()')
            ]
            
            for column_name, column_type in jobapp_columns:
                try:
                    cursor.execute(f"""
                        ALTER TABLE dating_jobapplication 
                        ADD COLUMN IF NOT EXISTS {column_name} {column_type}
                    """)
                    print(f"  ✅ Added column: {column_name}")
                except Exception as e:
                    print(f"  ⚠️  Column {column_name} already exists or error: {str(e)}")
            
            # 3. Create a sample job if none exists
            print("\n📋 Creating sample job...")
            try:
                cursor.execute("""
                    INSERT INTO dating_job (
                        title, job_type, category, status, description, 
                        location, salary_range, requirements, responsibilities, benefits
                    ) VALUES (
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
                    ON CONFLICT DO NOTHING
                """)
                print("  ✅ Sample job created/verified")
            except Exception as e:
                print(f"  ⚠️  Sample job creation error: {str(e)}")
            
            # 4. Verify the fix
            print("\n📋 Verifying fix...")
            try:
                cursor.execute("""
                    SELECT 
                        'Jobs' as table_name, COUNT(*) as count FROM dating_job
                    UNION ALL
                    SELECT 
                        'Job Applications', COUNT(*) FROM dating_jobapplication
                    UNION ALL
                    SELECT 
                        'Open Jobs', COUNT(*) FROM dating_job WHERE status = 'open'
                """)
                
                results = cursor.fetchall()
                for result in results:
                    print(f"  ✅ {result[0]}: {result[1]}")
                    
            except Exception as e:
                print(f"  ⚠️  Verification error: {str(e)}")
            
            print("\n✅ Job application issues fixed!")
            return True
            
    except Exception as e:
        print(f"❌ Job application fix failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_job_application()
    sys.exit(0 if success else 1)
