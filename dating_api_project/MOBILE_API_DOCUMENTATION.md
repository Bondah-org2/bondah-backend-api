# 📱 **BONDAH DATING MOBILE API DOCUMENTATION**

## 🚀 **BASE URL**
```
Production: https://bondah-backend-api-production.up.railway.app/api/
Development: http://localhost:8000/api/
```

## 🔐 **AUTHENTICATION**

### **JWT Token Authentication**
All protected endpoints require a JWT token in the Authorization header:
```
Authorization: Bearer <your-access-token>
```

### **Token Structure**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

---

## 📋 **MOBILE APP ENDPOINTS**

### **1. USER AUTHENTICATION**

#### **Register User**
```http
POST /api/auth/register/
Content-Type: application/json

{
  "email": "user@example.com",
  "name": "John Doe",
  "password": "securepassword123",
  "password_confirm": "securepassword123",
  "gender": "male",
  "age": 25,
  "location": "New York"
}
```

**Response:**
```json
{
  "message": "User registered successfully",
  "status": "success",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe",
    "gender": "male",
    "age": 25,
    "location": "New York",
    "bio": "",
    "is_matchmaker": false
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }
}
```

#### **Login User**
```http
POST /api/auth/login/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "message": "Login successful",
  "status": "success",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe",
    "gender": "male",
    "age": 25,
    "location": "New York",
    "bio": "",
    "is_matchmaker": false
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }
}
```

#### **Logout User**
```http
POST /api/auth/logout/
Content-Type: application/json

{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### **Refresh Token**
```http
POST /api/auth/refresh/
Content-Type: application/json

{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### **Password Reset Request**
```http
POST /api/auth/password-reset/
Content-Type: application/json

{
  "email": "user@example.com"
}
```

#### **Password Reset Confirm**
```http
POST /api/auth/password-reset-confirm/
Content-Type: application/json

{
  "uid": "base64-encoded-user-id",
  "token": "password-reset-token",
  "new_password": "newpassword123",
  "new_password_confirm": "newpassword123"
}
```

### **2. USER PROFILE MANAGEMENT**

#### **Get User Profile**
```http
GET /api/auth/profile/
Authorization: Bearer <access-token>
```

#### **Update User Profile**
```http
PUT /api/auth/profile/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "name": "John Smith",
  "gender": "male",
  "age": 26,
  "location": "Los Angeles",
  "bio": "Love hiking and photography",
  "is_matchmaker": false
}
```

### **3. OAuth Social Login**

#### **Google OAuth Login**
```http
POST /api/oauth/google/
Content-Type: application/json

{
  "access_token": "ya29.a0AfH6SMC...",
  "id_token": "eyJhbGciOiJSUzI1NiIs..."
}
```

**Response:**
```json
{
  "message": "Google login successful",
  "status": "success",
  "user": {
    "id": 1,
    "email": "user@gmail.com",
    "name": "John Doe",
    "social_accounts": [
      {
        "id": 1,
        "provider": "google",
        "provider_user_id": "123456789",
        "is_active": true
      }
    ]
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }
}
```

#### **Apple Sign-In**
```http
POST /api/oauth/apple/
Content-Type: application/json

{
  "identity_token": "eyJhbGciOiJSUzI1NiIs...",
  "authorization_code": "c1234567890abcdef...",
  "user": {
    "name": {
      "firstName": "John",
      "lastName": "Doe"
    }
  }
}
```

#### **Unified Social Login**
```http
POST /api/oauth/social-login/
Content-Type: application/json

{
  "provider": "google",
  "google_data": {
    "access_token": "ya29.a0AfH6SMC..."
  }
}
```

#### **Link Social Account to Existing User**
```http
POST /api/oauth/link-account/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "provider": "google",
  "access_token": "ya29.a0AfH6SMC..."
}
```

#### **Unlink Social Account**
```http
DELETE /api/oauth/unlink-account/google/
Authorization: Bearer <access-token>
```

#### **List Linked Social Accounts**
```http
GET /api/oauth/social-accounts/
Authorization: Bearer <access-token>
```

### **4. LOCATION MANAGEMENT**

#### **Update User Location**
```http
POST /api/location/update/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "accuracy": 10.5,
  "source": "gps"
}
```

**Response:**
```json
{
  "message": "Location updated successfully",
  "status": "success",
  "location": {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "city": "New York",
    "state": "New York",
    "country": "United States"
  }
}
```

#### **Geocode Address to Coordinates**
```http
POST /api/location/geocode/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "address": "Times Square, New York, NY"
}
```

#### **Update Location Privacy Settings**
```http
PUT /api/location/privacy/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "location_privacy": "public",
  "location_sharing_enabled": true,
  "location_update_frequency": "manual",
  "max_distance": 25
}
```

#### **Manage Location Permissions**
```http
GET /api/location/permissions/
Authorization: Bearer <access-token>

PUT /api/location/permissions/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "location_enabled": true,
  "background_location_enabled": false,
  "precise_location_enabled": true,
  "location_services_consent": true,
  "location_data_sharing": true
}
```

#### **Get Location History**
```http
GET /api/location/history/
Authorization: Bearer <access-token>
```

#### **Find Nearby Users**
```http
GET /api/location/nearby-users/?max_distance=25
Authorization: Bearer <access-token>
```

**Response:**
```json
{
  "message": "Nearby users retrieved successfully",
  "status": "success",
  "nearby_users": [
    {
      "id": 2,
      "name": "Jane Doe",
      "age": 28,
      "gender": "female",
      "city": "New York",
      "bio": "Love hiking and photography",
      "distance": 2.5,
      "coordinates": [40.7589, -73.9851]
    }
  ],
  "count": 1
}
```

#### **Update Match Preferences**
```http
PUT /api/location/match-preferences/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "max_distance": 30,
  "age_range_min": 25,
  "age_range_max": 35,
  "preferred_gender": "female"
}
```

#### **Get User Profile with Location**
```http
GET /api/location/profile/
Authorization: Bearer <access-token>
```

### **5. DEVICE REGISTRATION**

#### **Register Device for Push Notifications**
```http
POST /api/auth/device-register/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "device_id": "unique-device-id",
  "device_type": "ios",
  "push_token": "fcm-or-apns-token"
}
```

---

## 🎯 **EXISTING ENDPOINTS (Mobile Compatible)**

### **Newsletter & Waitlist**
- `POST /api/newsletter/signup/` - Newsletter subscription
- `POST /api/waitlist/` - Join waitlist

### **Jobs & Applications**
- `GET /api/jobs/` - List available jobs
- `GET /api/jobs/<id>/` - Get job details
- `POST /api/jobs/apply/` - Apply for job

### **Translation Service**
- `POST /api/translate/` - Translate text
- `GET /api/translate/languages/` - Get supported languages

### **Gamification**
- `POST /api/puzzle/` - Get puzzle challenge
- `POST /api/puzzle/verify/` - Verify puzzle answer
- `POST /api/coins/earn/` - Earn coins
- `POST /api/coins/spend/` - Spend coins

---

## 📱 **MOBILE APP INTEGRATION GUIDE**

### **React Native Implementation Example**

```javascript
// API Configuration
const API_BASE_URL = 'https://bondah-backend-api-production.up.railway.app/api';

// Authentication Service
class AuthService {
  static async login(email, password) {
    const response = await fetch(`${API_BASE_URL}/auth/login/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });
    return response.json();
  }

  static async register(userData) {
    const response = await fetch(`${API_BASE_URL}/auth/register/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(userData),
    });
    return response.json();
  }

  static async getProfile(token) {
    const response = await fetch(`${API_BASE_URL}/auth/profile/`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });
    return response.json();
  }
}

// Usage in React Native
const handleLogin = async () => {
  try {
    const result = await AuthService.login(email, password);
    if (result.status === 'success') {
      // Store tokens securely
      await AsyncStorage.setItem('access_token', result.tokens.access);
      await AsyncStorage.setItem('refresh_token', result.tokens.refresh);
      // Navigate to main app
    }
  } catch (error) {
    console.error('Login failed:', error);
  }
};
```

### **iOS Configuration**

#### **Info.plist Settings**
```xml
<key>CFBundleURLTypes</key>
<array>
    <dict>
        <key>CFBundleURLName</key>
        <string>bondah-dating</string>
        <key>CFBundleURLSchemes</key>
        <array>
            <string>bondah</string>
        </array>
    </dict>
</array>
```

#### **App Transport Security**
```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

### **Android Configuration**

#### **Network Security Config**
```xml
<network-security-config>
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">bondah-backend-api-production.up.railway.app</domain>
    </domain-config>
</network-security-config>
```

---

## 🔧 **ERROR HANDLING**

### **Common Error Responses**

```json
{
  "message": "Authentication failed",
  "status": "error",
  "errors": {
    "email": ["This field is required."],
    "password": ["This field is required."]
  }
}
```

### **HTTP Status Codes**
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error

---

## 🚀 **DEPLOYMENT CHECKLIST**

### **Environment Variables (Railway)**
```bash
# OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
APPLE_CLIENT_ID=your-apple-client-id
APPLE_SECRET=your-apple-secret
APPLE_KEY=your-apple-key

# JWT Configuration
JWT_SECRET_KEY=your-jwt-secret-key

# Email Configuration
EMAIL_HOST=mail.bondah.org
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@bondah.org
EMAIL_HOST_PASSWORD=your-email-password
DEFAULT_FROM_EMAIL=your-email@bondah.org
```

### **Database Migrations**
```bash
python manage.py makemigrations
python manage.py migrate
```

### **Create Superuser**
```bash
python manage.py createsuperuser
```

---

## 📞 **SUPPORT**

For technical support or questions about the mobile API:
- **Email**: support@bondah.org
- **Documentation**: This file
- **API Status**: Check Railway dashboard

---

## 🔄 **VERSION HISTORY**

- **v1.0.0** - Initial mobile API implementation
- **v1.1.0** - Added OAuth integration
- **v1.2.0** - Added push notifications
- **v1.3.0** - Added dating-specific endpoints

---

*Last Updated: December 2024*
*API Version: 1.0.0*
