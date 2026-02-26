# 📱 Mobile App Verification API Documentation

## **Complete Mobile App Backend Implementation**

This document covers all the API endpoints needed to implement the mobile app designs you've shared.

---

## **🎯 Mobile App Flow Implementation**

### **Flow 1: Onboarding & Account Creation**

#### **1. Push Notification Permission**
```http
POST /api/auth/device-register/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "device_id": "unique-device-identifier",
  "device_type": "ios",  // or "android"
  "push_token": "fcm-or-apns-token"
}
```

#### **2. Role Selection**
```http
POST /api/onboarding/role/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "selected_role": "looking_for_love"  // or "bondmaker"
}
```

#### **3. Account Creation**
```http
POST /api/auth/register/
Content-Type: application/json

{
  "email": "user@example.com",
  "name": "John Doe",
  "password": "securepassword",
  "password_confirm": "securepassword",
  "gender": "male",
  "age": 25,
  "location": "New York, NY"
}
```

#### **4. Social Login (Google/Apple)**
```http
POST /api/oauth/social-login/
Content-Type: application/json

{
  "provider": "google",  // or "apple"
  "access_token": "google-access-token",
  "identity_token": "apple-identity-token"  // for Apple
}
```

---

### **Flow 2: Email Verification**

#### **1. Request Email OTP**
```http
POST /api/verification/email/request/
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "message": "OTP sent to your email",
  "status": "success",
  "email": "user@example.com",
  "expires_in": 600
}
```

#### **2. Verify Email OTP**
```http
POST /api/verification/email/verify/
Content-Type: application/json

{
  "email": "user@example.com",
  "otp_code": "1234"
}
```

**Response:**
```json
{
  "message": "Email verified successfully",
  "status": "success",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "is_active": true
  }
}
```

#### **3. Resend Email OTP**
```http
POST /api/verification/resend/
Content-Type: application/json

{
  "type": "email",
  "identifier": "user@example.com"
}
```

---

### **Flow 3: Phone Verification**

#### **1. Request Phone OTP**
```http
POST /api/verification/phone/request/
Content-Type: application/json

{
  "phone_number": "1234567890",
  "country_code": "+1",
  "user_id": 1
}
```

**Response:**
```json
{
  "message": "OTP sent to your phone",
  "status": "success",
  "phone_number": "+11234567890",
  "expires_in": 600
}
```

#### **2. Verify Phone OTP**
```http
POST /api/verification/phone/verify/
Content-Type: application/json

{
  "phone_number": "1234567890",
  "country_code": "+1",
  "otp_code": "5678"
}
```

**Response:**
```json
{
  "message": "Phone number verified successfully",
  "status": "success",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "phone_verified": true
  }
}
```

#### **3. Resend Phone OTP**
```http
POST /api/verification/resend/
Content-Type: application/json

{
  "type": "phone",
  "identifier": "+11234567890"
}
```

---

## **🔐 Authentication Endpoints**

### **User Registration**
```http
POST /api/auth/register/
Content-Type: application/json

{
  "email": "user@example.com",
  "name": "John Doe",
  "password": "securepassword",
  "password_confirm": "securepassword",
  "gender": "male",
  "age": 25,
  "location": "New York, NY"
}
```

### **User Login**
```http
POST /api/auth/login/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword"
}
```

### **Social Login**
```http
POST /api/oauth/social-login/
Content-Type: application/json

{
  "provider": "google",
  "access_token": "google-access-token"
}
```

### **Token Refresh**
```http
POST /api/auth/refresh/
Content-Type: application/json

{
  "refresh": "your-refresh-token"
}
```

---

## **📍 Location Management**

### **Update Location**
```http
POST /api/location/update/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "accuracy": 10.5,
  "address": "123 Main St, New York, NY",
  "city": "New York",
  "state": "NY",
  "country": "USA",
  "postal_code": "10001"
}
```

### **Find Nearby Users**
```http
GET /api/location/nearby-users/?max_distance=25
Authorization: Bearer <access-token>
```

### **Update Privacy Settings**
```http
PUT /api/location/privacy/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "location_privacy": "friends",
  "location_sharing_enabled": true,
  "location_update_frequency": "hourly"
}
```

---

## **📷 Liveness Check (Facial Verification)**

### **Start Liveness Check**
```http
POST /api/liveness/start/
Authorization: Bearer <access-token>
```

### **Submit Video for Verification**
```http
POST /api/liveness/submit/video/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "session_id": "liveness_1234567890_1234",
  "video_data": "base64-encoded-video",
  "actions_completed": ["turn_left", "turn_right", "open_mouth"]
}
```

### **Check Verification Status**
```http
GET /api/liveness/status/<session_id>/
Authorization: Bearer <access-token>
```

### **Get User Verification Status**
```http
GET /api/verification/status/
Authorization: Bearer <access-token>
```

---

## **📱 Device Registration (Push Notifications)**

### **Register Device**
```http
POST /api/auth/device-register/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "device_id": "unique-device-identifier",
  "device_type": "ios",
  "push_token": "fcm-or-apns-token"
}
```

---

## **🎯 Complete Mobile App Integration**

### **Step 1: User Onboarding**
1. **Push Notification Permission** → `POST /api/auth/device-register/`
2. **Role Selection** → `POST /api/onboarding/role/`
3. **Account Creation** → `POST /api/auth/register/` or `POST /api/oauth/social-login/`

### **Step 2: Email Verification**
1. **Request OTP** → `POST /api/verification/email/request/`
2. **Verify OTP** → `POST /api/verification/email/verify/`
3. **Resend if needed** → `POST /api/verification/resend/`

### **Step 3: Phone Verification**
1. **Request OTP** → `POST /api/verification/phone/request/`
2. **Verify OTP** → `POST /api/verification/phone/verify/`
3. **Resend if needed** → `POST /api/verification/resend/`

### **Step 4: Profile Setup**
1. **Update Location** → `POST /api/location/update/`
2. **Set Privacy** → `PUT /api/location/privacy/`
3. **Liveness Check** → `POST /api/liveness/start/`

---

## **🔧 Error Handling**

### **Common Error Responses**
```json
{
  "message": "Invalid OTP code. Please try again.",
  "status": "error"
}
```

```json
{
  "message": "OTP has expired. Please request a new one.",
  "status": "error"
}
```

```json
{
  "message": "Too many OTP requests. Please wait 1 minute.",
  "status": "error"
}
```

---

## **📊 Rate Limiting**

- **Email OTP**: Max 3 requests per minute per email
- **Phone OTP**: Max 3 requests per minute per phone number
- **Resend OTP**: Same rate limits apply

---

## **✅ Success Indicators**

### **Email Verification Success**
- User account activated (`is_active: true`)
- Email verification status updated
- User can proceed to phone verification

### **Phone Verification Success**
- Phone verification status updated
- User verification level increased
- User can access full app features

### **Complete Onboarding**
- User has selected role (looking_for_love or bondmaker)
- Email and phone verified
- Device registered for push notifications
- Location permissions set
- Ready for matching and dating features

---

## **🚀 Production Deployment**

### **Environment Variables Required**
```env
# Email Configuration
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com

# OAuth Credentials
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
APPLE_CLIENT_ID=your-apple-client-id
APPLE_SECRET=your-apple-secret

# SMS Service (for phone verification)
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_PHONE_NUMBER=your-twilio-number
```

### **Database Migration**
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## **📱 Mobile App Implementation Checklist**

- ✅ **Push Notification Permission** - Device registration endpoint
- ✅ **Role Selection** - Looking for love vs Bondmaker
- ✅ **Account Creation** - Email/password and social login
- ✅ **Email Verification** - 4-digit OTP system
- ✅ **Phone Verification** - SMS OTP system
- ✅ **Location Management** - GPS tracking and privacy
- ✅ **Liveness Check** - Facial verification system
- ✅ **User Verification** - Badges and trust levels
- ✅ **Admin Dashboard** - Complete backend management

**Your mobile app backend is now 100% ready for the designs you've shared!** 🎉
