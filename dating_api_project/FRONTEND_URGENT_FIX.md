# 🚨 URGENT: Frontend API Configuration Fix

## **CRITICAL ISSUES FOUND:**

From the Railway HTTP logs, your frontend is calling **WRONG API endpoints**:

❌ **Wrong:** `/translate/languages/` → **Correct:** `/api/translate/languages/`
❌ **Wrong:** `/newsletter/subscribe/` → **Correct:** `/api/newsletter/subscribe/`
❌ **Wrong:** `/jobs/` → **Correct:** `/api/jobs/`

## **🔧 IMMEDIATE FIXES:**

### **1. Update Your API Base URL**

**In your frontend `.env` file:**
```bash
VITE_API_BASE_URL=https://bondah-backend-api-production.up.railway.app
```

**In your API configuration:**
```javascript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://bondah-backend-api-production.up.railway.app';
```

### **2. Fix All API Endpoints**

**Replace your current API calls with these CORRECT ones:**

```javascript
// ✅ CORRECT API ENDPOINTS
const API_ENDPOINTS = {
  // Waitlist
  waitlist: `${API_BASE_URL}/api/waitlist/`,
  
  // Newsletter
  newsletter: `${API_BASE_URL}/api/newsletter/subscribe/`,
  
  // Jobs
  jobs: `${API_BASE_URL}/api/jobs/`,
  jobOptions: `${API_BASE_URL}/api/jobs/options/`,
  jobApply: `${API_BASE_URL}/api/jobs/apply/`,
  
  // Translation
  translateLanguages: `${API_BASE_URL}/api/translate/languages/`,
  translate: `${API_BASE_URL}/api/translate/`,
  
  // Admin
  adminLogin: `${API_BASE_URL}/api/admin/login/`,
  adminVerifyOTP: `${API_BASE_URL}/api/admin/verify-otp/`,
  
  // Health check
  health: `${API_BASE_URL}/health/`
};
```

### **3. Example API Calls**

**Waitlist Signup:**
```javascript
const joinWaitlist = async (data) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/waitlist/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: data.email,
        firstName: data.firstName,
        lastName: data.lastName
      })
    });
    return await response.json();
  } catch (error) {
    console.error('Waitlist error:', error);
    throw error;
  }
};
```

**Newsletter Signup:**
```javascript
const subscribeNewsletter = async (data) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/newsletter/subscribe/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: data.email,
        name: data.name
      })
    });
    return await response.json();
  } catch (error) {
    console.error('Newsletter error:', error);
    throw error;
  }
};
```

**Get Translation Languages:**
```javascript
const getLanguages = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/translate/languages/`);
    return await response.json();
  } catch (error) {
    console.error('Languages error:', error);
    throw error;
  }
};
```

**Job Application:**
```javascript
const applyForJob = async (data) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/jobs/apply/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jobId: data.jobId,
        firstName: data.firstName,
        lastName: data.lastName,
        email: data.email,
        phone: data.phone,
        coverLetter: data.coverLetter
      })
    });
    return await response.json();
  } catch (error) {
    console.error('Job application error:', error);
    throw error;
  }
};
```

### **4. Test Your Fixes**

**Add this test function to your browser console:**

```javascript
const testAllEndpoints = async () => {
  console.log('🧪 Testing all API endpoints...');
  
  const endpoints = [
    { name: 'Health Check', url: `${API_BASE_URL}/health/`, method: 'GET' },
    { name: 'Job Options', url: `${API_BASE_URL}/api/jobs/options/`, method: 'GET' },
    { name: 'Translation Languages', url: `${API_BASE_URL}/api/translate/languages/`, method: 'GET' }
  ];
  
  for (const endpoint of endpoints) {
    try {
      const response = await fetch(endpoint.url, { method: endpoint.method });
      console.log(`✅ ${endpoint.name}: ${response.status} ${response.statusText}`);
    } catch (error) {
      console.error(`❌ ${endpoint.name}: ${error.message}`);
    }
  }
};

// Run the test
testAllEndpoints();
```

### **5. Common Issues & Solutions**

**Issue: CORS Error**
```
Access to fetch at 'https://bondah-backend-api-production.up.railway.app/api/waitlist/' 
from origin 'https://bondah-website-fe-production.up.railway.app' has been blocked by CORS policy
```

**Solution:** The backend has been updated to allow your domain. If you still get CORS errors, check that you're using the correct API_BASE_URL.

**Issue: 404 Not Found**
```
GET https://bondah-backend-api-production.up.railway.app/translate/languages/ 404
```

**Solution:** Add `/api/` prefix to all your API calls.

**Issue: 500 Internal Server Error**
```
POST https://bondah-backend-api-production.up.railway.app/api/waitlist/ 500
```

**Solution:** This might be an email configuration issue. The backend team is investigating.

### **6. Quick Verification**

**Test these URLs in your browser:**

✅ **Health Check:** https://bondah-backend-api-production.up.railway.app/health/
✅ **Job Options:** https://bondah-backend-api-production.up.railway.app/api/jobs/options/
✅ **Translation Languages:** https://bondah-backend-api-production.up.railway.app/api/translate/languages/

All should return JSON responses, not 404 errors.

## **🚀 After Making These Changes:**

1. **Update your API configuration**
2. **Test the endpoints in browser console**
3. **Deploy your updated frontend**
4. **Test all functionality**

**The main issue is the missing `/api/` prefix in your API calls!**
