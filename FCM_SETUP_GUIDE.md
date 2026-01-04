# Firebase Cloud Messaging (FCM) Setup Guide

This guide explains how to configure Firebase Cloud Messaging for the DocAssist Practice Manager mobile app.

## Prerequisites

- Firebase project created at https://console.firebase.google.com
- Admin access to Firebase project
- Flutter development environment set up
- Python backend environment set up

---

## Backend Setup

### 1. Firebase Admin SDK Credentials

1. **Generate Service Account Key:**
   - Go to Firebase Console → Project Settings → Service Accounts
   - Click "Generate New Private Key"
   - Save the JSON file securely (e.g., `/path/to/firebase-credentials.json`)

2. **Set Environment Variable:**
   ```bash
   export FIREBASE_CREDENTIALS_PATH="/path/to/firebase-credentials.json"
   ```

   Or add to your `.env` file:
   ```
   FIREBASE_CREDENTIALS_PATH=/path/to/firebase-credentials.json
   ```

### 2. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This will install `firebase-admin>=6.4.0` along with other dependencies.

### 3. Run Database Migration

```bash
cd backend
alembic upgrade head
```

This creates the `device_tokens` table.

### 4. Test Firebase Configuration

Start the backend server:
```bash
uvicorn app.main:app --reload
```

Test the configuration endpoint:
```bash
curl http://localhost:8000/api/v1/notifications/test
```

Expected response:
```json
{
  "firebase_configured": true,
  "message": "Firebase is properly configured"
}
```

---

## Flutter Setup

### 1. Add Firebase to Your Flutter App

#### For Android:

1. **Download google-services.json:**
   - Go to Firebase Console → Project Settings → General
   - Under "Your apps", select your Android app (or add one)
   - Download `google-services.json`
   - Place it in: `mobile/android/app/google-services.json`

2. **Update build.gradle files:**

   **android/build.gradle:**
   ```gradle
   buildscript {
       dependencies {
           classpath 'com.google.gms:google-services:4.4.0'
       }
   }
   ```

   **android/app/build.gradle:**
   ```gradle
   apply plugin: 'com.google.gms.google-services'

   dependencies {
       implementation platform('com.google.firebase:firebase-bom:32.7.0')
       implementation 'com.google.firebase:firebase-messaging'
   }
   ```

3. **Update AndroidManifest.xml:**

   Add to `android/app/src/main/AndroidManifest.xml`:
   ```xml
   <manifest>
       <application>
           <!-- FCM -->
           <meta-data
               android:name="com.google.firebase.messaging.default_notification_channel_id"
               android:value="default_channel" />

           <meta-data
               android:name="com.google.firebase.messaging.default_notification_icon"
               android:resource="@mipmap/ic_launcher" />
       </application>
   </manifest>
   ```

#### For iOS:

1. **Download GoogleService-Info.plist:**
   - Go to Firebase Console → Project Settings → General
   - Under "Your apps", select your iOS app (or add one)
   - Download `GoogleService-Info.plist`
   - Add it to Xcode project: `mobile/ios/Runner/GoogleService-Info.plist`

2. **Update Info.plist:**

   Add to `ios/Runner/Info.plist`:
   ```xml
   <key>FirebaseAppDelegateProxyEnabled</key>
   <false/>
   ```

3. **Update AppDelegate.swift:**

   **ios/Runner/AppDelegate.swift:**
   ```swift
   import UIKit
   import Flutter
   import Firebase

   @UIApplicationMain
   @objc class AppDelegate: FlutterAppDelegate {
     override func application(
       _ application: UIApplication,
       didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
     ) -> Bool {
       FirebaseApp.configure()

       if #available(iOS 10.0, *) {
         UNUserNotificationCenter.current().delegate = self as UNUserNotificationCenterDelegate
       }

       GeneratedPluginRegistrant.register(with: self)
       return super.application(application, didFinishLaunchingWithOptions: launchOptions)
     }
   }
   ```

4. **Enable Push Notifications Capability:**
   - Open `ios/Runner.xcworkspace` in Xcode
   - Select Runner target → Signing & Capabilities
   - Click "+ Capability"
   - Add "Push Notifications"
   - Add "Background Modes" and enable "Remote notifications"

5. **Upload APNs Certificate:**
   - Generate APNs certificate in Apple Developer Console
   - Upload to Firebase Console → Project Settings → Cloud Messaging → iOS app configuration

### 2. Install Flutter Packages

Dependencies are already in `pubspec.yaml`:
```yaml
dependencies:
  firebase_core: ^2.24.2
  firebase_messaging: ^14.7.10
  flutter_local_notifications: ^16.3.0
```

Run:
```bash
cd mobile
flutter pub get
```

---

## Integration with Your App

### 1. Initialize in main.dart

Update `mobile/lib/main.dart`:

```dart
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/providers/notification_provider.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Firebase
  await Firebase.initializeApp();

  runApp(
    ProviderScope(
      child: MyApp(),
    ),
  );
}

class MyApp extends ConsumerStatefulWidget {
  @override
  ConsumerState<MyApp> createState() => _MyAppState();
}

class _MyAppState extends ConsumerState<MyApp> {
  @override
  void initState() {
    super.initState();

    // Initialize push notifications
    Future.microtask(() {
      ref.read(notificationProvider.notifier);
    });
  }

  @override
  Widget build(BuildContext context) {
    // Your app widget tree
  }
}
```

### 2. Register Device After Login

In your auth flow, after successful login:

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/providers/notification_provider.dart';

// After successful login
final notificationNotifier = ref.read(notificationProvider.notifier);
await notificationNotifier.registerDevice(
  deviceName: 'My Device Name', // Optional
);
```

### 3. Unregister on Logout

```dart
// Before logout
final notificationNotifier = ref.read(notificationProvider.notifier);
await notificationNotifier.unregisterDevice();
```

### 4. Display Unread Count

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/providers/notification_provider.dart';

class NotificationBadge extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final unreadCount = ref.watch(unreadNotificationCountProvider);

    return Badge(
      label: Text('$unreadCount'),
      isLabelVisible: unreadCount > 0,
      child: Icon(Icons.notifications),
    );
  }
}
```

### 5. Request Permissions

```dart
// Request notification permissions (typically on first launch)
final notificationNotifier = ref.read(notificationProvider.notifier);
final granted = await notificationNotifier.requestPermissions();

if (granted) {
  // Permissions granted
} else {
  // Show explanation or settings link
}
```

---

## Backend Usage

### Send Notification to User

```python
from app.services.push_notifications import (
    get_push_notification_service,
    NotificationType,
)

# In your service or endpoint
push_service = get_push_notification_service(db)

# Send appointment reminder
await push_service.send_to_user(
    user_id=user_id,
    notification_type=NotificationType.APPOINTMENT_REMINDER,
    doctor_name="Dr. Smith",
    appointment_time="January 5, 2026 at 10:00 AM",
)

# Send slot offer
await push_service.send_to_user(
    user_id=user_id,
    notification_type=NotificationType.SLOT_OFFER,
    doctor_name="Dr. Smith",
    slot_time="January 5, 2026 at 2:30 PM",
)
```

### Send to Topic (Clinic Broadcast)

```python
# Send announcement to all clinic staff
await push_service.send_to_topic(
    topic=f"clinic_{clinic_id}",
    notification_type=NotificationType.GENERAL_ANNOUNCEMENT,
    title="Clinic Closed Tomorrow",
    message="The clinic will be closed on January 6 for maintenance.",
)
```

### Integration Examples

#### Appointment Reminder (Scheduled Task)

```python
# In a scheduled task (Celery, etc.)
from datetime import datetime, timedelta

# Get appointments for tomorrow
tomorrow = datetime.now() + timedelta(days=1)
appointments = await get_appointments_for_date(tomorrow)

for appointment in appointments:
    if appointment.patient.user_id:
        await push_service.send_to_user(
            user_id=appointment.patient.user_id,
            notification_type=NotificationType.APPOINTMENT_REMINDER,
            doctor_name=appointment.doctor.name,
            appointment_time=appointment.start_time.strftime("%B %d at %I:%M %p"),
        )
```

#### Waitlist Slot Offer

```python
# When appointment is cancelled
from app.services.waitlist import get_waitlist_service

waitlist_service = get_waitlist_service(db)
entry = await waitlist_service.process_cancelled_slot(
    doctor_id=doctor_id,
    slot_time=cancelled_slot_time,
    clinic_id=clinic_id,
)

if entry and entry.patient.user_id:
    await push_service.send_to_user(
        user_id=entry.patient.user_id,
        notification_type=NotificationType.SLOT_OFFER,
        doctor_name=doctor.name,
        slot_time=slot_time.strftime("%B %d at %I:%M %p"),
        data={"waitlist_id": str(entry.id)},
    )
```

---

## Testing

### 1. Test Backend Configuration

```bash
curl http://localhost:8000/api/v1/notifications/test
```

### 2. Register a Device

```bash
# Login first to get auth token
TOKEN="your_jwt_token"

# Register device
curl -X POST http://localhost:8000/api/v1/notifications/register \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_token": "test_fcm_token_123",
    "platform": "android",
    "device_name": "Test Device"
  }'
```

### 3. Send Test Notification

```bash
curl -X POST http://localhost:8000/api/v1/notifications/send \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your_user_id",
    "notification_type": "appointment_reminder",
    "template_vars": {
      "doctor_name": "Dr. Test",
      "appointment_time": "Tomorrow at 10:00 AM"
    }
  }'
```

### 4. Test on Real Device

1. Build and run the app on a physical device (emulators may have limitations)
2. Login to the app
3. Grant notification permissions when prompted
4. Check logs to verify FCM token registration
5. Send a test notification from the backend
6. Verify notification appears on device

---

## Notification Types

Available notification types and their template variables:

| Type | Template Variables | Use Case |
|------|-------------------|----------|
| `appointment_reminder` | `doctor_name`, `appointment_time` | Daily reminder for upcoming appointments |
| `appointment_confirmed` | `doctor_name`, `appointment_date` | Booking confirmation |
| `appointment_cancelled` | `doctor_name`, `appointment_date` | Cancellation notification |
| `appointment_rescheduled` | `new_appointment_time` | Reschedule notification |
| `slot_offer` | `doctor_name`, `slot_time` | Waitlist slot offer |
| `payment_received` | `amount` | Payment confirmation |
| `payment_pending` | `amount`, `appointment_date` | Payment reminder |
| `waitlist_position_update` | `position`, `wait_time` | Queue position update |
| `general_announcement` | `title`, `message` | Custom announcements |

---

## Troubleshooting

### Firebase Not Initialized

**Error:** `Firebase not configured. Set FIREBASE_CREDENTIALS_PATH environment variable.`

**Solution:** Set the `FIREBASE_CREDENTIALS_PATH` environment variable to point to your Firebase service account JSON file.

### Invalid Token Error

**Error:** Token errors when sending notifications

**Solution:** The app automatically deactivates invalid tokens. Users need to re-login to register a fresh token.

### Notifications Not Appearing on iOS

**Solution:**
1. Verify APNs certificate is uploaded to Firebase
2. Check Background Modes are enabled in Xcode
3. Ensure device is not in Do Not Disturb mode
4. Check notification permissions in device Settings

### Notifications Not Appearing on Android

**Solution:**
1. Verify `google-services.json` is correctly placed
2. Check notification channels are created
3. Ensure app has notification permissions
4. Verify FCM token is being generated

---

## Security Best Practices

1. **Never commit Firebase credentials to Git:**
   - Add to `.gitignore`: `firebase-credentials.json`, `google-services.json`, `GoogleService-Info.plist`

2. **Use environment variables:**
   - Store `FIREBASE_CREDENTIALS_PATH` in environment or secrets manager

3. **Validate permissions:**
   - Backend checks user authorization before sending notifications
   - Users can only register/unregister their own devices

4. **Rate limiting:**
   - Consider adding rate limits to prevent notification spam

---

## Production Checklist

- [ ] Firebase project created and configured
- [ ] Service account JSON downloaded and secured
- [ ] `FIREBASE_CREDENTIALS_PATH` environment variable set
- [ ] Database migration run (`alembic upgrade head`)
- [ ] `google-services.json` added to Android app
- [ ] `GoogleService-Info.plist` added to iOS app
- [ ] APNs certificate uploaded to Firebase
- [ ] Push notification permissions tested on real devices
- [ ] Backend notification sending tested
- [ ] Topic subscriptions tested
- [ ] Notification navigation tested
- [ ] Firebase credentials added to `.gitignore`
- [ ] Production server environment variables configured

---

## Additional Resources

- [Firebase Cloud Messaging Documentation](https://firebase.google.com/docs/cloud-messaging)
- [Firebase Admin Python SDK](https://firebase.google.com/docs/admin/setup)
- [FlutterFire Documentation](https://firebase.flutter.dev/docs/messaging/overview)
- [FCM HTTP v1 API](https://firebase.google.com/docs/reference/fcm/rest/v1/projects.messages)

---

**Last Updated:** 2026-01-04
