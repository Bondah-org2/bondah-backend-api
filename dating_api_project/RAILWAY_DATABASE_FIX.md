# 🚨 Railway Database Fix Guide

## **Critical Issues Identified**

### **Problem 1: Missing User Model Columns**
```
psycopg2.errors.UndefinedColumn: column dating_user.latitude does not exist
```

**Missing columns in `dating_user` table:**
- `latitude` (DECIMAL)
- `longitude` (DECIMAL) 
- `address` (TEXT)
- `city` (VARCHAR)
- `state` (VARCHAR)
- `country` (VARCHAR)
- `postal_code` (VARCHAR)
- `location_privacy` (VARCHAR)
- `location_sharing_enabled` (BOOLEAN)
- `location_update_frequency` (VARCHAR)
- `is_matchmaker` (BOOLEAN)
- `bio` (TEXT)
- `last_location_update` (TIMESTAMP)
- `max_distance` (INTEGER)
- `age_range_min` (INTEGER)
- `age_range_max` (INTEGER)
- `preferred_gender` (VARCHAR)

### **Problem 2: Missing Django Site Table**
```
django.db.utils.ProgrammingError: relation "django_site" does not exist
```

---

## 🔧 **Solution: Database Schema Fix**

### **Step 1: Run Database Fix Script on Railway**

1. **Access Railway Shell:**
   ```bash
   # In Railway dashboard, go to your service
   # Click on "Deploy Logs" tab
   # Click "Open Shell" or use Railway CLI
   ```

2. **Run the Database Fix Script:**
   ```bash
   # Navigate to your project directory
   cd /app
   
   # Run the database schema fix
   python fix_railway_database_schema.py
   ```

### **Step 2: Apply Django Migrations**

```bash
# Apply all migrations
python manage.py migrate

# Specifically apply the liveness verification migration
python manage.py migrate dating 0010

# Verify migrations are applied
python manage.py showmigrations dating
```

### **Step 3: Create Superuser (if needed)**

```bash
# Create superuser for Django admin access
python manage.py createsuperuser
```

---

## 📋 **What the Fix Script Does**

### **User Model Columns Added:**
- ✅ `latitude` - User's latitude coordinate
- ✅ `longitude` - User's longitude coordinate  
- ✅ `address` - Full address text
- ✅ `city` - User's city
- ✅ `state` - User's state/province
- ✅ `country` - User's country
- ✅ `postal_code` - Postal/ZIP code
- ✅ `location_privacy` - Privacy setting (public/friends/private/hidden)
- ✅ `location_sharing_enabled` - Whether location sharing is enabled
- ✅ `location_update_frequency` - How often to update location
- ✅ `is_matchmaker` - Whether user is a matchmaker
- ✅ `bio` - User biography
- ✅ `last_location_update` - Last time location was updated
- ✅ `max_distance` - Maximum distance for matches (km)
- ✅ `age_range_min` - Minimum age preference
- ✅ `age_range_max` - Maximum age preference
- ✅ `preferred_gender` - Gender preference for matches

### **Django Site Table:**
- ✅ Creates `django_site` table
- ✅ Inserts default site: `bondah.org`

---

## 🎯 **Expected Results After Fix**

### **Django Admin Access:**
- ✅ `/admin/` - Main admin dashboard
- ✅ `/admin/dating/user/` - User management
- ✅ `/admin/dating/livenessverification/` - Liveness checks
- ✅ `/admin/dating/userverificationstatus/` - Verification status
- ✅ `/admin/dating/socialaccount/` - OAuth accounts
- ✅ `/admin/dating/deviceregistration/` - Device registrations
- ✅ `/admin/dating/locationhistory/` - Location tracking
- ✅ `/admin/dating/usermatch/` - User matches
- ✅ `/admin/dating/locationpermission/` - Location permissions

### **API Endpoints Working:**
- ✅ All authentication endpoints
- ✅ All location management endpoints  
- ✅ All liveness check endpoints
- ✅ All OAuth endpoints
- ✅ All device registration endpoints

---

## 🚀 **Deployment Commands**

### **If using Railway CLI:**
```bash
# Deploy the fix
railway up

# Run migrations on Railway
railway run python manage.py migrate

# Run database fix script
railway run python fix_railway_database_schema.py
```

### **If using Git deployment:**
```bash
# Commit and push changes
git add .
git commit -m "Fix Railway database schema - add missing columns and tables"
git push origin main

# Railway will auto-deploy, then run:
# 1. python manage.py migrate
# 2. python fix_railway_database_schema.py
```

---

## 🧪 **Testing After Fix**

### **1. Test Django Admin:**
```bash
# Visit: https://your-railway-domain.com/admin/
# Should load without 500 errors
```

### **2. Test API Endpoints:**
```bash
# Test health check
curl https://your-railway-domain.com/health/

# Test liveness check (requires auth)
curl -X POST https://your-railway-domain.com/api/liveness/start/ \
  -H "Authorization: Bearer <token>"
```

### **3. Verify Database Schema:**
```bash
# Check if columns exist
python manage.py dbshell
# Then run: \d dating_user
```

---

## 📊 **Admin Interface Features**

### **User Management:**
- View all users with location data
- Filter by matchmaker status
- Search by email/name
- View user verification status

### **Liveness Verification:**
- Monitor verification sessions
- View verification results
- Track confidence scores
- Manage failed verifications

### **Location Management:**
- Track user locations
- Monitor location history
- Manage location permissions
- View user matches

### **OAuth Management:**
- Monitor social logins
- Track device registrations
- Manage social accounts

---

## ⚠️ **Important Notes**

1. **Backup First:** Always backup your Railway database before running fixes
2. **Test Locally:** Test the fix script locally first if possible
3. **Monitor Logs:** Watch Railway logs during the fix process
4. **Verify Results:** Test all endpoints after the fix

---

## 🆘 **If Issues Persist**

### **Check Railway Logs:**
```bash
# In Railway dashboard, check:
# 1. Build Logs
# 2. Deploy Logs  
# 3. HTTP Logs
```

### **Manual Database Fix:**
If the script fails, you can manually run SQL commands in Railway's database console:

```sql
-- Add missing columns one by one
ALTER TABLE dating_user ADD COLUMN latitude DECIMAL(10,8) NULL;
ALTER TABLE dating_user ADD COLUMN longitude DECIMAL(11,8) NULL;
-- ... continue for all missing columns
```

---

## ✅ **Success Indicators**

- ✅ Django admin loads without 500 errors
- ✅ All API endpoints respond correctly
- ✅ User model queries work without column errors
- ✅ Liveness verification endpoints functional
- ✅ Location management endpoints working
- ✅ OAuth endpoints operational

**The system will be fully operational for mobile app integration!** 🎉
