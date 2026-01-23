# 🔧 Railway Database Fix via pgAdmin

## **Step-by-Step Instructions**

### **Step 1: Open pgAdmin**
1. Open pgAdmin 4
2. Connect to your Railway PostgreSQL database
3. Navigate to your database (usually named `railway` or similar)

### **Step 2: Open Query Tool**
1. Right-click on your database
2. Select "Query Tool"
3. This opens the SQL editor

### **Step 3: Run the Fix Script**
1. Copy the entire contents of `RAILWAY_PGADMIN_FIX.sql`
2. Paste it into the Query Tool
3. Click the "Execute" button (▶️) or press F5

### **Step 4: Verify Success**
After running the script, you should see:
- ✅ All tables created successfully
- ✅ All columns added to `dating_user` table
- ✅ No error messages

---

## **What This Script Fixes**

### **Missing Columns in `dating_user` Table:**
- ✅ `latitude` - User's latitude coordinate
- ✅ `longitude` - User's longitude coordinate  
- ✅ `address` - Full address text
- ✅ `city` - User's city
- ✅ `state` - User's state/province
- ✅ `country` - User's country
- ✅ `postal_code` - Postal/ZIP code
- ✅ `location_privacy` - Privacy setting
- ✅ `location_sharing_enabled` - Location sharing toggle
- ✅ `location_update_frequency` - Update frequency
- ✅ `is_matchmaker` - Matchmaker status
- ✅ `bio` - User biography
- ✅ `last_location_update` - Last location update time
- ✅ `max_distance` - Maximum match distance
- ✅ `age_range_min` - Minimum age preference
- ✅ `age_range_max` - Maximum age preference
- ✅ `preferred_gender` - Gender preference

### **Missing Tables:**
- ✅ `django_site` - Required for OAuth functionality
- ✅ `dating_livenessverification` - Facial verification sessions
- ✅ `dating_userverificationstatus` - User verification levels
- ✅ `dating_socialaccount` - OAuth social accounts
- ✅ `dating_deviceregistration` - Mobile device tracking
- ✅ `dating_locationhistory` - Location tracking history
- ✅ `dating_usermatch` - User matches
- ✅ `dating_locationpermission` - Location permissions

---

## **Expected Results**

### **After Running the Script:**
1. **Django Admin** will load without 500 errors
2. **All API endpoints** will work correctly
3. **Mobile app integration** will be ready
4. **Location features** will function properly
5. **Liveness verification** will work
6. **OAuth login** will work

### **Test Your Fix:**
1. Visit: `https://your-railway-domain.com/admin/`
2. Should load without errors
3. All new models should be visible in admin

---

## **If You Get Errors**

### **Common Issues:**
1. **Permission denied** - Make sure you're connected as the database owner
2. **Table already exists** - This is normal, the script uses `IF NOT EXISTS`
3. **Column already exists** - This is normal, the script uses `IF NOT EXISTS`

### **Troubleshooting:**
- Check Railway logs for any remaining errors
- Verify all tables exist by running the verification queries
- Test the Django admin interface

---

## **Success Indicators**

✅ **Django Admin loads without 500 errors**
✅ **All API endpoints respond correctly**  
✅ **User model queries work without column errors**
✅ **Liveness verification endpoints functional**
✅ **Location management endpoints working**
✅ **OAuth endpoints operational**

**Your dating app backend will be fully operational!** 🎉
