#!/usr/bin/env python
"""
Force Collect Static Files
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

def force_collect_static():
    """Force collect static files"""
    print("🔄 FORCE COLLECTING STATIC FILES")
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
        # Get static root
        from django.conf import settings
        static_root = settings.STATIC_ROOT
        print(f"📂 Static root: {static_root}")
        
        # Ensure staticfiles directory exists
        if not os.path.exists(static_root):
            os.makedirs(static_root, exist_ok=True)
            print(f"✅ Created staticfiles directory: {static_root}")
        
        # Force collect static files
        print("🔄 Collecting static files...")
        execute_from_command_line([
            'manage.py', 
            'collectstatic', 
            '--noinput', 
            '--clear', 
            '--settings=backend.settings_prod',
            '--verbosity=2'
        ])
        
        # Verify collection
        if os.path.exists(static_root):
            file_count = 0
            for root, dirs, files in os.walk(static_root):
                file_count += len(files)
            
            print(f"📊 Total static files collected: {file_count}")
            
            # Check for admin files
            admin_css = os.path.join(static_root, 'admin', 'css', 'base.css')
            admin_js = os.path.join(static_root, 'admin', 'js', 'core.js')
            
            if os.path.exists(admin_css):
                print(f"✅ Admin CSS collected: {admin_css}")
            else:
                print(f"❌ Admin CSS missing: {admin_css}")
            
            if os.path.exists(admin_js):
                print(f"✅ Admin JS collected: {admin_js}")
            else:
                print(f"❌ Admin JS missing: {admin_js}")
            
            if file_count > 0:
                print("✅ Static files collection successful!")
                return True
            else:
                print("❌ No static files collected!")
                return False
        else:
            print("❌ Static files directory not created!")
            return False
            
    except Exception as e:
        print(f"❌ Static files collection failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = force_collect_static()
    sys.exit(0 if success else 1)
