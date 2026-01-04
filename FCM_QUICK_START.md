# FCM Push Notifications - Quick Start

This is your quick reference to get push notifications working.

## Files Created

### Backend (Python/FastAPI)
- ✅ `/backend/app/models/device_token.py` - Device token model
- ✅ `/backend/app/services/push_notifications.py` - FCM service (18KB)
- ✅ `/backend/app/api/v1/notifications.py` - API endpoints (8.6KB)
- ✅ `/backend/alembic/versions/003_add_device_tokens.py` - Database migration
- ✅ `/backend/requirements.txt` - Updated with firebase-admin

### Flutter (Mobile App)
- ✅ `/mobile/lib/core/services/push_notification_service.dart` - FCM service (15KB)
- ✅ `/mobile/lib/core/providers/notification_provider.dart` - State management (9.4KB)

### Documentation
- ✅ `FCM_SETUP_GUIDE.md` - Complete setup instructions (14KB)
- ✅ `PUSH_NOTIFICATIONS_API.md` - API reference (8.6KB)
- ✅ `FCM_IMPLEMENTATION_SUMMARY.md` - Architecture overview (18KB)

---

## 5-Minute Setup (Development)

### Backend Setup

1. **Install Dependencies:**
   ```bash
   cd /home/user/appointment_system/backend
   pip install -r requirements.txt
   ```

2. **Run Database Migration:**
   ```bash
   alembic upgrade head
   ```

3. **Get Firebase Credentials:**
   - Go to https://console.firebase.google.com
   - Create project (or use existing)
   - Project Settings → Service Accounts → Generate New Private Key
   - Save JSON file as `firebase-credentials.json`

4. **Set Environment Variable:**
   ```bash
   export FIREBASE_CREDENTIALS_PATH="/path/to/firebase-credentials.json"
   ```

5. **Start Backend:**
   ```bash
   uvicorn app.main:app --reload
   ```

6. **Test Configuration:**
   ```bash
   curl http://localhost:8000/api/v1/notifications/test
   ```

### Flutter Setup

1. **Add Firebase Config Files:**
   - Download `google-services.json` from Firebase Console
   - Place in: `/home/user/appointment_system/mobile/android/app/google-services.json`

   - Download `GoogleService-Info.plist` from Firebase Console
   - Place in: `/home/user/appointment_system/mobile/ios/Runner/GoogleService-Info.plist`

2. **Install Dependencies:**
   ```bash
   cd /home/user/appointment_system/mobile
   flutter pub get
   ```

3. **Update main.dart:**
   ```dart
   import 'package:firebase_core/firebase_core.dart';

   void main() async {
     WidgetsFlutterBinding.ensureInitialized();
     await Firebase.initializeApp();
     runApp(ProviderScope(child: MyApp()));
   }
   ```

4. **Initialize Notifications:**
   ```dart
   // In your app's init or login callback
   final notificationNotifier = ref.read(notificationProvider.notifier);
   await notificationNotifier.registerDevice();
   ```

5. **Run on Real Device:**
   ```bash
   flutter run
   ```

---

## Test Notification Flow

1. **Login to the app** (to get auth token)

2. **Check device is registered:**
   ```bash
   curl http://localhost:8000/api/v1/notifications/devices \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

3. **Send test notification:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/notifications/send \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "YOUR_USER_ID",
       "notification_type": "appointment_reminder",
       "template_vars": {
         "doctor_name": "Dr. Test",
         "appointment_time": "Tomorrow at 10:00 AM"
       }
     }'
   ```

4. **Verify notification appears on device**

---

## Common Issues

### "Firebase not configured"
- Make sure FIREBASE_CREDENTIALS_PATH environment variable is set
- Verify the path points to a valid JSON file
- Restart backend server after setting environment variable

### No FCM token on Flutter
- Make sure Firebase is initialized before app runs
- Check device has internet connection
- Verify google-services.json is in correct location
- Run on real device (not emulator)

### Notification not appearing
- Check notification permissions are granted
- Verify device token is registered on backend
- Check backend logs for FCM errors
- For iOS: Verify APNs certificate is uploaded to Firebase

---

## Next Steps

1. **Read the Full Docs:**
   - `FCM_SETUP_GUIDE.md` - Detailed setup for Android/iOS
   - `PUSH_NOTIFICATIONS_API.md` - All API endpoints
   - `FCM_IMPLEMENTATION_SUMMARY.md` - Architecture details

2. **Integrate with Your App:**
   - Add notification UI to show recent messages
   - Implement navigation from notification taps
   - Add settings to manage notification preferences

3. **Production Setup:**
   - Upload APNs certificate for iOS
   - Configure Firebase for production
   - Set up scheduled appointment reminders
   - Integrate with waitlist for slot offers

---

## Available Notification Types

1. `appointment_reminder` - Daily reminders
2. `appointment_confirmed` - Booking confirmations
3. `appointment_cancelled` - Cancellation notices
4. `appointment_rescheduled` - Reschedule updates
5. `slot_offer` - Waitlist slot offers
6. `payment_received` - Payment confirmations
7. `payment_pending` - Payment reminders
8. `waitlist_position_update` - Queue updates
9. `general_announcement` - Custom announcements

---

## Support

Need help? Check these files:
- Setup issues → `FCM_SETUP_GUIDE.md`
- API questions → `PUSH_NOTIFICATIONS_API.md`
- Architecture → `FCM_IMPLEMENTATION_SUMMARY.md`

Or examine the code:
- Backend: `backend/app/services/push_notifications.py`
- Flutter: `mobile/lib/core/services/push_notification_service.dart`

---

**Quick Tip:** The system is designed to work gracefully even if Firebase is not configured. The app will continue to function, just without push notifications.

**Status:** ✅ Ready to Use
**Last Updated:** 2026-01-04
