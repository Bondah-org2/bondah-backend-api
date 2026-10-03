# 🔧 Verification Tables Setup via pgAdmin

## **Required: Create New Verification Tables**

Since we added new models for mobile app verification, you need to create the corresponding tables in your Railway PostgreSQL database.

---

## **📋 Step-by-Step Instructions**

### **Step 1: Open pgAdmin**
1. Open pgAdmin 4
2. Connect to your Railway PostgreSQL database
3. Navigate to your database

### **Step 2: Run the Verification Tables Script**
1. Right-click your database → "Query Tool"
2. Copy the entire contents of `VERIFICATION_TABLES_PGADMIN.sql`
3. Paste into Query Tool
4. Click "Execute" (▶️) or press F5

### **Step 3: Verify Success**
After running the script, you should see:
- ✅ All 10 verification tables created
- ✅ All indexes created for performance
- ✅ No error messages

---

## **📊 What This Script Creates**

### **New Verification Tables:**
- ✅ `dating_emailverification` - Email OTP verification
- ✅ `dating_phoneverification` - Phone OTP verification  
- ✅ `dating_userroleselection` - Role selection tracking
- ✅ `dating_livenessverification` - Facial verification sessions
- ✅ `dating_userverificationstatus` - Overall verification status

### **Supporting Tables:**
- ✅ `dating_socialaccount` - OAuth social accounts
- ✅ `dating_deviceregistration` - Push notification devices
- ✅ `dating_locationhistory` - Location tracking
- ✅ `dating_usermatch` - User matches
- ✅ `dating_locationpermission` - Location permissions

---

## **🎯 Expected Results**

### **After Running the Script:**
1. **All tables created** - 10 new tables in your database
2. **Indexes created** - Performance optimization
3. **Foreign key constraints** - Data integrity
4. **Check constraints** - Data validation

### **Verification Query Results:**
The script will show you a list of all created tables:
```
dating_deviceregistration
dating_emailverification
dating_livenessverification
dating_locationhistory
dating_locationpermission
dating_phoneverification
dating_socialaccount
dating_userroleselection
dating_usermatch
dating_userverificationstatus
```

---

## **🚀 After Running the Script**

### **Your Mobile App Backend Will Have:**
- ✅ **Email OTP Verification** - 4-digit codes
- ✅ **Phone OTP Verification** - SMS integration ready
- ✅ **Role Selection** - Looking for love vs Bondmaker
- ✅ **Liveness Check** - Facial verification
- ✅ **User Verification Status** - Badges and trust levels
- ✅ **OAuth Integration** - Google, Apple, Facebook
- ✅ **Device Registration** - Push notifications
- ✅ **Location Management** - GPS tracking
- ✅ **User Matching** - Dating connections

### **API Endpoints Ready:**
```
POST /api/verification/email/request/    # Request email OTP
POST /api/verification/email/verify/     # Verify email OTP
POST /api/verification/phone/request/    # Request phone OTP
POST /api/verification/phone/verify/     # Verify phone OTP
POST /api/onboarding/role/               # Role selection
POST /api/liveness/start/               # Facial verification
```

---

## **⚠️ Important Notes**

1. **Run After Previous Fix** - Make sure you've already run the `RAILWAY_PGADMIN_FIX.sql` script
2. **No Data Loss** - This script only creates new tables, doesn't modify existing ones
3. **Backup Recommended** - Always backup your database before running scripts
4. **Test After Creation** - Verify all endpoints work after running the script

---

## **✅ Success Indicators**

After running the script successfully:
- ✅ All 10 tables listed in verification query
- ✅ No error messages in pgAdmin
- ✅ Mobile app endpoints functional
- ✅ Django admin shows new models
- ✅ Railway deployment ready

**Your mobile app backend will be 100% complete and ready for production!** 🎉
