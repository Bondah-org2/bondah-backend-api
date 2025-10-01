# 🔐 **OAUTH SETUP GUIDE - GOOGLE & APPLE SIGN-IN**

## 📋 **OVERVIEW**

This guide will help you set up Google OAuth and Apple Sign-In for your Bondah Dating mobile app. The OAuth system is now fully implemented and ready for configuration.

---

## 🚀 **IMPLEMENTATION STATUS**

### ✅ **COMPLETED:**
- ✅ Google OAuth verification system
- ✅ Apple Sign-In verification system
- ✅ OAuth user management
- ✅ Social account linking/unlinking
- ✅ JWT token generation for OAuth users
- ✅ Complete API endpoints
- ✅ Database models for social accounts
- ✅ Error handling and validation

### 🔧 **NEEDS CONFIGURATION:**
- ⚠️ Google OAuth credentials
- ⚠️ Apple Sign-In credentials
- ⚠️ Environment variables setup

---

## 🔑 **GOOGLE OAUTH SETUP**

### **Step 1: Create Google Cloud Project**

1. **Go to [Google Cloud Console](https://console.cloud.google.com/)**
2. **Create a new project** or select existing one
3. **Enable Google+ API** (if not already enabled)

### **Step 2: Create OAuth 2.0 Credentials**

1. **Navigate to:** APIs & Services → Credentials
2. **Click:** "Create Credentials" → "OAuth 2.0 Client ID"
3. **Application Type:** Choose based on your needs:
   - **Web Application** (for testing)
   - **iOS** (for iOS app)
   - **Android** (for Android app)

### **Step 3: Configure OAuth Consent Screen**

1. **Go to:** OAuth consent screen
2. **Choose:** External (for public apps)
3. **Fill in required fields:**
   - App name: "Bondah Dating"
   - User support email: your-email@bondah.org
   - Developer contact: your-email@bondah.org

### **Step 4: Set Up Authorized Domains**

**For Web Application:**
```
Authorized JavaScript origins:
- https://bondah-backend-api-production.up.railway.app
- https://bondah.org
- https://www.bondah.org

Authorized redirect URIs:
- https://bondah-backend-api-production.up.railway.app/api/oauth/google/callback/
- https://bondah.org/oauth/callback
```

**For Mobile Apps:**
```
iOS Bundle ID: com.bondah.dating
Android Package Name: com.bondah.dating
```

### **Step 5: Get Credentials**

After creation, you'll get:
- **Client ID** (e.g., `123456789-abcdefg.apps.googleusercontent.com`)
- **Client Secret** (for web applications)

---

## 🍎 **APPLE SIGN-IN SETUP**

### **Step 1: Apple Developer Account**

1. **Go to [Apple Developer Portal](https://developer.apple.com/)**
2. **Sign in** with your Apple Developer account
3. **Navigate to:** Certificates, Identifiers & Profiles

### **Step 2: Create App ID**

1. **Go to:** Identifiers → App IDs
2. **Click:** "+" to create new App ID
3. **Configure:**
   - **Description:** Bondah Dating
   - **Bundle ID:** `com.bondah.dating`
   - **Capabilities:** Enable "Sign In with Apple"

### **Step 3: Create Service ID**

1. **Go to:** Identifiers → Services IDs
2. **Click:** "+" to create new Service ID
3. **Configure:**
   - **Description:** Bondah Dating Web
   - **Identifier:** `com.bondah.dating.web`
   - **Enable:** Sign In with Apple
   - **Configure:** Add your domain and redirect URL

### **Step 4: Create Private Key**

1. **Go to:** Keys
2. **Click:** "+" to create new key
3. **Configure:**
   - **Key Name:** Bondah Dating Sign In Key
   - **Enable:** Sign In with Apple
4. **Download:** The `.p8` key file
5. **Note:** Key ID (10-character string)

### **Step 5: Configure Domains**

**Primary App ID Domain:**
```
Domain: bondah.org
Return URLs: https://bondah.org/oauth/apple/callback
```

---

## ⚙️ **ENVIRONMENT VARIABLES SETUP**

### **Railway Environment Variables**

Add these to your Railway project:

```bash
# Google OAuth
GOOGLE_CLIENT_ID=123456789-abcdefg.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Apple Sign-In
APPLE_CLIENT_ID=com.bondah.dating
APPLE_TEAM_ID=your-10-character-team-id
APPLE_KEY_ID=your-10-character-key-id
APPLE_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----
your-private-key-content
-----END PRIVATE KEY-----

# JWT Configuration
JWT_SECRET_KEY=your-secure-jwt-secret-key-here

# Existing variables (keep these)
SECRET_KEY=your-django-secret-key
DATABASE_URL=your-railway-database-url
EMAIL_HOST=mail.bondah.org
EMAIL_HOST_USER=your-email@bondah.org
EMAIL_HOST_PASSWORD=your-email-password
```

### **Local Development (.env file)**

Create a `.env` file in your project root:

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Apple Sign-In
APPLE_CLIENT_ID=com.bondah.dating
APPLE_TEAM_ID=your-team-id
APPLE_KEY_ID=your-key-id
APPLE_PRIVATE_KEY=your-private-key

# JWT
JWT_SECRET_KEY=your-jwt-secret

# Django
SECRET_KEY=your-django-secret
DEBUG=True
```

---

## 📱 **MOBILE APP INTEGRATION**

### **React Native - Google Sign-In**

```bash
npm install @react-native-google-signin/google-signin
```

```javascript
import { GoogleSignin } from '@react-native-google-signin/google-signin';

// Configure Google Sign-In
GoogleSignin.configure({
  webClientId: 'your-google-client-id.apps.googleusercontent.com',
  offlineAccess: true,
});

// Sign in function
const signInWithGoogle = async () => {
  try {
    await GoogleSignin.hasPlayServices();
    const userInfo = await GoogleSignin.signIn();
    
    // Send to your API
    const response = await fetch(`${API_BASE}/oauth/google/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        access_token: userInfo.serverAuthCode,
        id_token: userInfo.idToken,
      }),
    });
    
    const result = await response.json();
    // Handle success
  } catch (error) {
    console.error('Google Sign-In Error:', error);
  }
};
```

### **React Native - Apple Sign-In**

```bash
npm install @invertase/react-native-apple-authentication
```

```javascript
import appleAuth from '@invertase/react-native-apple-authentication';

const signInWithApple = async () => {
  try {
    const appleAuthRequestResponse = await appleAuth.performRequest({
      requestedOperation: appleAuth.Operation.LOGIN,
      requestedScopes: [appleAuth.Scope.EMAIL, appleAuth.Scope.FULL_NAME],
    });
    
    // Send to your API
    const response = await fetch(`${API_BASE}/oauth/apple/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        identity_token: appleAuthRequestResponse.identityToken,
        authorization_code: appleAuthRequestResponse.authorizationCode,
        user: appleAuthRequestResponse.user,
      }),
    });
    
    const result = await response.json();
    // Handle success
  } catch (error) {
    console.error('Apple Sign-In Error:', error);
  }
};
```

---

## 🧪 **TESTING OAUTH**

### **Test Google OAuth**

```bash
curl -X POST https://bondah-backend-api-production.up.railway.app/api/oauth/google/ \
  -H "Content-Type: application/json" \
  -d '{
    "access_token": "your-google-access-token"
  }'
```

### **Test Apple OAuth**

```bash
curl -X POST https://bondah-backend-api-production.up.railway.app/api/oauth/apple/ \
  -H "Content-Type: application/json" \
  -d '{
    "identity_token": "your-apple-identity-token"
  }'
```

### **Test Social Login (Unified)**

```bash
curl -X POST https://bondah-backend-api-production.up.railway.app/api/oauth/social-login/ \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "google",
    "google_data": {
      "access_token": "your-google-access-token"
    }
  }'
```

---

## 📋 **API ENDPOINTS REFERENCE**

### **OAuth Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/oauth/google/` | POST | Google OAuth login |
| `/api/oauth/apple/` | POST | Apple Sign-In |
| `/api/oauth/social-login/` | POST | Unified social login |
| `/api/oauth/link-account/` | POST | Link social account |
| `/api/oauth/unlink-account/<provider>/` | DELETE | Unlink social account |
| `/api/oauth/social-accounts/` | GET | List linked accounts |

### **Request/Response Examples:**

**Google OAuth Request:**
```json
{
  "access_token": "ya29.a0AfH6SMC...",
  "id_token": "eyJhbGciOiJSUzI1NiIs..."
}
```

**Success Response:**
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

---

## 🚀 **DEPLOYMENT CHECKLIST**

### **Before Deployment:**

- [ ] Google OAuth credentials created
- [ ] Apple Sign-In credentials created
- [ ] Environment variables set in Railway
- [ ] OAuth consent screens configured
- [ ] Authorized domains set
- [ ] Database migrations run
- [ ] API endpoints tested

### **After Deployment:**

- [ ] Test OAuth flows end-to-end
- [ ] Verify JWT token generation
- [ ] Test social account linking
- [ ] Monitor error logs
- [ ] Update mobile app with credentials

---

## 🔧 **TROUBLESHOOTING**

### **Common Issues:**

**1. "Invalid OAuth client" error:**
- Check if client ID is correct
- Verify authorized domains match your app

**2. "Redirect URI mismatch" error:**
- Ensure redirect URIs are exactly configured in Google Console
- Check for trailing slashes

**3. "Apple Sign-In not working":**
- Verify bundle ID matches Apple Developer configuration
- Check if Sign In with Apple is enabled for your App ID

**4. "Token verification failed":**
- Check if JWT secret key is set correctly
- Verify token expiration times

---

## 📞 **SUPPORT**

For OAuth setup assistance:
- **Google OAuth:** [Google OAuth Documentation](https://developers.google.com/identity/protocols/oauth2)
- **Apple Sign-In:** [Apple Sign-In Documentation](https://developer.apple.com/sign-in-with-apple/)
- **API Issues:** Check Railway logs or contact support

---

*OAuth implementation completed - Ready for mobile app integration!*
