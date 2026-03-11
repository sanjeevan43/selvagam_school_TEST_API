# 📄 Notification Logging Documentation

The system tracks notifications through two primary mechanisms: **Manual Admin Logs** for direct communication and **Automated Trip Logs** for real-time bus tracking status.

---

## 1. Manual Admin Notifications (Tracking History)

When an administrator sends a manual notification to parents or students via the Admin Panel, the record is stored in the `admin_parent_notifications` table.

### 🗄️ Database Table: `admin_parent_notifications`

| Field | Type | Description |
| :--- | :--- | :--- |
| `notification_id` | `UUID (PK)` | Unique identifier for the log entry. |
| `title` | `VARCHAR(150)` | The title of the sent notification. |
| `message` | `TEXT` | The full body content of the message. |
| `student_id` | `UUID (FK)` | The specific student the message concerns (Optional). |
| `sent_by_admin_id` | `UUID (FK)` | ID of the administrator who triggered the send. |
| `created_at` | `TIMESTAMP` | Record of exactly when the notification was sent. |

### 🔍 Retrieval Endpoints
- `GET /api/v1/admin-parent-notifications/student/{student_id}`: History for a specific student.
- `GET /api/v1/admin-parent-notifications/parent/{parent_id}`: History for all students under one parent.
- `GET /api/v1/admin-parent-notifications/admin/{admin_id}`: History of messages sent by a specific admin.

---

## 2. Automated Trip Progression Logs

For real-time bus tracking (e.g., "Bus Arrived", "Bus Approaching"), the system logs the status within the `trips` table directly to maintain a "Single Source of Truth" for each journey.

### 🗄️ Database Table: `trips`
**Column:** `stop_logs` (JSON)

This column stores a timestamped audit trail of when each stop was reached or skipped.

#### 📝 Example JSON Structure:
```json
{
  "stop_uuid_1": "2024-03-11T09:15:30",  // Arrived at Stop 1
  "stop_uuid_2": "2024-03-11T09:22:15",  // Arrived at Stop 2
  "stop_uuid_3": "SKIPPED",              // Stop was manually or automatically skipped
  "stop_uuid_4": null                    // Pending arrival
}
```

### 📡 Automated Triggers
- **Force Logout Logs**: These are not stored in a persistent "history" table but are logged in the server's application logs (`INFO: Multi-device login detected...`) and reflected by the deletion of the old record in the `fcm_tokens` table.
- **Trip Status Updates**: The `started_at` and `ended_at` timestamps in the `trips` table serve as the log for "Bus Started" and "Trip Completed" notifications.

---

## 3. Proximity Cache

The system also maintains a `route_stop_fcm_cache` to speed up the notification process by mapping `stop_id` to student FCM tokens, ensuring alerts are sent instantly without complex database joins during live tracking.
