#!/usr/bin/env python
"""
Check Static Files During Build
"""

import os
import sys

def check_static_files():
    """Check if static files exist"""
    print("🔍 CHECKING STATIC FILES DURING BUILD")
    print("=" * 50)
    
    static_root = "staticfiles"
    
    if not os.path.exists(static_root):
        print(f"❌ Static files directory missing: {static_root}")
        return False
    
    print(f"✅ Static files directory exists: {static_root}")
    
    # Check admin files
    admin_css = os.path.join(static_root, "admin", "css", "base.css")
    admin_js = os.path.join(static_root, "admin", "js", "core.js")
    
    if os.path.exists(admin_css):
        print(f"✅ Admin CSS exists: {admin_css}")
    else:
        print(f"❌ Admin CSS missing: {admin_css}")
    
    if os.path.exists(admin_js):
        print(f"✅ Admin JS exists: {admin_js}")
    else:
        print(f"❌ Admin JS missing: {admin_js}")
    
    # Count total files
    file_count = 0
    for root, dirs, files in os.walk(static_root):
        file_count += len(files)
    
    print(f"📊 Total static files: {file_count}")
    
    if file_count > 0:
        print("✅ Static files check passed!")
        return True
    else:
        print("❌ No static files found!")
        return False

if __name__ == "__main__":
    success = check_static_files()
    sys.exit(0 if success else 1)
