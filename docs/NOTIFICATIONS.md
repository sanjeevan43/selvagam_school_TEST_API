# 📣 Selvagam School Notification Documentation

This document explains how to use the notification system to send messages to Parents, Drivers, and Students via Firebase Cloud Messaging (FCM).

---

### 🔐 Authentication & Session Security
These notifications are triggered when users log in or out to ensure secure access.

| Title | Message Body | Trigger |
| :--- | :--- | :--- |
| **Login Permission Requested** | "Someone is trying to login on a {Device Name}. Do you allow this?" | Sent to the **old device** when a new login attempt occurs. Contains `request_id`. |
| **Session Expired** | "You have been logged in on another device" | Sent to an **old device** AFTER a login request is approved. |
| **Login Approved** | "Your login has been approved. You can now use the app on this device." | Sent to the **new device** once the old device approves the request. |
| **Login Denied** | "Your login request was denied by your other device." | Sent to the **new device** if the old device rejects the request. |

**Endpoint:** `GET /api/v1/notifications/status`

**Success Response:**
```json
{
  "status": "online",
  "initialized": true,
  "creds_found": true,
  "creds_path": "/path/to/firebase-credentials.json",
  "project_id": "school-transport-fcm"
}
```

---

## 🚀 Sending Notifications

### 1. Broadcast to All Parents
Sends a notification to every registered parent device with an active status.
**Endpoint:** `POST /api/v1/notifications/broadcast/parents`
```json
{
  "title": "School Holiday",
  "body": "Tomorrow is a holiday due to local festival.",
  "messageType": "audio"
}
```
*`messageType` can be "audio" or "text". Default is "audio" for prioritized alerts.*

### 2. Broadcast to All Drivers
Sends a notification to every active driver's app.
**Endpoint:** `POST /api/v1/notifications/broadcast/drivers`
```json
{
  "title": "New Route Update",
  "body": "Please check your updated route map for tomorrow morning."
}
```

### 3. Send to a Specific Route
Notifies all parents and students assigned to a specific bus route ID (either pickup or drop).
**Endpoint:** `POST /api/v1/notifications/route/{route_id}`
```json
{
  "title": "Delay Alert: Route 5",
  "body": "The bus is running 15 minutes late due to traffic."
}
```

### 4. Send to a Specific Class
Notifies all parents who have students in a specific class.
**Endpoint:** `POST /api/v1/notifications/class/{class_id}`

### 5. Individual Notifications
- **Student Guardians**: `POST /api/v1/notifications/student/{student_id}`
- **Specific Parent**: `POST /api/v1/notifications/parent/{parent_id}`
- **Specific Device Token**: `POST /api/v1/notifications/send-device` (Requires `token` field)

---

## 📱 Mobile App Integration (Technical Details)

When a notification is sent, the mobile app receives both a **Notification** (UI) and a **Data Payload** (Logic).

### Data Payload Format:
The app should handle these keys in the FCM message:

| Key | Description |
| :--- | :--- |
| `type` | `admin_notification` or `proximity_alert` |
| `messageType` | `audio` (plays alert) or `text` (silent) |
| `recipientType` | `parent`, `driver`, `student`, `route`, `class` |
| `timestamp` | Unix timestamp |
| `message` | The actual body text |
| `trip_id` | (Optional) Link to active trip |

---

## 🛠 Troubleshooting

1.  **"Firebase not initialized"**: 
    - Check `firebase-credentials.json` in root.
    - Check if `GOOGLE_APPLICATION_CREDENTIALS` is set if running outside default environment.
2.  **"No FCM tokens found"**:
    - Ensure parents have logged into the app.
    - Token registration happens automatically at `POST /api/v1/fcm-tokens` or `PUT /api/v1/parents/{id}/fcm-token`.
3.  **Low Delivery Rate**:
    - The backend uses `priority: high` and `android_channel_id: "high_importance_channel"`.
    - Ensure the mobile app has defined this channel in its manifest.
