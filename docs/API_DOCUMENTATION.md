# School Transport Management API Documentation

## Base Information

- **Base URL**: `http://api.selvagam.com/api/v1`
- **API Version**: 1.0.0
- **Authentication**: JWT Bearer Token

---

## Authentication

All protected endpoints require a JWT token in the Authorization header:
```
Authorization: Bearer <your_token_here>
```

### 1. Admin Login
**Endpoint**: `POST /auth/admin/login`
**Description**: Login for system administrators.

### 2. Parent Login
**Endpoint**: `POST /auth/parent/login`
**Description**: Login for parents.

### 3. Driver Login
**Endpoint**: `POST /auth/driver/login`
**Description**: Login for bus drivers.

**Request Body (All Login)**:
```json
{
  "phone": 9876543210,
  "password": "your_password"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 4. Get Profile (By Phone)
**Endpoints**: 
- `GET /auth/admin/profile/phone/{phone}`
- `GET /auth/parent/profile/phone/{phone}`
- `GET /auth/driver/profile/phone/{phone}`

---

## Admins

### 1. Create Admin
**Endpoint**: `POST /admins`
**Request Body**:
```json
{
  "phone": 9876543210,
  "email": "admin@school.com",
  "name": "Admin Name"
}
```
*Note: Password is auto-generated and hashed by default during creation.*

### 2. Get All Admins
**Endpoint**: `GET /admins`
**Query Parameters**:
- `status`: `ACTIVE`, `INACTIVE`, `ALL` (default)

### 3. Get All Admin Phone Numbers
**Endpoint**: `GET /admins/phone-numbers/all`
**Description**: Retrieve a unique flat list of all active admin phone numbers.

### 4. Get Admin by ID
**Endpoint**: `GET /admins/{admin_id}`

### 5. Update Admin Status
**Endpoint**: `PUT /admins/{admin_id}/status`
**Request Body**: `{"status": "ACTIVE"}`

### 6. Password Management
- **Reset (Admin/ID)**: `PATCH /admins/{admin_id}/reset-password`
- **Reset (By Phone)**: `PATCH /admins/reset-password-by-phone`
- **Reset to Default**: `PATCH /admins/{admin_id}/reset-default-password` (Sets to First4Name@Last4Phone)

---

---


## Parents

### 1. Create Parent
**Endpoint**: `POST /parents`
**Request Body**:
```json
{
  "name": "Parent Name",
  "phone": 9876543210,
  "email": "parent@example.com",
  "parent_role": "FATHER",
  "door_no": "123",
  "street": "Main Street",
  "city": "Chennai",
  "district": "Chennai",
  "pincode": "600001"
}
```
*Note: Password is auto-generated and hashed by default. Default password is First4Name@Last4Phone.*

### 2. Update Parent FCM Token
**Endpoint**: `PUT /parents/{parent_id}/fcm-token`
**Description**: Updates the FCM token for single-device login enforcement.
**Request Body**: `{"fcm_token": "token_string"}`

### 3. Get All Parent FCM Tokens
**Endpoint**: `GET /parents/fcm-tokens/all`
**Response**: `{"fcm_tokens": ["token1", "token2"], "count": 2}`

---

## Drivers

### 1. Create Driver
**Endpoint**: `POST /drivers`
**Request Body**:
```json
{
  "name": "Driver Name",
  "phone": 9876543210,
  "email": "driver@example.com",
  "licence_number": "DL12345",
  "licence_expiry": "2030-01-01"
}
```

### 2. Upload Driver Photo
**Endpoint**: `POST /uploads/driver/{driver_id}/photo`
**Description**: Upload profile photo via multipart/form-data.

### 3. Update Driver Status
**Endpoint**: `PUT /drivers/{driver_id}/status`
**Statuses**: `ACTIVE`, `INACTIVE`, `SUSPENDED`, `RESIGNED`

---

## Students

### 1. Create Student
**Endpoint**: `POST /students`
**Request Body**:
```json
{
  "parent_id": "parent_uuid",
  "s_parent_id": "optional_parent_uuid",
  "name": "Student Name",
  "dob": "2015-01-01",
  "class_id": "class_uuid",
  "pickup_route_id": "route_uuid",
  "drop_route_id": "route_uuid",
  "pickup_stop_id": "stop_uuid",
  "drop_stop_id": "stop_uuid",
  "emergency_contact": 9876543210
}
```

### 2. Update Student Status
**Endpoint**: `PATCH /students/{student_id}/status`
**Description**: Combined update for student life-cycle and transport availability.
**Request Body**:
```json
{
  "student_status": "CURRENT",
  "transport_status": "ACTIVE"
}
```
*Student Statuses: `CURRENT`, `ALUMNI`, `DISCONTINUED`, `LONG_ABSENT`*
*Transport Statuses: `ACTIVE`, `INACTIVE`*

### 3. Switch Parents
**Endpoint**: `POST /students/{student_id}/switch-parents`
**Description**: Swap Primary (parent_id) and Secondary (s_parent_id) roles.

### 4. Upgrade Class
**Endpoint**: `PATCH /students/{student_id}/upgrade`
**Request Body**: `{"new_class_id": "uuid", "new_study_year": "2024-25"}`

---

## Buses

### 1. Create Bus
**Endpoint**: `POST /buses`
**Request Body**:
```json
{
  "registration_number": "TN-01-AB-1234",
  "vehicle_type": "Mini Bus",
  "seating_capacity": 30,
  "rc_expiry_date": "2025-10-10",
  "fc_expiry_date": "2024-12-12"
}
```

### 2. Upload Documents
- **RC Book**: `POST /uploads/bus/{bus_id}/rc-book`
- **FC Certificate**: `POST /uploads/bus/{bus_id}/fc-certificate`

### 3. Assign Driver
**Endpoint**: `PATCH /buses/{bus_id}/driver`
**Request Body**: `{"driver_id": "uuid"}`

---

## Routes & Route Stops

### 1. Create Route Stop (Transactional)
**Endpoint**: `POST /route-stops`
**Description**: Adding a stop at a specific order (e.g., 2) will automatically shift existing stops (2 → 3, 3 → 4, etc.).

### 2. Reorder Stops
**Endpoint**: `PUT /route-stops/{stop_id}`
**Description**: Changing `pickup_stop_order` or `drop_stop_order` triggers a bulk update to maintain contiguous sequences.

---

## Trips & Tracking

### 1. Create Trip
**Endpoint**: `POST /trips`
**Request Body**: `{"bus_id": "uuid", "driver_id": "uuid", "route_id": "uuid", "trip_type": "PICKUP"}`

### 2. Start Trip
**Endpoint**: `POST /trip/start`
**Description**: Moves status to `ONGOING` and notifies all parents on the route.

### 3. Combined Location Update
**Endpoint**: `POST /bus-tracking/location`
**Description**: Updates bus position, handles automatic stop progression, and triggers proximity notifications ("Approaching" & "Arrived").

---

## Classes & Bulk Ops

### 1. Promote All
**Endpoint**: `POST /classes/promote-all`
**Description**: Increments all students by one grade (e.g., Class 1 → 2).

### 2. Bulk Upgrade
**Endpoint**: `POST /students/bulk-upgrade-class`
**Request Body**: `{"current_class_id": "id1", "new_class_id": "id2", "new_study_year": "2024-25"}`

---

## Error Handling
- `400 Bad Request`: Validation errors or business logic violations.
- `401 Unauthorized`: Invalid or expired JWT.
- `403 Forbidden`: Admin-only key missing for notification broadcast.
- `404 Not Found`: Resource ID does not exist.
- `422 Unprocessable Entity`: Data schema mismatch.

---

**Interactive Documentation**:
- [Swagger UI](http://api.selvagam.com/docs)
- [ReDoc](http://api.selvagam.com/redoc)
