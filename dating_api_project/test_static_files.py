#!/usr/bin/env python
"""
Test Static Files Collection and Serving
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

def test_static_files():
    """Test static files collection"""
    print("📁 TESTING STATIC FILES")
    print("=" * 50)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
    
    try:
        django.setup()
        print("✅ Django setup successful")
    except Exception as e:
        print(f"❌ Django setup failed: {str(e)}")
        return False
    
    print("\n📁 Testing static files...")
    
    try:
        # Get static root path
        from django.conf import settings
        static_root = settings.STATIC_ROOT
        static_url = settings.STATIC_URL
        
        print(f"📂 Static root: {static_root}")
        print(f"🔗 Static URL: {static_url}")
        
        # Check if staticfiles directory exists
        if os.path.exists(static_root):
            print(f"✅ Static files directory exists: {static_root}")
            
            # Count files
            file_count = 0
            for root, dirs, files in os.walk(static_root):
                file_count += len(files)
            
            print(f"📊 Total static files: {file_count}")
            
            # Check for admin files
            admin_css = os.path.join(static_root, 'admin', 'css', 'base.css')
            admin_js = os.path.join(static_root, 'admin', 'js', 'core.js')
            
            if os.path.exists(admin_css):
                print(f"✅ Admin CSS exists: {admin_css}")
            else:
                print(f"❌ Admin CSS missing: {admin_css}")
            
            if os.path.exists(admin_js):
                print(f"✅ Admin JS exists: {admin_js}")
            else:
                print(f"❌ Admin JS missing: {admin_js}")
            
            # List some admin files
            admin_dir = os.path.join(static_root, 'admin')
            if os.path.exists(admin_dir):
                print(f"\n📋 Admin static files:")
                for root, dirs, files in os.walk(admin_dir):
                    level = root.replace(admin_dir, '').count(os.sep)
                    indent = ' ' * 2 * level
                    print(f"{indent}{os.path.basename(root)}/")
                    subindent = ' ' * 2 * (level + 1)
                    for file in files[:10]:  # Show first 10 files
                        print(f"{subindent}{file}")
                    if len(files) > 10:
                        print(f"{subindent}... and {len(files) - 10} more files")
        else:
            print(f"❌ Static files directory missing: {static_root}")
            
            # Try to collect static files
            print("\n🔄 Collecting static files...")
            execute_from_command_line(['manage.py', 'collectstatic', '--noinput', '--clear', '--settings=backend.settings_prod'])
            
            if os.path.exists(static_root):
                print(f"✅ Static files collected successfully!")
            else:
                print(f"❌ Static files collection failed!")
                return False
        
        print("\n🎉 Static files test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Static files test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_static_files()
    sys.exit(0 if success else 1)
