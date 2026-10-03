# 📚 Bondah Dating API - Comprehensive Documentation

## 🚀 Quick Access

- **Swagger UI**: https://bondah-backend-api-production.up.railway.app/api/docs/
- **ReDoc**: https://bondah-backend-api-production.up.railway.app/api/redoc/
- **OpenAPI Schema**: https://bondah-backend-api-production.up.railway.app/api/schema/

## 📋 Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Base URLs](#base-urls)
4. [API Endpoints](#api-endpoints)
   - [Authentication & User Management](#authentication--user-management)
   - [Chat & Messaging](#chat--messaging)
   - [Social Feed & Stories](#social-feed--stories)
   - [Live Streaming](#live-streaming)
   - [Matching & Discovery](#matching--discovery)
   - [Location Services](#location-services)
   - [Monetization & Payments](#monetization--payments)
   - [Virtual Gifting](#virtual-gifting)
   - [Verification & Security](#verification--security)
   - [Admin & Management](#admin--management)
   - [Translation Services](#translation-services)
5. [Response Formats](#response-formats)
6. [Error Handling](#error-handling)
7. [Rate Limiting](#rate-limiting)
8. [SDK & Examples](#sdk--examples)

---

## 🎯 Overview

The Bondah Dating API is a comprehensive platform that provides all the backend functionality for a modern dating application. It includes advanced features like real-time chat, live streaming, virtual gifting, AI-powered matching, and more.

### Key Features
- 🔐 **Multi-factor Authentication** (JWT, OAuth, Social Login)
- 💬 **Real-time Communication** (Chat, Voice/Video Calls)
- 📱 **Social Features** (Feed, Stories, Posts, Comments)
- 🎥 **Live Streaming** (Sessions, Audience Interaction)
- 🎁 **Monetization** (Subscriptions, Virtual Gifts, Bondcoins)
- 📍 **Location Services** (GPS, Nearby Users, Geo-matching)
- 🔒 **Security** (Document Verification, Facial Recognition)
- 🎯 **AI Matching** (Smart Recommendations, Compatibility Scoring)

---

## 🔐 Authentication

### JWT Token Authentication
Most endpoints require JWT authentication. Include the access token in the Authorization header:

```http
Authorization: Bearer <your-access-token>
```

### Token Structure
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### OAuth Integration
- **Google OAuth**: `/api/oauth/google/`
- **Apple OAuth**: `/api/oauth/apple/`
- **Social Login**: `/api/oauth/social-login/`

---

## 🌐 Base URLs

- **Production**: `https://bondah-backend-api-production.up.railway.app/api/`
- **Development**: `http://localhost:8000/api/`

---

## 📡 API Endpoints

### 🔐 Authentication & User Management

#### User Registration
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

#### User Login
```http
POST /api/auth/login/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

#### Token Refresh
```http
POST /api/auth/refresh/
Content-Type: application/json

{
  "refresh": "your-refresh-token"
}
```

#### User Profile Management
```http
GET /api/auth/profile/
Authorization: Bearer <token>

PUT /api/auth/profile/
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "John Smith",
  "bio": "Love traveling and photography",
  "age": 26,
  "location": "San Francisco"
}
```

#### Account Deactivation
```http
POST /api/auth/deactivate/
Authorization: Bearer <token>
```

#### Device Registration (Push Notifications)
```http
POST /api/auth/device-register/
Authorization: Bearer <token>
Content-Type: application/json

{
  "device_id": "unique-device-id",
  "device_type": "ios",
  "push_token": "firebase-push-token"
}
```

---

### 💬 Chat & Messaging

#### Chat Management
```http
GET /api/chat/
Authorization: Bearer <token>

POST /api/chat/
Authorization: Bearer <token>
Content-Type: application/json

{
  "participants": [1, 2, 3],
  "chat_type": "group",
  "name": "Friends Chat"
}
```

#### Messages
```http
GET /api/chat/{chat_id}/messages/
Authorization: Bearer <token>

POST /api/chat/{chat_id}/messages/
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "Hello! How are you?",
  "message_type": "text"
}
```

#### Voice/Video Calls
```http
POST /api/calls/initiate/
Authorization: Bearer <token>
Content-Type: application/json

{
  "recipient_id": 123,
  "call_type": "video"
}

POST /api/calls/{call_id}/answer/
Authorization: Bearer <token>

POST /api/calls/{call_id}/end/
Authorization: Bearer <token>
```

#### Chat Tipping
```http
POST /api/chat/{chat_id}/messages/
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "Great conversation!",
  "message_type": "tip",
  "tip_amount": 50,
  "tip_gift": 1
}
```

---

### 📱 Social Feed & Stories

#### Posts
```http
GET /api/feed/
Authorization: Bearer <token>

POST /api/feed/
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "Having a great day at the beach!",
  "media_urls": ["https://example.com/beach.jpg"],
  "location": "Miami Beach",
  "visibility": "public"
}
```

#### Comments
```http
GET /api/feed/posts/{post_id}/comments/
Authorization: Bearer <token>

POST /api/feed/posts/{post_id}/comments/
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "Looks amazing! 😍"
}
```

#### Stories
```http
GET /api/feed/stories/
Authorization: Bearer <token>

POST /api/feed/stories/
Authorization: Bearer <token>
Content-Type: application/json

{
  "media_url": "https://example.com/story.jpg",
  "duration": 24,
  "content": "Story caption"
}
```

#### Interactions (Like, Share, Report)
```http
POST /api/feed/posts/{post_id}/interact/
Authorization: Bearer <token>
Content-Type: application/json

{
  "action": "like"
}

POST /api/feed/posts/{post_id}/share/
Authorization: Bearer <token>
```

---

### 🎥 Live Streaming

#### Live Sessions
```http
GET /api/live-sessions/
Authorization: Bearer <token>

POST /api/live-sessions/
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Speed Dating Session",
  "subject_matter": "Speed Dating",
  "max_participants": 10,
  "is_public": true
}
```

#### Join/Leave Sessions
```http
POST /api/live-sessions/{session_id}/join/
Authorization: Bearer <token>

POST /api/live-sessions/{session_id}/leave/
Authorization: Bearer <token>
```

#### Live Gifts
```http
POST /api/live-sessions/gifts/
Authorization: Bearer <token>
Content-Type: application/json

{
  "session_id": 123,
  "gift_id": 5,
  "recipient_id": 456
}
```

---

### 🎯 Matching & Discovery

#### User Search
```http
GET /api/search/users/
Authorization: Bearer <token>

Query Parameters:
- age_min: 18
- age_max: 35
- gender: female
- distance: 25
- interests: ["travel", "music"]
```

#### User Recommendations
```http
GET /api/users/recommendations/
Authorization: Bearer <token>
```

#### User Interactions
```http
POST /api/users/interact/
Authorization: Bearer <token>
Content-Type: application/json

{
  "target_user_id": 123,
  "action": "like",
  "interaction_type": "like"
}
```

#### User Profile Details
```http
GET /api/users/{user_id}/profile/
Authorization: Bearer <token>
```

---

### 📍 Location Services

#### Update Location
```http
POST /api/location/update/
Authorization: Bearer <token>
Content-Type: application/json

{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "accuracy": 10.5,
  "address": "New York, NY"
}
```

#### Nearby Users
```http
GET /api/location/nearby-users/
Authorization: Bearer <token>

Query Parameters:
- radius: 10 (km)
- limit: 50
```

#### Location Privacy Settings
```http
PUT /api/location/privacy/
Authorization: Bearer <token>
Content-Type: application/json

{
  "location_enabled": true,
  "background_location_enabled": false,
  "location_data_sharing": true
}
```

---

### 💰 Monetization & Payments

#### Subscription Plans
```http
GET /api/subscriptions/plans/
Authorization: Bearer <token>

POST /api/subscriptions/
Authorization: Bearer <token>
Content-Type: application/json

{
  "plan_id": 1,
  "payment_method_id": 2
}
```

#### Current Subscription
```http
GET /api/subscriptions/current/
Authorization: Bearer <token>
```

#### Bondcoin Balance
```http
GET /api/bondcoin/balance/
Authorization: Bearer <token>
```

#### Bondcoin Purchase
```http
POST /api/bondcoin/purchase/
Authorization: Bearer <token>
Content-Type: application/json

{
  "package_id": 1,
  "payment_method_id": 2
}
```

#### Payment Processing
```http
POST /api/payments/process/
Authorization: Bearer <token>
Content-Type: application/json

{
  "transaction_type": "subscription",
  "payment_method": 1,
  "amount_usd": 9.99,
  "subscription": 123
}
```

---

### 🎁 Virtual Gifting

#### Gift Categories
```http
GET /api/gifts/categories/
Authorization: Bearer <token>
```

#### Available Gifts
```http
GET /api/gifts/
Authorization: Bearer <token>

Query Parameters:
- category: 1
- price_min: 10
- price_max: 100
```

#### Send Gift
```http
POST /api/gifts/send/
Authorization: Bearer <token>
Content-Type: application/json

{
  "gift_id": 5,
  "recipient_id": 123,
  "message": "Happy Birthday!",
  "occasion": "birthday"
}
```

#### Gift Transactions
```http
GET /api/gifts/transactions/
Authorization: Bearer <token>
```

---

### 🔒 Verification & Security

#### Email OTP
```http
POST /api/verification/email/request/
Authorization: Bearer <token>

POST /api/verification/email/verify/
Authorization: Bearer <token>
Content-Type: application/json

{
  "otp_code": "123456"
}
```

#### Phone OTP
```http
POST /api/verification/phone/request/
Authorization: Bearer <token>

POST /api/verification/phone/verify/
Authorization: Bearer <token>
Content-Type: application/json

{
  "otp_code": "123456"
}
```

#### Document Verification
```http
POST /api/document-verification/upload/
Authorization: Bearer <token>
Content-Type: multipart/form-data

{
  "document_type": "passport",
  "document_image": <file>,
  "front_image": <file>,
  "back_image": <file>
}
```

#### Facial Verification (Liveness Check)
```http
POST /api/liveness/start/
Authorization: Bearer <token>

POST /api/liveness/submit/video/
Authorization: Bearer <token>
Content-Type: multipart/form-data

{
  "session_id": "session-123",
  "video_file": <file>
}
```

#### Username Validation
```http
POST /api/username/validate/
Authorization: Bearer <token>
Content-Type: application/json

{
  "username": "john_doe_123"
}
```

---

### 👨‍💼 Admin & Management

#### Admin Login
```http
POST /api/admin/login/
Content-Type: application/json

{
  "email": "admin@bondah.com",
  "password": "adminpassword"
}
```

#### Job Management
```http
GET /api/jobs/
Authorization: Bearer <token>

POST /api/admin/jobs/create/
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Backend Developer",
  "description": "Looking for a skilled backend developer",
  "job_type": "full-time",
  "location": "Remote"
}
```

#### Waitlist Management
```http
GET /api/admin/waitlist/
Authorization: Bearer <token>
```

---

### 🌍 Translation Services

#### Translate Text
```http
POST /api/translate/
Authorization: Bearer <token>
Content-Type: application/json

{
  "text": "Hello, how are you?",
  "target_language": "es",
  "source_language": "en"
}
```

#### Supported Languages
```http
GET /api/translate/languages/
Authorization: Bearer <token>
```

---

## 📊 Response Formats

### Success Response
```json
{
  "message": "Operation completed successfully",
  "status": "success",
  "data": {
    // Response data
  }
}
```

### Error Response
```json
{
  "message": "Error description",
  "status": "error",
  "errors": {
    "field_name": ["Error message"]
  }
}
```

### Paginated Response
```json
{
  "count": 100,
  "next": "https://api.bondah.com/api/endpoint/?page=3",
  "previous": "https://api.bondah.com/api/endpoint/?page=1",
  "results": [
    // Array of results
  ]
}
```

---

## ❌ Error Handling

### HTTP Status Codes
- `200` - OK (Success)
- `201` - Created (Resource created)
- `400` - Bad Request (Invalid input)
- `401` - Unauthorized (Authentication required)
- `403` - Forbidden (Insufficient permissions)
- `404` - Not Found (Resource not found)
- `422` - Unprocessable Entity (Validation error)
- `429` - Too Many Requests (Rate limited)
- `500` - Internal Server Error (Server error)

### Common Error Responses
```json
{
  "message": "Authentication credentials were not provided.",
  "status": "error",
  "code": "authentication_failed"
}
```

---

## ⏱️ Rate Limiting

- **General API**: 1000 requests per hour per user
- **Authentication**: 10 attempts per minute per IP
- **File Upload**: 10 uploads per minute per user
- **Chat Messages**: 100 messages per minute per user

---

## 🛠️ SDK & Examples

### React Native Example
```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'https://bondah-backend-api-production.up.railway.app/api/',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Login user
const login = async (email, password) => {
  try {
    const response = await api.post('/auth/login/', {
      email,
      password,
    });
    return response.data;
  } catch (error) {
    throw error.response.data;
  }
};

// Get user profile
const getUserProfile = async () => {
  try {
    const response = await api.get('/auth/profile/');
    return response.data;
  } catch (error) {
    throw error.response.data;
  }
};
```

### Python Example
```python
import requests
import json

class BondahAPI:
    def __init__(self, base_url="https://bondah-backend-api-production.up.railway.app/api/"):
        self.base_url = base_url
        self.token = None
        
    def set_token(self, token):
        self.token = token
        
    def _make_request(self, method, endpoint, data=None):
        headers = {
            'Content-Type': 'application/json',
        }
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
            
        url = f"{self.base_url}{endpoint}"
        response = requests.request(method, url, headers=headers, json=data)
        
        if response.status_code >= 400:
            raise Exception(response.json())
            
        return response.json()
    
    def login(self, email, password):
        return self._make_request('POST', 'auth/login/', {
            'email': email,
            'password': password
        })
    
    def get_profile(self):
        return self._make_request('GET', 'auth/profile/')

# Usage
api = BondahAPI()
login_data = api.login('user@example.com', 'password')
api.set_token(login_data['tokens']['access'])
profile = api.get_profile()
```

---

## 📞 Support

- **Documentation**: https://bondah-backend-api-production.up.railway.app/api/docs/
- **API Schema**: https://bondah-backend-api-production.up.railway.app/api/schema/
- **Health Check**: https://bondah-backend-api-production.up.railway.app/health/

---

## 🔄 Version History

- **v1.0.0** - Initial release with comprehensive dating platform features
  - Authentication & User Management
  - Real-time Chat & Messaging
  - Social Feed & Stories
  - Live Streaming & Virtual Gifting
  - Advanced Matching & Discovery
  - Location Services
  - Monetization & Payment Processing
  - Document Verification & Security

---

*This documentation is automatically generated and updated with each API change. For the most current information, always refer to the Swagger UI or ReDoc interfaces.*
