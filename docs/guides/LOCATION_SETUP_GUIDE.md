# 🗺️ **LOCATION SYSTEM SETUP GUIDE - BONDAH DATING APP**

## 📋 **OVERVIEW**

This guide covers the comprehensive location system implemented for the Bondah Dating mobile app. The system includes GPS tracking, geocoding, privacy controls, and location-based matching - essential features for any modern dating application.

---

## 🚀 **IMPLEMENTATION STATUS**

### ✅ **COMPLETED:**
- ✅ GPS coordinates storage (latitude/longitude)
- ✅ Address geocoding and reverse geocoding
- ✅ Distance calculation between users
- ✅ Location privacy controls
- ✅ Location history tracking
- ✅ Nearby user discovery
- ✅ Match preferences based on location
- ✅ Location permissions management
- ✅ Complete API endpoints
- ✅ Database models and relationships

### 🔧 **NEEDS CONFIGURATION:**
- ⚠️ Google Maps API key (for geocoding)
- ⚠️ Database migrations
- ⚠️ Location permissions setup

---

## 🗄️ **DATABASE MODELS**

### **Updated User Model:**
```python
class User(AbstractUser):
    # Location Fields
    latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    
    # Location Privacy Settings
    location_privacy = models.CharField(max_length=20, choices=[
        ('public', 'Public'),
        ('friends', 'Friends Only'),
        ('private', 'Private'),
        ('hidden', 'Hidden')
    ], default='public')
    location_sharing_enabled = models.BooleanField(default=True)
    location_update_frequency = models.CharField(max_length=20, choices=[
        ('realtime', 'Real-time'),
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('manual', 'Manual Only')
    ], default='manual')
    
    # Matching Preferences
    max_distance = models.PositiveIntegerField(default=50)
    age_range_min = models.PositiveIntegerField(default=18)
    age_range_max = models.PositiveIntegerField(default=100)
    preferred_gender = models.CharField(max_length=10, blank=True, null=True)
    last_location_update = models.DateTimeField(blank=True, null=True)
```

### **New Location Models:**

#### **LocationHistory**
- Stores user location history for privacy and tracking
- Includes accuracy, source, and timestamp information

#### **UserMatch**
- Stores potential matches between users
- Includes distance calculation and compatibility scores

#### **LocationPermission**
- Manages user's location permission settings
- Controls background location, precise location, etc.

---

## 🛠️ **LOCATION UTILITIES**

### **Core Functions:**
- `calculate_distance()` - Haversine formula for distance calculation
- `geocode_address()` - Convert address to GPS coordinates
- `reverse_geocode()` - Convert GPS coordinates to address
- `find_nearby_users()` - Find users within specified distance
- `update_user_location()` - Update user's current location
- `calculate_match_score()` - Calculate compatibility between users

### **Privacy Controls:**
- `can_view_location()` - Check if user can view another's location
- Location privacy levels: Public, Friends Only, Private, Hidden
- Granular permission controls

---

## 📱 **API ENDPOINTS**

### **Location Management:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/location/update/` | POST | Update user's current location |
| `/api/location/geocode/` | POST | Convert address to coordinates |
| `/api/location/privacy/` | PUT | Update location privacy settings |
| `/api/location/permissions/` | GET/PUT | Manage location permissions |
| `/api/location/history/` | GET | Get location history |
| `/api/location/nearby-users/` | GET | Find nearby users |
| `/api/location/match-preferences/` | GET/PUT | Manage match preferences |
| `/api/location/profile/` | GET | Get profile with location data |
| `/api/location/statistics/` | GET | Location statistics (admin) |

### **Request/Response Examples:**

#### **Update Location:**
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

#### **Find Nearby Users:**
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

---

## 🔧 **CONFIGURATION**

### **Environment Variables:**

Add these to your Railway project:

```bash
# Google Maps API (for geocoding)
GOOGLE_MAPS_API_KEY=your-google-maps-api-key

# Location Services
LOCATION_SERVICES_ENABLED=True
DEFAULT_MAX_DISTANCE=50
LOCATION_UPDATE_FREQUENCY=manual
LOCATION_HISTORY_RETENTION_DAYS=30
```

### **Google Maps API Setup:**

1. **Go to [Google Cloud Console](https://console.cloud.google.com/)**
2. **Enable APIs:**
   - Geocoding API
   - Maps JavaScript API
   - Places API
3. **Create API Key:**
   - Go to Credentials → Create Credentials → API Key
   - Restrict the key to your domains
4. **Add to Environment Variables**

---

## 📱 **MOBILE APP INTEGRATION**

### **React Native - Location Services:**

```bash
npm install @react-native-community/geolocation
npm install react-native-permissions
```

#### **Request Location Permission:**
```javascript
import {request, PERMISSIONS, RESULTS} from 'react-native-permissions';
import Geolocation from '@react-native-community/geolocation';

const requestLocationPermission = async () => {
  try {
    const granted = await request(
      Platform.OS === 'ios'
        ? PERMISSIONS.IOS.LOCATION_WHEN_IN_USE
        : PERMISSIONS.ANDROID.ACCESS_FINE_LOCATION
    );
    
    if (granted === RESULTS.GRANTED) {
      return true;
    }
    return false;
  } catch (error) {
    console.error('Permission request error:', error);
    return false;
  }
};
```

#### **Get Current Location:**
```javascript
const getCurrentLocation = () => {
  return new Promise((resolve, reject) => {
    Geolocation.getCurrentPosition(
      (position) => {
        const {latitude, longitude, accuracy} = position.coords;
        resolve({
          latitude,
          longitude,
          accuracy,
          source: 'gps'
        });
      },
      (error) => {
        reject(error);
      },
      {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 10000
      }
    );
  });
};
```

#### **Update Location to API:**
```javascript
const updateLocation = async () => {
  try {
    const location = await getCurrentLocation();
    
    const response = await fetch(`${API_BASE}/api/location/update/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(location),
    });
    
    const result = await response.json();
    if (result.status === 'success') {
      console.log('Location updated:', result.location);
    }
  } catch (error) {
    console.error('Location update failed:', error);
  }
};
```

#### **Find Nearby Users:**
```javascript
const findNearbyUsers = async (maxDistance = 25) => {
  try {
    const response = await fetch(
      `${API_BASE}/api/location/nearby-users/?max_distance=${maxDistance}`,
      {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      }
    );
    
    const result = await response.json();
    if (result.status === 'success') {
      return result.nearby_users;
    }
  } catch (error) {
    console.error('Failed to find nearby users:', error);
  }
};
```

---

## 🔒 **PRIVACY & SECURITY**

### **Location Privacy Levels:**

1. **Public** - Anyone can see your location
2. **Friends Only** - Only matched users can see your location
3. **Private** - Only users you've liked can see your location
4. **Hidden** - No one can see your location

### **Data Protection:**
- Location history automatically expires after 30 days
- Users can delete their location history
- Precise location data is encrypted
- IP-based location fallback for privacy

### **Permission Controls:**
- Location services consent required
- Background location requires explicit permission
- Users can disable location sharing anytime
- Granular permission settings

---

## 🧪 **TESTING**

### **Test Location Update:**
```bash
curl -X POST https://bondah-backend-api-production.up.railway.app/api/location/update/ \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 40.7128,
    "longitude": -74.0060,
    "accuracy": 10.5,
    "source": "gps"
  }'
```

### **Test Nearby Users:**
```bash
curl -X GET "https://bondah-backend-api-production.up.railway.app/api/location/nearby-users/?max_distance=25" \
  -H "Authorization: Bearer <access-token>"
```

### **Test Geocoding:**
```bash
curl -X POST https://bondah-backend-api-production.up.railway.app/api/location/geocode/ \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "Times Square, New York, NY"
  }'
```

---

## 🚀 **DEPLOYMENT CHECKLIST**

### **Before Deployment:**
- [ ] Google Maps API key configured
- [ ] Database migrations created and run
- [ ] Location permissions tested
- [ ] API endpoints tested
- [ ] Privacy controls verified
- [ ] Error handling implemented

### **After Deployment:**
- [ ] Location services working
- [ ] Geocoding functioning
- [ ] Distance calculations accurate
- [ ] Privacy settings respected
- [ ] Mobile app integration tested
- [ ] Performance optimized

---

## 📊 **LOCATION FEATURES FOR DATING APP**

### **Core Dating Features:**
1. **Location-Based Matching** - Find users within specified distance
2. **Distance Display** - Show how far potential matches are
3. **City/Area Matching** - Match users from same city or area
4. **Travel Mode** - Show matches when traveling to different locations
5. **Location Privacy** - Control who can see your location

### **Advanced Features:**
1. **Hotspots** - Popular dating locations in the area
2. **Location History** - See where you've been (for safety)
3. **Geofencing** - Notifications when entering specific areas
4. **Location Verification** - Verify user is in their claimed location
5. **Travel Preferences** - Set preferences for different cities

---

## 🔧 **TROUBLESHOOTING**

### **Common Issues:**

**1. "Location not found" error:**
- Check if GPS is enabled
- Verify location permissions
- Test with different coordinates

**2. "Geocoding failed" error:**
- Check Google Maps API key
- Verify API quotas
- Test with different addresses

**3. "Distance calculation error":**
- Verify coordinate format
- Check for invalid coordinates
- Test with known distances

**4. "Privacy settings not working":**
- Check user permissions
- Verify location privacy logic
- Test with different privacy levels

---

## 📞 **SUPPORT**

For location system assistance:
- **Google Maps API:** [Google Maps Documentation](https://developers.google.com/maps/documentation)
- **React Native Location:** [React Native Geolocation](https://github.com/react-native-community/react-native-geolocation)
- **API Issues:** Check Railway logs or contact support

---

*Location system implementation completed - Ready for mobile app integration!*
