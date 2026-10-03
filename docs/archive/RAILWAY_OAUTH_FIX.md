# 🚨 Railway OAuth Deployment Fix

## Problem Identified

Railway deployment failing with:
```
ModuleNotFoundError: No module named 'rest_auth'
```

## Root Cause

Railway was deploying **OLD CODE** that still referenced the deprecated `django-rest-auth` package. The local fixes weren't pushed to production.

---

## ✅ Files Fixed (Ready to Deploy)

### 1. `requirements.txt` ✅
**Changed:**
```diff
- django-rest-auth==0.9.5
+ dj-rest-auth==5.0.2
```

### 2. `backend/settings.py` ✅
**Changed:**
```diff
INSTALLED_APPS = [
    ...
-   'rest_auth',
-   'rest_auth.registration',
+   'rest_framework.authtoken',
+   'dj_rest_auth',
+   'dj_rest_auth.registration',
]
```

### 3. `backend/settings_prod.py` ✅ **NEW FIX!**
**Changed:**
```diff
INSTALLED_APPS = [
    ...
-   'rest_auth',
-   'rest_auth.registration',
+   'rest_framework.authtoken',
+   'dj_rest_auth',
+   'dj_rest_auth.registration',
]
```

### 4. `dating/views.py` ✅
**Changed:**
```diff
- from rest_framework.permissions import AllowAny
+ from rest_framework.permissions import AllowAny, IsAuthenticated
```

---

## 🚀 Deployment Steps

### Step 1: Commit Changes to Git

```bash
# Navigate to project directory
cd dating_api_project

# Check what changed
git status

# Add all changes
git add .

# Commit with descriptive message
git commit -m "Fix: Update to dj-rest-auth for Railway OAuth deployment

- Replace deprecated django-rest-auth with dj-rest-auth
- Update both settings.py and settings_prod.py
- Add rest_framework.authtoken to INSTALLED_APPS
- Fix missing IsAuthenticated import in views.py
- Create OAuth/Mobile models with migration 0009"

# Push to GitHub (Railway will auto-deploy)
git push origin main
```

### Step 2: Verify Railway Auto-Deploy

1. **Go to Railway Dashboard**
2. **Check Deployment Logs**
3. **Look for:**
   ```
   ✅ Installing dependencies...
   ✅ Collecting dj-rest-auth==5.0.2
   ✅ Successfully installed dj-rest-auth-5.0.2
   ✅ Starting gunicorn...
   ✅ Booting worker with pid: X
   ```

### Step 3: Run Migrations on Railway

After successful deployment:

**Option A: Via Railway Dashboard**
1. Go to your Django service
2. Click on "Settings" → "Deploy"
3. Add this to deploy command or run in shell:
   ```bash
   python manage.py migrate
   ```

**Option B: Via Railway Shell**
1. Click on your service
2. Go to "..." → "Shell"
3. Run:
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```

### Step 4: Test OAuth Endpoints

```bash
# Test health check
curl https://your-app.railway.app/health/

# Test API root
curl https://your-app.railway.app/api/

# Test OAuth endpoint (should return 400/401, not 500)
curl -X POST https://your-app.railway.app/api/oauth/google/ \
  -H "Content-Type: application/json" \
  -d '{"access_token": "test"}'
```

---

## 🔍 Troubleshooting

### Issue: Still getting "No module named 'rest_auth'"

**Solution:**
1. Check if you pushed to the correct branch
2. Verify Railway is deploying from `main` branch
3. Check Railway environment variable: `DJANGO_SETTINGS_MODULE`
   - Should be: `backend.settings` or `backend.settings_prod`

### Issue: Deployment succeeds but OAuth fails

**Solution:**
1. Check Railway environment variables:
   ```
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   APPLE_CLIENT_ID=your-apple-client-id
   ```

2. Run migrations:
   ```bash
   python manage.py migrate
   ```

### Issue: Static files not loading

**Solution:**
```bash
python manage.py collectstatic --noinput
```

---

## 📋 Railway Environment Variables Checklist

Make sure these are set in Railway Dashboard:

### Required:
- [x] `DATABASE_URL` (auto-set by Railway)
- [ ] `SECRET_KEY` (Django secret key)
- [ ] `DJANGO_SETTINGS_MODULE=backend.settings_prod`
- [ ] `ALLOWED_HOSTS` (your-app.railway.app)

### OAuth Credentials:
- [ ] `GOOGLE_CLIENT_ID`
- [ ] `GOOGLE_CLIENT_SECRET`
- [ ] `APPLE_CLIENT_ID`
- [ ] `APPLE_SECRET`
- [ ] `APPLE_KEY`

### Email (Optional):
- [ ] `EMAIL_HOST_USER`
- [ ] `EMAIL_HOST_PASSWORD`
- [ ] `DEFAULT_FROM_EMAIL`

### JWT (Recommended):
- [ ] `JWT_SECRET_KEY` (long random string)

---

## 🎯 Quick Deploy Checklist

- [ ] 1. All files updated locally
- [ ] 2. Changes committed to Git
- [ ] 3. Pushed to GitHub main branch
- [ ] 4. Railway auto-deployed successfully
- [ ] 5. No "rest_auth" errors in logs
- [ ] 6. Migrations applied on Railway
- [ ] 7. Static files collected
- [ ] 8. OAuth endpoints accessible
- [ ] 9. Health check returns 200
- [ ] 10. Database tables verified

---

## 🔐 Security Note

After deployment, update these in Railway:
```bash
# Generate a secure Django secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Generate a secure JWT secret key (50+ characters)
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Set in Railway:
- `SECRET_KEY=<django-secret-key>`
- `JWT_SECRET_KEY=<jwt-secret-key>`

---

## ✅ Expected Result

After successful deployment, you should see:

### Railway Logs:
```
[INFO] Starting gunicorn 21.2.0
[INFO] Listening at: http://0.0.0.0:8080
[INFO] Using worker: sync
[INFO] Booting worker with pid: 4
✅ NO ERRORS - Worker started successfully
```

### API Test:
```bash
curl https://your-app.railway.app/health/
{
  "status": "healthy",
  "message": "Bondah Dating API is running",
  "version": "1.0.0"
}
```

---

## 📚 Related Documentation

- `MIGRATION_SUCCESS_SUMMARY.md` - What was fixed locally
- `PGADMIN_RAILWAY_SETUP.md` - Database management
- `QUICK_START_MOBILE.md` - OAuth integration guide
- `RAILWAY_DEPLOYMENT.md` - General deployment guide

---

## 🆘 If All Else Fails

1. **Check Railway Logs** for exact error
2. **Verify Git push** was successful
3. **Check Railway is deploying** from correct branch
4. **Try manual redeploy** in Railway dashboard
5. **Check requirements.txt** is in repository root
6. **Verify Python version** matches runtime.txt

---

**Last Updated:** October 1, 2025  
**Status:** Ready to deploy ✅

