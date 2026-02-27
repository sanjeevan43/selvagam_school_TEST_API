# 🚌 School Transport Management API - Complete Documentation

## 📋 Table of Contents
1. [Overview](#overview)
2. [Authentication APIs](#authentication-apis)
3. [Admin APIs](#admin-apis)
4. [Parent APIs](#parent-apis)
5. [Driver APIs](#driver-apis)
6. [Route APIs](#route-apis)
7. [Bus APIs](#bus-apis)
8. [Route Stop APIs](#route-stop-apis)
9. [Student APIs](#student-apis)
10. [Trip APIs](#trip-apis)
11. [Tracking & Proximity APIs](#tracking--proximity-apis)
12. [Class & Promotion APIs](#class--promotion-apis)
13. [Database Table Models](#database-table-models)

---

## 🎯 Overview

**Base URL**: `http://api.selvagam.com/api/v1`
**API Version**: 1.0.0
**Authentication**: JWT Bearer Token

---

## 🔐 Authentication APIs

### 1. Split Login
**Endpoints**: 
- `POST /auth/admin/login`
- `POST /auth/parent/login`
- `POST /auth/driver/login`
**Description**: Separate login endpoints for different user types to ensure security and role isolation.

### 2. Profile by Phone
**Endpoints**:
- `GET /auth/admin/profile/phone/{phone}`
- `GET /auth/parent/profile/phone/{phone}`
- `GET /auth/driver/profile/phone/{phone}`

---

## 👨‍💼 Admin APIs
- `GET /admins` - List all admins
- `GET /admins/phone-numbers/all` - Get all active admin phone numbers (flat list)
- `PATCH /admins/{id}/reset-password` - Reset password (Admin override)
- `PATCH /admins/{id}/reset-default-password` - Reset to auto-generated default

---

## 👨‍👩‍👧‍👦 Parent APIs
- `POST /parents` - Create parent
- `PUT /parents/{id}/fcm-token` - Update FCM token on login
- `GET /parents/fcm-tokens/all` - List all active parent tokens

---

## 🚗 Driver APIs
- `POST /drivers` - Create driver
- `POST /uploads/driver/{id}/photo` - Upload driver profile photo
- `GET /drivers/fcm-tokens/all` - List all active driver tokens

---

## 🚌 Bus APIs
- `POST /buses` - Create bus with RC/FC expiry tracking
- `POST /uploads/bus/{id}/rc-book` - Upload RC Book PDF/Image
- `POST /uploads/bus/{id}/fc-certificate` - Upload FC Certificate
- `PATCH /buses/{id}/driver` - Assign/Reassign driver to bus

---

## 🛣️ Route APIs
- `POST /routes` - Create route
- `GET /routes` - List all routes (with status filtering)
- `PUT /routes/{id}/status` - Activate/Deactivate route

---

## 🛑 Route Stop APIs
- `POST /route-stops` - Create stop (Automatic shifting of existing stops)
- `PUT /route-stops/{id}` - Update stop (Transactional reordering if order changes)
- `GET /route-stops/by-route/{route_id}/pickup-order` - Ordered list for pickup

---

## 🎓 Student APIs
- `POST /students` - Create student with Primary/Secondary parent assignment
- `PATCH /students/{id}/status` - Combined update for study and transport status
- `POST /students/{id}/switch-parents` - Swap Primary and Secondary parent roles
- `POST /uploads/student/{id}/photo` - Upload student photo

---

## 🗓️ Trip APIs
- `POST /trips` - Create trip (Morning/Evening)
- `GET /trips/ongoing/all` - List currently active trips

---

## 📡 Tracking & Proximity APIs
- `POST /bus-tracking/location` - Combined endpoint for:
    - Stop progression tracking
    - Trip auto-completion
    - Proximity alerts ("Approaching", "Arrived")
- `POST /trip/start` - Notify all parents on a route that the trip has started

---

## 🏫 Class & Promotion APIs
- `POST /students/bulk-upgrade-class` - Move all students from one class to another
- `POST /classes/promote-all` - Bulk increment all students' class (e.g., Class 9 → 10)
- `POST /classes/demote-all` - Bulk decrement all students' class (Admin rollback)

---

## 🗄️ Database Table Models (Key Fields)

### 1. Students Table
| Column | Type | Description |
|--------|------|-------------|
| student_id | UUID | Primary Key |
| parent_id | UUID | Primary Parent |
| s_parent_id | UUID | Secondary Parent (Nullable) |
| student_status | Enum | `CURRENT`, `ALUMNI`, `DISCONTINUED`, `LONG_ABSENT` |
| transport_status | Enum | `ACTIVE`, `INACTIVE` |

### 2. Buses Table
| Column | Type | Description |
|--------|------|-------------|
| status | Enum | `ACTIVE`, `INACTIVE`, `MAINTENANCE`, `SCRAP`, `SPARE` |
| rc_expiry_date | Date | Registration expiry |
| fc_expiry_date | Date | Fitness certificate expiry |

---

**Interactive Documentation**:
- [Swagger UI](http://api.selvagam.com/docs)
- [ReDoc](http://api.selvagam.com/redoc)

