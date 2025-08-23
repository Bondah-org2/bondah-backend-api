# 🚨 URGENT: Railway Email Configuration Fix

## **CRITICAL ISSUE:**
The waitlist 500 error is caused by **missing email credentials** in Railway environment variables.

## **🔧 IMMEDIATE FIX:**

### **Step 1: Add Email Environment Variables to Railway**

Go to your Railway dashboard → `bondah-backend-api` service → **Variables** tab and add these:

```bash
# Email Configuration (REQUIRED)
EMAIL_HOST=mail.bondah.org
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@bondah.org
EMAIL_HOST_PASSWORD=your-email-password
DEFAULT_FROM_EMAIL=your-email@bondah.org

# CORS Fix (ALSO REQUIRED)
CORS_ALLOW_ALL_ORIGINS=true
```

### **Step 2: Get Your Email Credentials**

**If using Roundcube webmail:**
- **Email:** `your-email@bondah.org`
- **Password:** Your Roundcube webmail password
- **Host:** `mail.bondah.org`
- **Port:** `587` (TLS) or `465` (SSL)

**If using Gmail:**
- **Email:** `your-gmail@gmail.com`
- **Password:** Gmail App Password (not regular password)
- **Host:** `smtp.gmail.com`
- **Port:** `587`

### **Step 3: Test Email Configuration**

After adding the variables, Railway will automatically redeploy. Test the waitlist endpoint:

```bash
curl -X POST https://bondah-backend-api-production.up.railway.app/api/waitlist/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "firstName": "Test",
    "lastName": "User"
  }'
```

### **Step 4: Alternative - Disable Email Temporarily**

If you can't get email working immediately, we can temporarily disable email sending:

**Add this environment variable:**
```bash
DISABLE_EMAIL=true
```

This will allow the waitlist to work without sending emails.

## **📋 COMPLETE RAILWAY ENVIRONMENT VARIABLES:**

```bash
# Django Settings
SECRET_KEY=your-production-secret-key
DEBUG=False
ALLOWED_HOSTS=bondah-backend-api-production.up.railway.app

# Database (Railway provides this)
DATABASE_URL=postgresql://...

# Email Configuration (FIXES 500 ERROR)
EMAIL_HOST=mail.bondah.org
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@bondah.org
EMAIL_HOST_PASSWORD=your-email-password
DEFAULT_FROM_EMAIL=your-email@bondah.org

# CORS Settings (FIXES FRONTEND ISSUES)
CORS_ALLOW_ALL_ORIGINS=true
CORS_ALLOWED_ORIGINS=https://bondah-website-fe-production.up.railway.app,http://localhost:3000,http://localhost:5173

# Optional: Disable email temporarily
DISABLE_EMAIL=true
```

## **🚀 After Adding Email Variables:**

1. **Railway will auto-redeploy**
2. **Waitlist 500 error will be fixed**
3. **Frontend can successfully submit forms**
4. **Email confirmations will be sent**

**The main issue is missing email credentials causing the 500 error!**
