#!/usr/bin/env python
"""
Check Waitlist Admin Visibility
"""
import os
import sys
import django

def check_waitlist_admin():
    """Check if waitlist entries are visible in admin"""
    print("🔍 CHECKING WAITLIST ADMIN VISIBILITY")
    print("=" * 50)
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_prod')
    django.setup()
    
    try:
        from dating.models import Waitlist
        from django.contrib import admin
        from django.contrib.admin.sites import site
        
        # Check database entries
        print("\n📋 Checking database entries...")
        waitlist_entries = Waitlist.objects.all().order_by('-date_joined')
        print(f"✅ Total waitlist entries in database: {waitlist_entries.count()}")
        
        if waitlist_entries.exists():
            print("\n📋 Recent waitlist entries:")
            for entry in waitlist_entries[:10]:
                print(f"  - ID: {entry.id}, Email: {entry.email}, Name: {entry.first_name} {entry.last_name}, Date: {entry.date_joined}")
        else:
            print("❌ No waitlist entries found in database!")
        
        # Check admin registration
        print("\n📋 Checking admin registration...")
        if Waitlist in admin.site._registry:
            print("✅ Waitlist is registered in admin")
            admin_class = admin.site._registry[Waitlist]
            print(f"✅ Admin class: {admin_class.__class__.__name__}")
            
            # Test admin queryset
            try:
                admin_queryset = admin_class.get_queryset(None)
                admin_count = admin_queryset.count()
                print(f"✅ Admin queryset count: {admin_count}")
                
                if admin_count > 0:
                    print("\n📋 Admin queryset entries:")
                    for entry in admin_queryset[:5]:
                        print(f"  - {entry}")
                else:
                    print("❌ Admin queryset is empty!")
                    
            except Exception as e:
                print(f"❌ Admin queryset error: {str(e)}")
        else:
            print("❌ Waitlist is NOT registered in admin!")
        
        # Check model fields
        print("\n📋 Checking model fields...")
        fields = [f.name for f in Waitlist._meta.fields]
        print(f"✅ Model fields: {fields}")
        
        # Check if date_joined field exists
        if 'date_joined' in fields:
            print("✅ date_joined field exists")
        else:
            print("❌ date_joined field missing!")
        
        # Test creating a new entry
        print("\n🧪 Testing new entry creation...")
        import time
        test_email = f"admin_test_{int(time.time())}@example.com"
        
        try:
            test_entry = Waitlist.objects.create(
                email=test_email,
                first_name="Admin",
                last_name="Test"
            )
            print(f"✅ Test entry created: {test_entry}")
            
            # Verify it's in database
            db_entry = Waitlist.objects.filter(email=test_email).first()
            if db_entry:
                print(f"✅ Test entry found in database: {db_entry}")
            else:
                print("❌ Test entry not found in database!")
            
            # Clean up
            test_entry.delete()
            print("✅ Test entry cleaned up")
            
        except Exception as e:
            print(f"❌ Test entry creation failed: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Final summary
        print(f"\n📊 SUMMARY:")
        print(f"  - Database entries: {Waitlist.objects.count()}")
        print(f"  - Admin registered: {Waitlist in admin.site._registry}")
        print(f"  - Model fields: {len(fields)}")
        
        if Waitlist.objects.count() > 0:
            print("✅ WAITLIST ENTRIES EXIST - They should be visible in Django admin!")
        else:
            print("❌ NO WAITLIST ENTRIES - That's why admin is empty!")
            
    except Exception as e:
        print(f"❌ Check failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_waitlist_admin()
