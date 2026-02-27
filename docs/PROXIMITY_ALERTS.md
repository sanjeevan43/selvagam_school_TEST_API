# Proximity Alerts & Bus Tracking API Documentation

The Proximity Alerts system tracks the real-time location of the bus, manages stop progression, and sends automated push notifications to parents when the bus is approaching or has arrived at their specific stop.

## 📡 Location Update Endpoint

This is the primary endpoint that should be called by the driver app periodically (e.g., every 5-10 seconds) during an active trip.

**URL:** `POST /api/v1/bus-tracking/location`  
**Method:** `POST`  
**Tags:** `Proximity Alerts`, `Bus Tracking`

### 📥 Request Body (JSON)

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `trip_id` | `string` | Yes | The UUID of the current active trip. |
| `latitude` | `float` | Yes | Current GPS latitude of the bus (-90 to 90). |
| `longitude` | `float` | Yes | Current GPS longitude of the bus (-180 to 180). |
| `timestamp` | `string` | No | ISO format timestamp of the location reading. |

#### **Example Request JSON:**
```json
{
  "trip_id": "550e8400-e29b-41d4-a716-446655440000",
  "latitude": 13.0827,
  "longitude": 80.2707,
  "timestamp": "2024-03-20T10:30:00Z"
}
```

---

### 📤 Response JSON

The response returns details of both **Stop Progression** (database state) and **Proximity Alerts** (geofence notifications).

#### **Example Response JSON:**
```json
{
  "success": true,
  "trip_id": "550e8400-e29b-41d4-a716-446655440000",
  "stop_progression": {
    "success": true,
    "trip_id": "550e8400-e29b-41d4-a716-446655440000",
    "current_stop_order": 3,
    "current_stop_info": {
      "stop_name": "Anna Nagar East",
      "stop_order": 3
    },
    "stops_passed": 1,
    "trip_completed": false,
    "message": "Reached Anna Nagar East"
  },
  "proximity_alerts": {
    "success": true,
    "trip_id": "550e8400-e29b-41d4-a716-446655440000",
    "notifications_sent": [
      "Notified Approaching: Anna Nagar West",
      "Notified Arrived: Anna Nagar East"
    ]
  }
}
```

---

## 🛠️ Core Logic & Trigger Radii

The system automatically filters which parents to notify based on the distance between the bus and the stop coordinates.

| Status | Radius | Action Taken |
| :--- | :--- | :--- |
| **Approaching** | **500m** | Sends "Bus Approaching" notification to parents at that stop. |
| **Arrived** | **20m** | Sends "Bus Arrived" notification to parents at that stop. |
| **Current Stop** | **300m** | Updates the `current_stop_order` in the database to keep the route map accurate. |

> **Note:** The `APPROACHING_RADIUS` can be adjusted via the `GEOFENCE_RADIUS` variable in your `.env` file.

## 🔔 Notifications Sent

### 1. **Bus Approaching**
- **Trigger:** Bus within 500m of a stop.
- **Title:** `🚌 Bus Approaching`
- **Body:** `The bus is approaching [Stop Name]. Please be ready.`

### 2. **Bus Arrived**
- **Trigger:** Bus within 20m of a stop.
- **Title:** `🚌 Bus Arrived`
- **Body:** `The bus has arrived at [Stop Name].`

### 3. **Trip Completed**
- **Trigger:** Bus reaches the final stop of the route.
- **Title:** `✅ Trip Completed`
- **Body:** `The bus has reached the final stop: [Stop Name].`

---

## 🚀 How to Use (Frontend Integration)
1. Call `PUT /api/v1/trips/{trip_id}/start` when the driver clicks "Start Trip".
2. Start a background GPS timer on the driver's phone.
3. Every 5-10 seconds, call `POST /api/v1/bus-tracking/location` with the current coordinates.
4. The backend will handle all logic:
   - Calculating distances.
   - Finding parents for those specific stops.
   - Sending push notifications.
   - Updating the database trip status.
   - Auto-completing the trip at the last stop.
