# Quick Start Guide - Mobile OAuth Integration

## ✅ System Status: READY FOR MOBILE APP

### What Was Fixed

1. **OAuth Package Updated**
   - Changed from deprecated `django-rest-auth` → `dj-rest-auth`
   - All OAuth dependencies installed and configured

2. **Migrations Completed**
   - ✅ New migration created: `0009_user_address_user_age_range_max_user_age_range_min_and_more.py`
   - ✅ All models migrated to database
   - ✅ 5 new mobile-ready models added

3. **Missing Imports Fixed**
   - Added `IsAuthenticated` to views.py

---

## 🚀 Mobile App OAuth Integration

### Google Sign-In (iOS/Android)

**Step 1: Mobile App (React Native/Flutter/Native)**
```javascript
// Get Google access token from Google Sign-In SDK
const { accessToken } = await GoogleSignin.signIn();
```

**Step 2: Send to Your Backend**
```javascript
POST https://your-domain.com/api/oauth/google/
Headers: {
  "Content-Type": "application/json"
}
Body: {
  "access_token": "google-access-token-here"
}

Response: {
  "access": "jwt-access-token",
  "refresh": "jwt-refresh-token",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

### Apple Sign-In (iOS)

**Step 1: Mobile App**
```swift
// Get Apple identity token
let appleIDCredential = authorization.credential as? ASAuthorizationAppleIDCredential
let identityToken = String(data: appleIDCredential.identityToken!, encoding: .utf8)
```

**Step 2: Send to Your Backend**
```javascript
POST https://your-domain.com/api/oauth/apple/
Body: {
  "identity_token": "apple-identity-token-here",
  "user_info": {  // Optional, only on first sign-in
    "name": "John Doe",
    "email": "user@example.com"
  }
}

Response: {
  "access": "jwt-access-token",
  "refresh": "jwt-refresh-token",
  "user": { ... }
}
```

---

## 📍 Location Services Integration

### Update User Location
```javascript
POST /api/location/update/
Headers: {
  "Authorization": "Bearer jwt-access-token"
}
Body: {
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

### Find Nearby Matches
```javascript
GET /api/matches/nearby/?distance=50
Headers: {
  "Authorization": "Bearer jwt-access-token"
}

Response: {
  "matches": [
    {
      "user_id": 2,
      "name": "Jane Doe",
      "distance": 3.5,  // km
      "match_score": 85.5
    }
  ]
}
```

---

## 📱 Device Registration (Push Notifications)

```javascript
POST /api/devices/register/
Headers: {
  "Authorization": "Bearer jwt-access-token"
}
Body: {
  "device_id": "unique-device-identifier",
  "device_type": "ios",  // or "android"
  "push_token": "fcm-or-apns-token"
}
```

---

## 🔐 JWT Token Management

### Using Access Token
```javascript
// Add to all authenticated requests
Headers: {
  "Authorization": "Bearer your-access-token"
}
```

### Refresh Token When Expired
```javascript
POST /api/token/refresh/
Body: {
  "refresh": "your-refresh-token"
}

Response: {
  "access": "new-access-token"
}
```

---

## 🔧 Environment Setup

### Required Environment Variables

Create `.env` file in `dating_api_project/`:
```env
# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Apple OAuth
APPLE_CLIENT_ID=your-apple-client-id
APPLE_SECRET=your-apple-secret
APPLE_KEY=your-apple-key

# Google Maps (for geocoding)
GOOGLE_MAPS_API_KEY=your-google-maps-api-key

# JWT
JWT_SECRET_KEY=your-super-secret-key-min-50-chars-long

# Database (for local development)
DB_NAME=bondah_db2
DB_USER=bondah_user2
DB_PASSWORD=bondahpassorg
DB_HOST=localhost
DB_PORT=5432

# Email
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com
```

---

## 📊 Available Models

### Core Models
1. **User** - Extended with location and preferences
2. **SocialAccount** - OAuth provider data
3. **DeviceRegistration** - Push notification tokens
4. **LocationHistory** - GPS tracking
5. **UserMatch** - Matching algorithm data
6. **LocationPermission** - Privacy settings

### Supporting Models
- Waitlist
- EmailLog
- Job & JobApplication
- AdminUser & AdminOTP
- TranslationLog

---

## 🧪 Testing OAuth Locally

### Test with cURL

**Google OAuth:**
```bash
curl -X POST http://localhost:8000/api/oauth/google/ \
  -H "Content-Type: application/json" \
  -d '{"access_token": "test-google-token"}'
```

**Apple OAuth:**
```bash
curl -X POST http://localhost:8000/api/oauth/apple/ \
  -H "Content-Type: application/json" \
  -d '{"identity_token": "test-apple-token"}'
```

### Run Development Server
```bash
cd dating_api_project
python manage.py runserver
```

Access at: `http://localhost:8000`

---

## 🚢 Deployment to Railway

### Before Deploying:

1. ✅ Set environment variables in Railway dashboard
2. ✅ Update `settings_prod.py` if needed
3. ✅ Run migrations on Railway: `python manage.py migrate`
4. ✅ Collect static files: `python manage.py collectstatic --noinput`

### Railway Commands:
```bash
railway login
railway link
railway up
```

---

## 📚 Additional Documentation

- `MIGRATION_SUCCESS_SUMMARY.md` - Detailed migration report
- `MOBILE_API_DOCUMENTATION.md` - Complete API reference
- `OAUTH_SETUP_GUIDE.md` - OAuth implementation details
- `LOCATION_SETUP_GUIDE.md` - Location services guide
- `RAILWAY_DEPLOYMENT.md` - Deployment guide

---

## ✅ Verification Checklist

- [x] OAuth packages installed
- [x] Migrations created and applied
- [x] Models registered in database
- [x] OAuth endpoints available
- [x] Location tracking enabled
- [x] Device registration ready
- [x] JWT authentication configured
- [x] System health check passed

---

## 🎯 Next Steps

1. **Get OAuth Credentials**
   - Google: https://console.cloud.google.com
   - Apple: https://developer.apple.com

2. **Configure Mobile App**
   - Install OAuth SDKs
   - Implement sign-in flows
   - Add location permissions

3. **Test Integration**
   - Test Google Sign-In
   - Test Apple Sign-In
   - Test location updates
   - Test push notifications

4. **Deploy**
   - Set production environment variables
   - Deploy to Railway
   - Test production endpoints

---

**Need Help?**
- Check the detailed docs in the project
- Review `MOBILE_API_DOCUMENTATION.md` for all endpoints
- See `OAUTH_SETUP_GUIDE.md` for OAuth troubleshooting

🎉 **Your system is ready for mobile app development!**

