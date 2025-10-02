# 🔧 Advanced Profile Tables Setup via pgAdmin

## **Required: Create Advanced Profile Tables**

Since we added extensive new models and extended the User model with 25+ new fields for the advanced profile features, you need to create the corresponding tables in your Railway PostgreSQL database.

---

## **📋 Step-by-Step Instructions**

### **Step 1: Open pgAdmin**
1. Open pgAdmin 4
2. Connect to your Railway PostgreSQL database
3. Navigate to your database

### **Step 2: Run the Advanced Profile Tables Script**
1. Right-click your database → "Query Tool"
2. Copy the **entire contents** of `ADVANCED_PROFILE_TABLES_PGADMIN.sql`
3. Paste into Query Tool
4. Click "Execute" (▶️) or press F5

### **Step 3: Verify Success**
After running the script, you should see:
- ✅ All 5 new tables created
- ✅ All 23 new user columns added
- ✅ All constraints and indexes created
- ✅ Sample interests data inserted
- ✅ No error messages

---

## **📊 What This Script Creates**

### **New Tables:**
- ✅ `dating_userinterest` - Interest categories (Sports, Music, Travel, etc.)
- ✅ `dating_userprofileview` - Profile view tracking and analytics
- ✅ `dating_userinteraction` - User interactions (Like, Dislike, Request Live, etc.)
- ✅ `dating_searchquery` - Search analytics and query tracking
- ✅ `dating_recommendationengine` - Personalized recommendation system

### **Extended User Table (23 New Columns):**
- ✅ **Profile Pictures**: `profile_picture`, `profile_gallery`
- ✅ **Personal Info**: `education_level`, `height`, `zodiac_sign`, `languages`, `relationship_status`
- ✅ **Lifestyle**: `smoking_preference`, `drinking_preference`, `pet_preference`, `exercise_frequency`, `kids_preference`
- ✅ **Personality**: `personality_type`, `love_language`, `communication_style`
- ✅ **Interests**: `hobbies`, `interests`
- ✅ **Future Plans**: `marriage_plans`, `kids_plans`, `religion_importance`, `religion`
- ✅ **Dating Preferences**: `dating_type`, `open_to_long_distance`

### **Data Integrity:**
- ✅ **Check Constraints** - Validates all choice fields
- ✅ **Foreign Keys** - Ensures data integrity
- ✅ **Indexes** - Optimizes query performance
- ✅ **Sample Data** - Pre-populated interest categories

---

## **🎯 Expected Results**

### **After Running the Script:**
1. **All 5 tables created** - New advanced functionality
2. **All 23 user columns added** - Complete profile information
3. **All constraints created** - Data validation
4. **All indexes created** - Performance optimization
5. **Sample interests inserted** - Ready-to-use interest categories

### **Verification Query Results:**
The script will show you:

**Tables Created:**
```
dating_userinterest
dating_userprofileview
dating_userinteraction
dating_searchquery
dating_recommendationengine
```

**User Columns Added:**
```
communication_style, dating_type, drinking_preference, education_level, 
exercise_frequency, height, hobbies, interests, kids_plans, kids_preference, 
languages, love_language, marriage_plans, open_to_long_distance, 
personality_type, pet_preference, profile_gallery, profile_picture, 
religion, religion_importance, relationship_status, smoking_preference, 
zodiac_sign
```

---

## **🚀 After Running the Script**

### **Your Mobile App Backend Will Have:**
- ✅ **Complete User Profiles** - All personal information fields from Figma
- ✅ **Advanced Search** - 20+ filtering options
- ✅ **Category Filtering** - Casual Dating, LGBTQ+, Sugar, etc.
- ✅ **User Interactions** - Like, dislike, request live, share, report
- ✅ **Recommendation Engine** - Personalized matching
- ✅ **Profile Analytics** - View tracking and insights
- ✅ **Interest System** - Pre-populated categories
- ✅ **Profile Gallery** - Multiple photo support

### **API Endpoints Ready:**
```
GET /api/search/users/                    # Advanced user search
GET /api/users/category/                  # Category filtering
GET /api/users/recommendations/           # Personalized recommendations
GET /api/users/<user_id>/profile/         # Detailed profile viewing
POST /api/users/interact/                 # User interactions
GET /api/users/interests/                 # Manage interests
```

---

## **⚠️ Important Notes**

1. **Run After Previous Fixes** - Make sure you've already run the previous database fix scripts
2. **No Data Loss** - This script only adds new columns and tables, doesn't modify existing data
3. **Backup Recommended** - Always backup your database before running scripts
4. **Test After Creation** - Verify all endpoints work after running the script

---

## **✅ Success Indicators**

After running the script successfully:
- ✅ All 5 tables listed in verification query
- ✅ All 23 user columns listed in verification query
- ✅ No error messages in pgAdmin
- ✅ Mobile app endpoints functional
- ✅ Django admin shows new models
- ✅ Railway deployment ready

**Your mobile app backend will be 100% complete with all Figma design features!** 🎉

---

## **🔧 Troubleshooting**

### **If you get errors:**
1. **Check previous scripts** - Make sure you ran the verification tables script first
2. **Check permissions** - Ensure you have ALTER TABLE permissions
3. **Check constraints** - Some constraints might conflict if columns already exist
4. **Check data types** - Ensure JSONB is supported in your PostgreSQL version

### **If columns already exist:**
- The script uses `ADD COLUMN IF NOT EXISTS` so it should skip existing columns
- If you get constraint errors, the columns might exist but without constraints

**Your advanced profile system is now ready for production!** 🚀
