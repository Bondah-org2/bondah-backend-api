#!/usr/bin/env python
"""
Test Static Files Serving
"""

import os
import sys
import django

def test_static_serving():
    """Test if static files can be served"""
    print("🌐 TESTING STATIC FILES SERVING")
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
        from django.conf import settings
        from django.contrib.staticfiles.finders import find
        
        static_root = settings.STATIC_ROOT
        static_url = settings.STATIC_URL
        
        print(f"📂 Static root: {static_root}")
        print(f"🔗 Static URL: {static_url}")
        
        # Test if admin CSS can be found
        admin_css_path = find('admin/css/base.css')
        if admin_css_path:
            print(f"✅ Admin CSS found: {admin_css_path}")
        else:
            print("❌ Admin CSS not found by finder")
        
        # Test if admin JS can be found
        admin_js_path = find('admin/js/core.js')
        if admin_js_path:
            print(f"✅ Admin JS found: {admin_js_path}")
        else:
            print("❌ Admin JS not found by finder")
        
        # Check static files storage
        from django.contrib.staticfiles.storage import staticfiles_storage
        
        # Test if files exist in storage
        if staticfiles_storage.exists('admin/css/base.css'):
            print("✅ Admin CSS exists in storage")
        else:
            print("❌ Admin CSS not in storage")
        
        if staticfiles_storage.exists('admin/js/core.js'):
            print("✅ Admin JS exists in storage")
        else:
            print("❌ Admin JS not in storage")
        
        # Test URL generation
        try:
            css_url = staticfiles_storage.url('admin/css/base.css')
            js_url = staticfiles_storage.url('admin/js/core.js')
            print(f"✅ CSS URL: {css_url}")
            print(f"✅ JS URL: {js_url}")
        except Exception as e:
            print(f"❌ URL generation failed: {str(e)}")
        
        print("🎉 Static files serving test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Static files serving test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_static_serving()
    sys.exit(0 if success else 1)
