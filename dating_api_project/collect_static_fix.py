#!/usr/bin/env python
"""
Collect Static Files Fix for Railway
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

def collect_static_fix():
    """Fix static files collection"""
    print("📁 COLLECTING STATIC FILES")
    print("=" * 50)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
    
    try:
        django.setup()
        print("✅ Django setup successful")
    except Exception as e:
        print(f"❌ Django setup failed: {str(e)}")
        return False
    
    print("\n📁 Collecting static files...")
    
    try:
        # Create staticfiles directory if it doesn't exist
        static_root = os.path.join(os.path.dirname(__file__), 'staticfiles')
        if not os.path.exists(static_root):
            os.makedirs(static_root)
            print(f"✅ Created staticfiles directory: {static_root}")
        
        # Collect static files
        execute_from_command_line(['manage.py', 'collectstatic', '--noinput', '--clear', '--settings=backend.settings_prod'])
        print("✅ Static files collected successfully")
        
        # Verify static files
        admin_css = os.path.join(static_root, 'admin', 'css', 'base.css')
        if os.path.exists(admin_css):
            print(f"✅ Admin CSS exists: {admin_css}")
        else:
            print(f"⚠️  Admin CSS not found: {admin_css}")
        
        # List some static files
        print("\n📋 Static files collected:")
        for root, dirs, files in os.walk(static_root):
            level = root.replace(static_root, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files[:5]:  # Show first 5 files
                print(f"{subindent}{file}")
            if len(files) > 5:
                print(f"{subindent}... and {len(files) - 5} more files")
        
        print("\n🎉 Static files collection completed!")
        return True
        
    except Exception as e:
        print(f"❌ Static files collection failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = collect_static_fix()
    sys.exit(0 if success else 1)
