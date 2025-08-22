# Frontend Setup Guide for Bondah Dating API

## 🚨 **CRITICAL: Frontend Configuration**

### **1. API Base URL Configuration**

Your frontend needs to point to the Railway backend. Add this to your frontend environment:

```javascript
// .env file in your frontend project
VITE_API_BASE_URL=https://bondah-backend-api-production.up.railway.app
# or
REACT_APP_API_BASE_URL=https://bondah-backend-api-production.up.railway.app
```

### **2. Frontend API Configuration**

Make sure your frontend is configured to use the correct API URL:

```javascript
// In your frontend API configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://bondah-backend-api-production.up.railway.app';

// Example API call
const response = await fetch(`${API_BASE_URL}/api/jobs/apply/`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    jobId: 5,
    firstName: "John",
    lastName: "Doe",
    email: "john@example.com",
    phone: "+1234567890",
    coverLetter: "I'm excited to join the team!"
  })
});
```

### **3. CORS Issues - Quick Fix**

If you're getting CORS errors, the backend is now configured to allow these localhost ports:
- `http://localhost:3000` (React default)
- `http://localhost:3001` (React alternative)
- `http://localhost:5173` (Vite default)
- `http://localhost:8080` (Vue default)
- `http://localhost:4173` (Vite preview)
- `http://localhost:5174` (Vite alternative)
- `http://localhost:3002` (React alternative)

### **4. Testing Checklist**

Before testing, ensure:

✅ **Frontend is running on one of the allowed localhost ports**
✅ **API_BASE_URL is correctly set to Railway URL**
✅ **Request headers include 'Content-Type: application/json'**
✅ **Request body matches the expected format**

### **5. Common Issues & Solutions**

#### **Issue: CORS Error**
```
Access to fetch at 'https://bondah-backend-api-production.up.railway.app/api/jobs/apply/' from origin 'http://localhost:3000' has been blocked by CORS policy
```

**Solution**: 
- Check if your frontend port is in the allowed list above
- Ensure `CORS_ALLOW_ALL_ORIGINS=true` is set in Railway environment variables

#### **Issue: 404 Not Found**
```
GET https://bondah-backend-api-production.up.railway.app/api/jobs/apply/ 404
```

**Solution**: 
- Use POST method, not GET
- Check the API endpoint URL is correct

#### **Issue: 500 Internal Server Error**
```
POST https://bondah-backend-api-production.up.railway.app/api/jobs/apply/ 500
```

**Solution**: 
- Check request body format
- Ensure all required fields are present

### **6. Working API Endpoints**

#### **Job Application**
```javascript
POST ${API_BASE_URL}/api/jobs/apply/
Content-Type: application/json

{
  "jobId": 5,
  "firstName": "John",
  "lastName": "Doe", 
  "email": "john@example.com",
  "phone": "+1234567890",
  "coverLetter": "I'm excited to join the team!"
}
```

#### **Waitlist Signup**
```javascript
POST ${API_BASE_URL}/api/waitlist/
Content-Type: application/json

{
  "email": "user@example.com",
  "firstName": "John",
  "lastName": "Doe"
}
```

#### **Newsletter Signup**
```javascript
POST ${API_BASE_URL}/api/newsletter/subscribe/
Content-Type: application/json

{
  "email": "user@example.com",
  "name": "John Doe"
}
```

#### **Job Options (for dropdowns)**
```javascript
GET ${API_BASE_URL}/api/jobs/options/
```

### **7. Railway Environment Variables**

Make sure these are set in Railway:
```
CORS_ALLOW_ALL_ORIGINS=true
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,https://your-frontend-domain.com
```

### **8. Testing Steps**

1. **Start your frontend locally**
2. **Set the correct API_BASE_URL**
3. **Test with a simple job application**
4. **Check browser console for errors**
5. **Verify the request is reaching the backend**

### **9. Debug Information**

If you're still having issues, check:
- Browser Network tab for request/response details
- Browser Console for JavaScript errors
- Railway deployment logs for backend errors
- Frontend environment variables are loaded correctly

## 🆘 **Need Help?**

If you're still experiencing issues:
1. Share the exact error message from browser console
2. Share the Network tab request/response details
3. Confirm which localhost port your frontend is running on
4. Share your frontend API configuration code
