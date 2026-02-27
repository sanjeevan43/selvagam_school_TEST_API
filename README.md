# School Transport Management API

A comprehensive REST API for managing school transportation, including students, parents, drivers, buses, routes, and real-time tracking with proximity alerts.

## 📁 Project Structure

```
school-app-backend/
├── app/
│   ├── __init__.py
│   ├── api/                    # API endpoints and data models
│   │   ├── __init__.py
│   │   ├── routes.py          # Core entity route definitions
│   │   ├── notification_routes.py # Auth, Notifications & Proximity logic
│   │   └── models.py          # Pydantic models and schemas
│   ├── core/                   # Core utilities and configuration
│   │   ├── __init__.py
│   │   ├── auth.py            # JWT authentication
│   │   ├── config.py          # Application configuration
│   │   ├── database.py        # Database connection and queries
│   │   └── security.py        # Password hashing and security
│   ├── services/               # Business logic services
│   │   ├── __init__.py
│   │   ├── bus_tracking.py    # Stop progression & trip completion
│   │   ├── proximity_service.py # Geofence & Proximity alert logic
│   │   ├── cascade_updates.py # Cascade update operations
│   │   └── notification_service.py # Firebase Cloud Messaging service
│   └── notification_api/       # Firebase integration layer
├── docs/                       # Documentation files
│   ├── API_DOCUMENTATION.md
│   ├── COMPLETE_API_DOCUMENTATION.md
│   ├── NOTIFICATIONS.md
│   ├── PROXIMITY_ALERTS.md
│   ├── ADD_DOMAIN_GUIDE.md
│   └── DEPLOY_SECOND_API_GUIDE.md
├── scripts/                    # Deployment and utility scripts
├── sql/                        # SQL migration scripts  
├── main.py                     # FastAPI application entry point
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
└── README.md                  # This file
```

## 🚀 Features

### Core Entities
- **Admins**: System administrators with full control
- **Parents**: Student guardians with FCM push notifications & single-device login
- **Drivers**: Bus drivers with real-time tracking & photo uploads
- **Students**: Student management with class promotion/bulk upgrade logic
- **Buses**: Fleet management with document tracking (RC/FC)
- **Routes**: Route and stop management with transactional reordering
- **Trips**: Daily trip management (Morning/Evening)

### Status Management
- **Student Status**: `CURRENT`, `ALUMNI`, `DISCONTINUED`, `LONG_ABSENT`
- **Transport Status**: `ACTIVE`, `INACTIVE`
- **Bus Status**: `ACTIVE`, `INACTIVE`, `MAINTENANCE`, `SCRAP`, `SPARE`
- **Driver Status**: `ACTIVE`, `INACTIVE`, `SUSPENDED`, `RESIGNED`

### Advanced Features
- **Split Authentication**: Separate login endpoints for Admins, Parents, and Drivers
- **Real-time Bus Tracking**: Automated stop progression and trip auto-completion
- **Proximity Alerts**: Geofence-based notifications ("Approaching", "Arrived")
- **FCM Notifications**: Targeted broadcasts by Route, Class, or Individual
- **Bulk Operations**: Promote all classes, bulk upgrade students to new classes
- **Cascade Updates**: Automated sync across related entities on status/info changes

## 📦 Installation

1. **Clone the repository**
```bash
git clone https://github.com/sanjeevan43/school-app-backend.git
cd school-app-backend
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your database credentials and FCM keys
```

## 🏃 Running the API

### Development Mode
```bash
python main.py
```

### Production Mode
See `docs/DEPLOY_SECOND_API_GUIDE.md` for production deployment instructions.

## 📚 API Documentation

Once running, access interactive documentation at:
- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

## 🔑 Key Endpoints

### Authentication
- `POST /api/v1/auth/admin/login` - Admin specific login
- `POST /api/v1/auth/parent/login` - Parent specific login
- `POST /api/v1/auth/driver/login` - Driver specific login
- `GET /api/v1/auth/admin/profile/phone/{phone}` - Admin profile
- `GET /api/v1/auth/parent/profile/phone/{phone}` - Parent profile
- `GET /api/v1/auth/driver/profile/phone/{phone}` - Driver profile

### Tracking & Alerts
- `POST /api/v1/bus-tracking/location` - Combined tracking & proximity alerts
- `POST /api/v1/trip/start` - Start trip and notify parents
- `POST /api/v1/trip/complete` - Manually complete trip

### Notifications
- `POST /api/v1/notifications/broadcast/parents` - Message all parents
- `POST /api/v1/notifications/route/{route_id}` - Message specific route
- `POST /api/v1/notifications/class/{class_id}` - Message specific class

## 🔧 Tech Stack

- **Framework**: FastAPI
- **Database**: MySQL
- **Authentication**: JWT & Bcrypt
- **Notifications**: Google Firebase Admin SDK (V1 API)
- **Tracking**: Haversine distance-based geofencing

## 👥 Support

For API support, contact: admin@school.com