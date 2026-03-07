import re
from pydantic import BaseModel, EmailStr, Field, validator, ConfigDict, field_validator
from typing import Optional, Literal, Any
from datetime import date, datetime
from enum import Enum

# Common Validation logic
def phone_validator(v: int) -> int:
    if v is not None:
        v_str = str(v)
        if not re.match(r"^\d{10}$", v_str):
            raise ValueError('Phone number must be exactly 10 digits')
    return v

# Enums
class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ALL = "ALL"


class DriverStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    RESIGNED = "RESIGNED"
    ALL = "ALL"


class BusStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"
    SCRAP = "SCRAP"
    SPARE = "SPARE"
    ALL = "ALL"


class UserType(str, Enum):
    ADMIN = "admin"
    PARENT = "parent"
    DRIVER = "driver"

class ParentRole(str, Enum):
    FATHER = "FATHER"
    MOTHER = "MOTHER"
    GUARDIAN = "GUARDIAN"
    ALL = "ALL"

class StudentStatus(str, Enum):
    CURRENT = "CURRENT"
    ALUMNI = "ALUMNI"
    DISCONTINUED = "DISCONTINUED"
    LONG_ABSENT = "LONG_ABSENT"
    ACTIVE = "ACTIVE"
    ALL = "ALL"



class TransportStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    ALL = "ALL"


class TripType(str, Enum):
    PICKUP = "PICKUP"
    DROP = "DROP"

class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    ALL = "ALL"

class TripStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    ONGOING = "ONGOING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELED = "CANCELED"
    ALL = "ALL"

class ActiveFilter(str, Enum):
    ALL = "ALL"
    ACTIVE_ONLY = "ACTIVE_ONLY"


# Admin Models
class AdminBase(BaseModel):
    phone: int = Field(..., description="User phone number")
    email: Optional[EmailStr] = None
    name: str = Field(..., max_length=100)

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        return phone_validator(v)


class AdminCreate(AdminBase):
    pass

class AdminUpdate(BaseModel):
    phone: Optional[int] = Field(None, description="User phone number")
    email: Optional[EmailStr] = None
    name: Optional[str] = Field(None, max_length=100)
    status: Optional[UserStatus] = None

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        return phone_validator(v) if v is not None else v


class AdminResponse(BaseModel):
    admin_id: str
    phone: int = Field(..., description="User phone number")
    email: Optional[EmailStr] = None
    name: str = Field(..., max_length=100)
    status: UserStatus
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Parent Models
class ParentBase(BaseModel):
    phone: int = Field(..., description="User phone number")
    email: Optional[EmailStr] = None
    name: str = Field(..., max_length=100)
    parent_role: ParentRole = ParentRole.GUARDIAN
    door_no: Optional[str] = Field(None, max_length=50)
    street: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=50)
    district: Optional[str] = Field(None, max_length=50)
    pincode: Optional[str] = Field(None, max_length=10)

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        return phone_validator(v)


class ParentCreate(ParentBase):
    pass  # Password will be auto-generated

class ParentUpdate(BaseModel):
    phone: Optional[int] = Field(None, description="User phone number")
    email: Optional[EmailStr] = None
    name: Optional[str] = Field(None, max_length=100)
    parent_role: Optional[ParentRole] = None
    door_no: Optional[str] = Field(None, max_length=50)
    street: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=50)
    district: Optional[str] = Field(None, max_length=50)
    pincode: Optional[str] = Field(None, max_length=10)
    parents_active_status: Optional[UserStatus] = None

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        return phone_validator(v) if v is not None else v


class ParentResponse(BaseModel):
    parent_id: str
    phone: int = Field(..., description="User phone number")
    email: Optional[EmailStr] = None
    name: str = Field(..., max_length=100)
    parent_role: ParentRole = ParentRole.GUARDIAN
    door_no: Optional[str] = Field(None, max_length=50)
    street: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=50)
    district: Optional[str] = Field(None, max_length=50)
    pincode: Optional[str] = Field(None, max_length=10)
    parents_active_status: UserStatus = UserStatus.ACTIVE
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Driver Models
class DriverBase(BaseModel):
    name: str = Field(..., max_length=100)
    phone: int = Field(..., description="User phone number")
    email: Optional[EmailStr] = None
    licence_number: Optional[str] = Field(None, max_length=50)
    licence_expiry: Optional[date] = None
    photo_url: Optional[str] = Field(None, max_length=255)
    fcm_token: Optional[str] = Field(None, max_length=255)

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        return phone_validator(v)


class DriverCreate(DriverBase):
    pass  # Password will be auto-generated

class DriverUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    phone: Optional[int] = Field(None, description="User phone number")
    email: Optional[EmailStr] = None
    licence_number: Optional[str] = Field(None, max_length=50)
    licence_expiry: Optional[date] = None
    fcm_token: Optional[str] = Field(None, max_length=255)
    status: Optional[DriverStatus] = None

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        return phone_validator(v) if v is not None else v


class DriverResponse(BaseModel):
    driver_id: str
    name: str = Field(..., max_length=100)
    phone: int = Field(..., description="User phone number")
    email: Optional[EmailStr] = None
    licence_number: Optional[str] = Field(None, max_length=50)
    licence_expiry: Optional[date] = None
    fcm_token: Optional[str] = Field(None, max_length=255)
    status: DriverStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Route Models
class RouteBase(BaseModel):
    name: str = Field(..., max_length=100)

class RouteCreate(RouteBase):
    pass

class RouteUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    routes_active_status: Optional[UserStatus] = None

class RouteResponse(BaseModel):
    route_id: str
    name: str = Field(..., max_length=100)
    routes_active_status: UserStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Bus Models
class BusBase(BaseModel):
    registration_number: str = Field(..., max_length=20)
    driver_id: Optional[str] = None
    route_id: Optional[str] = None
    vehicle_type: Optional[str] = Field(None, max_length=50)
    bus_brand: Optional[str] = Field(None, max_length=100)
    bus_model: Optional[str] = Field(None, max_length=100)
    seating_capacity: int = Field(..., gt=0, lt=100)
    rc_expiry_date: Optional[date] = None
    fc_expiry_date: Optional[date] = None
    rc_book_url: Optional[str] = Field(None, max_length=255)
    fc_certificate_url: Optional[str] = Field(None, max_length=255)
    bus_name: Optional[str] = Field(None, max_length=50)

    @field_validator('registration_number')
    @classmethod
    def validate_reg_no(cls, v):
        # Basic registration number format validation (alphanumeric and spaces/hyphens)
        if not re.match(r"^[A-Z0-9\s\-]+$", v.upper()):
            raise ValueError('Registration number must be alphanumeric')
        return v.upper()

class BusCreate(BusBase):
    pass

class BusUpdate(BaseModel):
    registration_number: Optional[str] = Field(None, max_length=20)
    driver_id: Optional[str] = None
    route_id: Optional[str] = None
    vehicle_type: Optional[str] = Field(None, max_length=50)
    bus_brand: Optional[str] = Field(None, max_length=100)
    bus_model: Optional[str] = Field(None, max_length=100)
    seating_capacity: Optional[int] = Field(None, gt=0)
    rc_expiry_date: Optional[date] = None
    fc_expiry_date: Optional[date] = None
    rc_book_url: Optional[str] = Field(None, max_length=255)
    fc_certificate_url: Optional[str] = Field(None, max_length=255)
    status: Optional[BusStatus] = None
    bus_name: Optional[str] = Field(None, max_length=50)

class BusResponse(BaseModel):
    bus_id: str
    registration_number: str = Field(..., max_length=20)
    driver_id: Optional[str] = None
    route_id: Optional[str] = None
    vehicle_type: Optional[str] = Field(None, max_length=50)
    bus_brand: Optional[str] = Field(None, max_length=100)
    bus_model: Optional[str] = Field(None, max_length=100)
    seating_capacity: int = Field(..., gt=0)
    rc_expiry_date: Optional[date] = None
    fc_expiry_date: Optional[date] = None
    rc_book_url: Optional[str] = Field(None, max_length=255)
    fc_certificate_url: Optional[str] = Field(None, max_length=255)
    status: BusStatus
    bus_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Class Models
class ClassBase(BaseModel):
    class_name: str = Field(..., max_length=20)
    section: str = Field(..., max_length=10)

class ClassCreate(ClassBase):
    pass

class ClassUpdate(BaseModel):
    class_name: Optional[str] = Field(None, max_length=20)
    section: Optional[str] = Field(None, max_length=10)
    status: Optional[UserStatus] = None

class ClassResponse(BaseModel):
    class_id: str
    class_name: str = Field(..., max_length=20)
    section: str = Field(..., max_length=10)
    status: UserStatus
    number_of_students: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Route Stop Models
class RouteStopBase(BaseModel):
    route_id: str
    stop_name: str = Field(..., max_length=100)
    location: Optional[str] = Field(None, max_length=100)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    pickup_stop_order: int
    drop_stop_order: int

    @field_validator('stop_name')
    @classmethod
    def validate_stop_name(cls, v):
        if len(v.strip()) < 3:
            raise ValueError('Stop name must be at least 3 characters long')
        return v.strip()

class RouteStopCreate(RouteStopBase):
    pass

class RouteStopUpdate(BaseModel):
    stop_name: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=100)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    pickup_stop_order: Optional[int] = None
    drop_stop_order: Optional[int] = None

class RouteStopResponse(BaseModel):
    stop_id: str
    route_id: str
    stop_name: str = Field(..., max_length=100)
    location: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    pickup_stop_order: int
    drop_stop_order: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Student Models
class StudentCreate(BaseModel):
    parent_id: str
    s_parent_id: Optional[str] = None
    name: str = Field(..., max_length=100)
    gender: Gender
    dob: Optional[date] = None
    study_year: str = Field(..., max_length=20)
    class_id: Optional[str] = None
    pickup_route_id: str
    drop_route_id: str
    pickup_stop_id: str
    drop_stop_id: str
    emergency_contact: Optional[int] = Field(None, description="Emergency contact number")
    student_photo_url: Optional[str] = Field(None, max_length=200)
    is_transport_user: bool = True
    student_status: StudentStatus = StudentStatus.CURRENT
    transport_status: TransportStatus = TransportStatus.ACTIVE

    @field_validator('s_parent_id', mode='before')
    @classmethod
    def validate_s_parent_id(cls, v):
        """Convert invalid s_parent_id values to None"""
        if v in [None, "", "string", "null"]:
            return None
        return v
    
    @field_validator('student_photo_url', mode='before')
    @classmethod
    def validate_photo_url(cls, v):
        """Convert invalid photo URL values to None"""
        if v in ["", "string", "null"]:
            return None
        return v

class StudentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    gender: Optional[Gender] = None
    dob: Optional[date] = None
    study_year: Optional[str] = Field(None, max_length=20)
    class_id: Optional[str] = None
    pickup_route_id: Optional[str] = None
    drop_route_id: Optional[str] = None
    pickup_stop_id: Optional[str] = None
    drop_stop_id: Optional[str] = None
    is_transport_user: Optional[bool] = None
    emergency_contact: Optional[int] = None
    student_photo_url: Optional[str] = None
    student_status: Optional[StudentStatus] = None
    transport_status: Optional[TransportStatus] = None

class SecondaryParentUpdate(BaseModel):
    s_parent_id: Optional[str] = Field(None, description="Secondary Parent ID (UUID)")

class StudentPhotoUpdate(BaseModel):
    student_photo_url: str = Field(..., max_length=200, description="URL of the student's photo")

class PrimaryParentUpdate(BaseModel):
    parent_id: str = Field(..., description="Primary Parent ID (UUID)")

class ClassUpgradeRequest(BaseModel):
    new_class_id: str = Field(..., description="The new class ID to move the student(s) to")
    new_study_year: Optional[str] = Field(None, description="The new study year (e.g., 2024-2025)")

class BulkClassUpgradeRequest(BaseModel):
    current_class_id: str = Field(..., description="The class ID currently assigned to students")
    new_class_id: str = Field(..., description="The new class ID to move students to")
    new_study_year: Optional[str] = Field(None, description="The new study year for all affected students")

class UpgradeResponse(BaseModel):
    message: str
    affected_students: int

class BulkPromoteRequest(BaseModel):
    new_study_year: Optional[str] = Field(None, description="New study year for all students (e.g., 2025-2026)")
    max_class: Optional[int] = Field(10, description="Maximum class number. Students at this class will be marked as ALUMNI. Default: 10")
    
class BulkDemoteRequest(BaseModel):
    new_study_year: Optional[str] = Field(None, description="New study year for all students")
    min_class: Optional[int] = Field(1, description="Minimum class number. Students at this class will NOT be demoted. Default: 1")

class BulkPromoteResponse(BaseModel):
    message: str
    total_classes_processed: int
    total_students_promoted: int
    details: list
    graduated_students: Optional[int] = 0

class StudentResponse(BaseModel):
    student_id: str
    parent_id: str
    s_parent_id: Optional[str] = None
    name: str
    gender: Gender
    dob: Optional[date] = None
    study_year: str
    class_id: Optional[str] = None
    pickup_route_id: str
    drop_route_id: str
    pickup_stop_id: str
    drop_stop_id: str
    emergency_contact: Optional[int] = None
    student_photo_url: Optional[str] = None
    student_status: StudentStatus
    transport_status: TransportStatus
    is_transport_user: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Trip Models
class TripBase(BaseModel):
    bus_id: str
    driver_id: str
    route_id: str
    trip_date: date
    trip_type: TripType

class TripCreate(TripBase):
    pass

class TripUpdate(BaseModel):
    status: Optional[TripStatus] = None
    current_stop_order: Optional[int] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

class TripResponse(BaseModel):
    trip_id: str
    bus_id: str
    driver_id: str
    route_id: str
    trip_date: date
    trip_type: TripType
    status: TripStatus
    current_stop_order: int
    skipped_stops: Optional[str] = None
    stop_logs: Any = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Authentication Models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[str] = None
    user_type: Optional[str] = None
    phone: Optional[int] = None

# Error Handling Models
class ErrorHandlingBase(BaseModel):
    error_type: Optional[str] = Field(None, max_length=50)
    error_code: Optional[int] = None
    error_description: Optional[str] = Field(None, max_length=255)

class ErrorHandlingCreate(ErrorHandlingBase):
    pass

class ErrorHandlingUpdate(BaseModel):
    error_type: Optional[str] = Field(None, max_length=50)
    error_code: Optional[int] = None
    error_description: Optional[str] = Field(None, max_length=255)

class ErrorHandlingResponse(BaseModel):
    error_id: str
    error_type: Optional[str] = Field(None, max_length=50)
    error_code: Optional[int] = None
    error_description: Optional[str] = Field(None, max_length=255)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# FCM Token Models
class FCMTokenBase(BaseModel):
    fcm_token: str = Field(..., max_length=255)
    student_id: Optional[str] = None
    parent_id: Optional[str] = None

class FCMTokenCreate(FCMTokenBase):
    pass

class FCMTokenUpdate(BaseModel):
    fcm_token: Optional[str] = Field(None, max_length=255)
    student_id: Optional[str] = None
    parent_id: Optional[str] = None

class FCMTokenResponse(BaseModel):
    fcm_id: str
    fcm_token: str = Field(..., max_length=255)
    student_id: Optional[str] = None
    parent_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class BusLocationUpdate(BaseModel):
    trip_id: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    timestamp: Optional[datetime] = None

class DriverLocationUpdate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

class DriverLocationResponse(BaseModel):
    driver_id: str
    latitude: float
    longitude: float
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class NotificationRequest(BaseModel):
    trip_id: str
    message: str = Field(..., min_length=1, max_length=500)
    stop_id: Optional[str] = None

    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError('Message cannot be empty or just whitespace')
        return v.strip()

# Universal login model (phone + password)
class LoginRequest(BaseModel):
    phone: int = Field(..., description="User phone number")
    password: str = Field(..., min_length=1, description="User password")

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        return phone_validator(v)

class BusDriverAssign(BaseModel):
    driver_id: Optional[str] = Field(None, description="Driver ID (UUID) or null to unassign")

# Status Update Models
class StatusUpdate(BaseModel):
    status: UserStatus = Field(..., description="New status value")

class DriverStatusUpdate(BaseModel):
    status: DriverStatus = Field(..., description="New driver status value (ACTIVE, INACTIVE, SUSPENDED, RESIGNED)")

class BusStatusUpdate(BaseModel):
    status: BusStatus = Field(..., description="New bus status value (ACTIVE, INACTIVE, MAINTENANCE, SCRAP, SPARE)")

class StudentStatusUpdate(BaseModel):
    status: StudentStatus = Field(..., description="New student status value (CURRENT, ALUMNI, DISCONTINUED, LONG_ABSENT)")

class TransportStatusUpdate(BaseModel):
    status: TransportStatus = Field(..., description="New transport status value (ACTIVE, INACTIVE)")

class CombinedStatusUpdate(BaseModel):
    student_status: Optional[StudentStatus] = Field(None, description="Student status (CURRENT, ALUMNI, DISCONTINUED, LONG_ABSENT)")
    transport_status: Optional[TransportStatus] = Field(None, description="Transport status (ACTIVE, INACTIVE)")

class TripStatusUpdate(BaseModel):
    status: TripStatus = Field(..., description="New trip status value")
class PasswordReset(BaseModel):
    new_password: str = Field(..., min_length=1, max_length=72, description="New user password")

class PasswordResetByPhone(BaseModel):
    phone: int = Field(..., description="User phone number")
    new_password: str = Field(..., min_length=1, max_length=72, description="New user password")

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        return phone_validator(v)

class PasswordUpdate(BaseModel):
    new_password: str = Field(..., min_length=1, max_length=72, description="New user password")
    old_password: Optional[str] = Field(None, description="Current user password")

# Admin Parent Notification Models
class AdminParentNotificationBase(BaseModel):
    title: str = Field(..., max_length=150)
    message: str
    student_id: Optional[str] = None
    sent_by_admin_id: str

class AdminParentNotificationCreate(AdminParentNotificationBase):
    pass

class AdminParentNotificationResponse(AdminParentNotificationBase):
    notification_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
