from fastapi import APIRouter, HTTPException, status, File, UploadFile
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime, date
import uuid
import logging
import json
import re

from app.core.database import get_db, execute_query
from app.api.models import *
from app.core.auth import create_access_token
from app.services.bus_tracking import bus_tracking_service
from app.notification_api.service import notification_service
from app.services.cascade_updates import cascade_service
from app.services.upload_service import upload_service

router = APIRouter()
logger = logging.getLogger(__name__)

# =====================================================
# USER PROFILE
# =====================================================

@router.get("/auth/profile", tags=["Authentication"])
async def get_profile(phone: int):
    """Get user profile by phone number"""
    try:
        # Check admins table
        admin_query = "SELECT admin_id, phone, email, name, status, last_login_at, created_at FROM admins WHERE phone = %s"
        admin = execute_query(admin_query, (phone,), fetch_one=True)
        
        if admin:
            return {
                "user_type": "admin",
                "user_id": admin['admin_id'],
                "phone": admin['phone'],
                "email": admin['email'],
                "name": admin['name'],
                "status": admin['status'],
                "last_login_at": admin['last_login_at'],
                "created_at": admin['created_at']
            }
        
        # Check parents table
        parent_query = "SELECT parent_id, phone, email, name, parent_role, parents_active_status, last_login_at, created_at FROM parents WHERE phone = %s"
        parent = execute_query(parent_query, (phone,), fetch_one=True)
        
        if parent:
            return {
                "user_type": "parent",
                "user_id": parent['parent_id'],
                "phone": parent['phone'],
                "email": parent['email'],
                "name": parent['name'],
                "parent_role": parent['parent_role'],
                "status": parent['parents_active_status'],
                "last_login_at": parent['last_login_at'],
                "created_at": parent['created_at']
            }
        
        # Check drivers table
        driver_query = "SELECT driver_id, phone, email, name, licence_number, status, created_at FROM drivers WHERE phone = %s"
        driver = execute_query(driver_query, (phone,), fetch_one=True)
        
        if driver:
            return {
                "user_type": "driver",
                "user_id": driver['driver_id'],
                "phone": driver['phone'],
                "email": driver['email'],
                "name": driver['name'],
                "licence_number": driver['licence_number'],
                "status": driver['status'],
                "created_at": driver['created_at']
            }
        
        raise HTTPException(status_code=404, detail="User not found")
        
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get profile")

# =====================================================
# ADMIN ENDPOINTS
# =====================================================

@router.post("/admins", response_model=AdminResponse, tags=["Admins"])
async def create_admin(admin: AdminCreate):
    """Create a new admin"""
    try:
        admin_id = str(uuid.uuid4())
        query = """
        INSERT INTO admins (admin_id, phone, email, password_hash, name)
        VALUES (%s, %s, %s, %s, %s)
        """
        execute_query(query, (admin_id, admin.phone, admin.email, admin.password, admin.name))
        
        return await get_admin(admin_id)
    except Exception as e:
        logger.error(f"Create admin error: {e}")
        raise HTTPException(status_code=400, detail="Failed to create admin")

@router.get("/admins", response_model=List[AdminResponse], tags=["Admins"])
async def get_all_admins(status: UserStatus = UserStatus.ALL):
    """Get all admins"""
    if status == UserStatus.ALL:
        query = "SELECT admin_id, phone, email, name, status, last_login_at, created_at, updated_at FROM admins ORDER BY created_at DESC"
        admins = execute_query(query, fetch_all=True)
    else:
        query = "SELECT admin_id, phone, email, name, status, last_login_at, created_at, updated_at FROM admins WHERE status = %s ORDER BY created_at DESC"
        admins = execute_query(query, (status.value,), fetch_all=True)
    return admins or []


@router.get("/admins/{admin_id}", response_model=AdminResponse, tags=["Admins"])
async def get_admin(admin_id: str):
    """Get admin by ID"""
    query = "SELECT admin_id, phone, email, name, status, last_login_at, created_at, updated_at FROM admins WHERE admin_id = %s"
    admin = execute_query(query, (admin_id,), fetch_one=True)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    return admin

@router.put("/admins/{admin_id}", response_model=AdminResponse, tags=["Admins"])
async def update_admin(admin_id: str, admin_update: AdminUpdate):
    """Update admin"""
    update_fields = []
    values = []
    
    for field, value in admin_update.dict(exclude_unset=True).items():
        if value is not None:
            update_fields.append(f"{field} = %s")
            values.append(value)
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    values.append(admin_id)
    query = f"UPDATE admins SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE admin_id = %s"
    
    result = execute_query(query, tuple(values))
    if result == 0:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    return await get_admin(admin_id)

@router.put("/admins/{admin_id}/status", response_model=AdminResponse, tags=["Admins"])
async def update_admin_status(admin_id: str, status_update: StatusUpdate):
    """Update admin status only"""
    query = "UPDATE admins SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE admin_id = %s"
    result = execute_query(query, (status_update.status.value, admin_id))
    if result == 0:
        raise HTTPException(status_code=404, detail="Admin not found")
    return await get_admin(admin_id)

@router.delete("/admins/{admin_id}", tags=["Admins"])
async def delete_admin(admin_id: str):
    """Delete admin"""
    query = "DELETE FROM admins WHERE admin_id = %s"
    result = execute_query(query, (admin_id,))
    if result == 0:
        raise HTTPException(status_code=404, detail="Admin not found")
    return {"message": "Admin deleted successfully"}

@router.patch("/admins/{admin_id}/password", tags=["Admins"])
async def patch_admin_password(admin_id: str, password_data: PasswordUpdate):
    """PATCH: Update admin password"""
    query = "UPDATE admins SET password_hash = %s, updated_at = CURRENT_TIMESTAMP WHERE admin_id = %s"
    result = execute_query(query, (password_data.new_password, admin_id))
    if result == 0:
        raise HTTPException(status_code=404, detail="Admin not found")
    return {"message": "Password updated successfully"}

# =====================================================
# PARENT ENDPOINTS
# =====================================================

@router.post("/parents", response_model=ParentResponse, tags=["Parents"])
async def create_parent(parent: ParentCreate):
    """Create a new parent"""
    try:
        parent_id = str(uuid.uuid4())
        query = """
        INSERT INTO parents (parent_id, phone, email, password_hash, name, parent_role, 
                           door_no, street, city, district, pincode)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        result = execute_query(query, (parent_id, parent.phone, parent.email, parent.password, 
                             parent.name, parent.parent_role.value, parent.door_no, parent.street,
                             parent.city, parent.district, parent.pincode))
        
        if result == 0:
            raise HTTPException(status_code=400, detail="Failed to insert parent")
        
        return await get_parent(parent_id)
    except Exception as e:
        logger.error(f"Create parent error: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to create parent: {str(e)}")

@router.get("/parents", response_model=List[ParentResponse], tags=["Parents"])
async def get_all_parents(
    status: UserStatus = UserStatus.ALL,
    role: ParentRole = ParentRole.ALL,
    student_status: StudentStatus = StudentStatus.ALL,
    transport_status: TransportStatus = TransportStatus.ALL,
    search: Optional[str] = None
):
    """Get all parents with optional filters for status, role, and search (name/phone)"""
    conditions = []
    params = []
    
    if status != UserStatus.ALL:
        conditions.append("parents_active_status = %s")
        params.append(status.value)
    
    if role != ParentRole.ALL:
        conditions.append("parent_role = %s")
        params.append(role.value)

    if student_status != StudentStatus.ALL:
        conditions.append("""
            EXISTS (SELECT 1 FROM students s 
                   WHERE (s.parent_id = parents.parent_id OR s.s_parent_id = parents.parent_id) 
                   AND s.student_status = %s)
        """)
        params.append(student_status.value)

    if transport_status != TransportStatus.ALL:
        conditions.append("""
            EXISTS (SELECT 1 FROM students s 
                   WHERE (s.parent_id = parents.parent_id OR s.s_parent_id = parents.parent_id) 
                   AND s.transport_status = %s)
        """)
        params.append(transport_status.value)
        
    if search:
        conditions.append("(name LIKE %s OR phone LIKE %s)")
        search_param = f"%{search}%"
        params.append(search_param)
        params.append(search_param)
        
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"""
    SELECT parent_id, phone, email, name, parent_role, door_no, street, city, district, pincode, 
           parents_active_status, last_login_at, created_at, updated_at 
    FROM parents {where_clause} 
    ORDER BY created_at DESC
    """
    
    parents = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return parents or []


@router.get("/parents/{parent_id}", response_model=ParentResponse, tags=["Parents"])
async def get_parent(parent_id: str):
    """Get parent by ID"""
    query = "SELECT parent_id, phone, email, name, parent_role, door_no, street, city, district, pincode, parents_active_status, last_login_at, created_at, updated_at FROM parents WHERE parent_id = %s"
    parent = execute_query(query, (parent_id,), fetch_one=True)
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    return parent

@router.put("/parents/{parent_id}", response_model=ParentResponse, tags=["Parents"])
async def update_parent(parent_id: str, parent_update: ParentUpdate):
    """Update parent with cascade updates"""
    try:
        # Get old data for cascade comparison
        old_parent = execute_query("SELECT parent_id, phone, email, name, parents_active_status FROM parents WHERE parent_id = %s", (parent_id,), fetch_one=True)
        if not old_parent:
            raise HTTPException(status_code=404, detail="Parent not found")
        
        update_fields = []
        values = []
        
        for field, value in parent_update.dict(exclude_unset=True).items():
            if value is not None:
                update_fields.append(f"{field} = %s")
                values.append(value)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        values.append(parent_id)
        query = f"UPDATE parents SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE parent_id = %s"
        
        result = execute_query(query, tuple(values))
        if result == 0:
            raise HTTPException(status_code=404, detail="Parent not found")
        
        # Trigger cascade updates
        new_data = parent_update.dict(exclude_unset=True)
        cascade_service.update_parent_cascades(parent_id, old_parent, new_data)
        
        return await get_parent(parent_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update parent error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update parent")

@router.put("/parents/{parent_id}/status", response_model=ParentResponse, tags=["Parents"])
async def update_parent_status(parent_id: str, status_update: StatusUpdate):
    """Update parent status only"""
    query = "UPDATE parents SET parents_active_status = %s, updated_at = CURRENT_TIMESTAMP WHERE parent_id = %s"
    result = execute_query(query, (status_update.status.value, parent_id))
    if result == 0:
        raise HTTPException(status_code=404, detail="Parent not found")
    return await get_parent(parent_id)

@router.patch("/parents/{parent_id}/password", tags=["Parents"])
async def patch_parent_password(parent_id: str, password_data: PasswordUpdate):
    """PATCH: Update parent password"""
    query = "UPDATE parents SET password_hash = %s, updated_at = CURRENT_TIMESTAMP WHERE parent_id = %s"
    result = execute_query(query, (password_data.new_password, parent_id))
    if result == 0:
        raise HTTPException(status_code=404, detail="Parent not found")
    return {"message": "Password updated successfully"}

@router.get("/parents/{parent_id}/students", response_model=List[StudentResponse], tags=["Parents"])
async def get_parent_students(parent_id: str):
    """Get all students belonging to a parent (Primary or Secondary)"""
    query = "SELECT * FROM students WHERE parent_id = %s OR s_parent_id = %s ORDER BY name"
    students = execute_query(query, (parent_id, parent_id), fetch_all=True)
    return students or []

@router.put("/parents/{parent_id}/fcm-token", tags=["Parents"])
async def update_parent_fcm_token(parent_id: str, fcm_data: dict):
    """Update FCM token for parent when they login"""
    try:
        fcm_token = fcm_data.get("fcm_token")
        if not fcm_token:
            raise HTTPException(status_code=400, detail="fcm_token is required")
        
        # Check if parent exists
        parent = execute_query("SELECT parent_id FROM parents WHERE parent_id = %s", (parent_id,), fetch_one=True)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent not found")
        
        # Update or insert FCM token
        query = """
        INSERT INTO fcm_tokens (fcm_id, fcm_token, parent_id) 
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE 
        fcm_token = VALUES(fcm_token),
        updated_at = CURRENT_TIMESTAMP
        """
        fcm_id = str(uuid.uuid4())
        execute_query(query, (fcm_id, fcm_token, parent_id))
        
        return {
            "message": "FCM token updated successfully",
            "parent_id": parent_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update parent FCM token error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update FCM token")

@router.patch("/parents/{parent_id}/fcm-token", tags=["Parents"])
async def patch_parent_fcm_token(parent_id: str, fcm_data: dict):
    """PATCH: Update parent FCM token"""
    try:
        fcm_token = fcm_data.get("fcm_token")
        if not fcm_token:
            raise HTTPException(status_code=400, detail="fcm_token is required")
        
        # Check if parent exists
        parent = execute_query("SELECT parent_id FROM parents WHERE parent_id = %s", (parent_id,), fetch_one=True)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent not found")
        
        # Update or insert FCM token
        query = """
        INSERT INTO fcm_tokens (fcm_id, fcm_token, parent_id) 
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE 
        fcm_token = VALUES(fcm_token),
        updated_at = CURRENT_TIMESTAMP
        """
        fcm_id = str(uuid.uuid4())
        execute_query(query, (fcm_id, fcm_token, parent_id))
        
        return {
            "message": "FCM token updated successfully",
            "parent_id": parent_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update parent FCM token error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update FCM token")

@router.get("/parents/fcm-tokens/all", tags=["Parents"])
async def get_all_parent_fcm_tokens():
    """GET: Retrieve all unique parent FCM tokens (flat list)"""
    query = """
    SELECT DISTINCT f.fcm_token 
    FROM parents p
    INNER JOIN fcm_tokens f ON p.parent_id = f.parent_id
    WHERE f.fcm_token IS NOT NULL AND p.parents_active_status = 'ACTIVE'
    """
    token_results = execute_query(query, fetch_all=True)
    # Use set comprehension to ensure uniqueness and then convert back to list
    fcm_tokens = list({row['fcm_token'] for row in token_results}) if token_results else []
    return {"fcm_tokens": fcm_tokens, "count": len(fcm_tokens)}

@router.delete("/parents/{parent_id}", tags=["Parents"])
async def delete_parent(parent_id: str):
    """Delete parent with cascade cleanup"""
    try:
        # Get parent data for cascade cleanup
        parent_data = execute_query("SELECT parent_id, phone, email, name FROM parents WHERE parent_id = %s", (parent_id,), fetch_one=True)
        if not parent_data:
            raise HTTPException(status_code=404, detail="Parent not found")
        
        # Perform cascade cleanup
        cascade_service.delete_cascades("parents", parent_id, parent_data)
        
        # Delete parent
        query = "DELETE FROM parents WHERE parent_id = %s"
        result = execute_query(query, (parent_id,))
        if result == 0:
            raise HTTPException(status_code=404, detail="Parent not found")
        
        return {"message": "Parent deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete parent error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete parent")

# =====================================================
# DRIVER ENDPOINTS
# =====================================================

@router.post("/drivers", response_model=DriverResponse, tags=["Drivers"])
async def create_driver(driver: DriverCreate):
    """Create a new driver"""
    try:
        driver_id = str(uuid.uuid4())
        query = """
        INSERT INTO drivers (driver_id, name, phone, email, licence_number, licence_expiry, 
                           password_hash, photo_url, fcm_token)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        execute_query(query, (driver_id, driver.name, driver.phone, driver.email,
                             driver.licence_number, driver.licence_expiry, driver.password,
                             driver.photo_url, driver.fcm_token))
        
        return await get_driver(driver_id)
    except Exception as e:
        logger.error(f"Create driver error: {e}")
        raise HTTPException(status_code=400, detail="Failed to create driver")

@router.get("/drivers", response_model=List[DriverResponse], tags=["Drivers"])
async def get_all_drivers(status: DriverStatus = DriverStatus.ALL, active_filter: ActiveFilter = ActiveFilter.ALL):
    """Get all drivers, with status and active status filtering."""
    conditions = []
    params = []
    
    if active_filter == ActiveFilter.ACTIVE_ONLY:
        conditions.append("status = 'ACTIVE'")
    elif status != DriverStatus.ALL:
        conditions.append("status = %s")
        params.append(status.value)
    
    if conditions:
        query = f"SELECT driver_id, name, phone, email, licence_number, licence_expiry, photo_url, status, fcm_token, created_at, updated_at FROM drivers WHERE {' AND '.join(conditions)} ORDER BY name"
        drivers = execute_query(query, tuple(params), fetch_all=True)
    else:
        query = "SELECT driver_id, name, phone, email, licence_number, licence_expiry, photo_url, status, fcm_token, created_at, updated_at FROM drivers ORDER BY name"
        drivers = execute_query(query, fetch_all=True)
    return drivers or []


@router.get("/drivers/{driver_id}", response_model=DriverResponse, tags=["Drivers"])
async def get_driver(driver_id: str):
    """Get driver by ID"""
    query = "SELECT driver_id, name, phone, email, licence_number, licence_expiry, photo_url, status, fcm_token, created_at, updated_at FROM drivers WHERE driver_id = %s"
    driver = execute_query(query, (driver_id,), fetch_one=True)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return driver

@router.put("/drivers/{driver_id}", response_model=DriverResponse, tags=["Drivers"])
async def update_driver(driver_id: str, driver_update: DriverUpdate):
    """Update driver"""
    update_fields = []
    values = []
    
    for field, value in driver_update.dict(exclude_unset=True).items():
        if value is not None:
            update_fields.append(f"{field} = %s")
            values.append(value)
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    values.append(driver_id)
    query = f"UPDATE drivers SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE driver_id = %s"
    
    result = execute_query(query, tuple(values))
    if result == 0:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    return await get_driver(driver_id)

@router.put("/drivers/{driver_id}/status", response_model=DriverResponse, tags=["Drivers"])
async def update_driver_status(driver_id: str, status_update: DriverStatusUpdate):
    """Update driver status only (ACTIVE, INACTIVE, SUSPENDED)"""
    query = "UPDATE drivers SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE driver_id = %s"
    result = execute_query(query, (status_update.status.value, driver_id))
    if result == 0:
        raise HTTPException(status_code=404, detail="Driver not found")
    return await get_driver(driver_id)

@router.patch("/drivers/{driver_id}/fcm-token", response_model=DriverResponse, tags=["Drivers"])
async def patch_driver_fcm_token(driver_id: str, fcm_data: dict):
    """PATCH: Update driver FCM token"""
    fcm_token = fcm_data.get("fcm_token")
    if not fcm_token:
        raise HTTPException(status_code=400, detail="fcm_token is required")
    
    query = "UPDATE drivers SET fcm_token = %s, updated_at = CURRENT_TIMESTAMP WHERE driver_id = %s"
    result = execute_query(query, (fcm_token, driver_id))
    if result == 0:
        raise HTTPException(status_code=404, detail="Driver not found")
    return await get_driver(driver_id)

@router.get("/drivers/fcm-tokens/all", tags=["Drivers"])
async def get_all_driver_fcm_tokens():
    """GET: Retrieve all unique driver FCM tokens (flat list)"""
    query = """
    SELECT DISTINCT fcm_token 
    FROM drivers 
    WHERE fcm_token IS NOT NULL AND fcm_token != '' AND status = 'ACTIVE'
    """
    token_results = execute_query(query, fetch_all=True)
    # Use set comprehension to ensure uniqueness
    fcm_tokens = list({row['fcm_token'] for row in token_results}) if token_results else []
    return {"fcm_tokens": fcm_tokens, "count": len(fcm_tokens)}

@router.delete("/drivers/{driver_id}", tags=["Drivers"])
async def delete_driver(driver_id: str):
    """Delete driver"""
    query = "DELETE FROM drivers WHERE driver_id = %s"
    result = execute_query(query, (driver_id,))
    if result == 0:
        raise HTTPException(status_code=404, detail="Driver not found")
    return {"message": "Driver deleted successfully"}

@router.patch("/drivers/{driver_id}/password", tags=["Drivers"])
async def patch_driver_password(driver_id: str, password_data: PasswordUpdate):
    """PATCH: Update driver password"""
    query = "UPDATE drivers SET password_hash = %s, updated_at = CURRENT_TIMESTAMP WHERE driver_id = %s"
    result = execute_query(query, (password_data.new_password, driver_id))
    if result == 0:
        raise HTTPException(status_code=404, detail="Driver not found")
    return {"message": "Password updated successfully"}

@router.post("/uploads/driver/{driver_id}/photo", tags=["Drivers"])
async def upload_driver_photo(driver_id: str, file: UploadFile = File(...)):
    """Upload/Update driver photo and delete old one if exists"""
    # Verify driver and get old photo
    driver = execute_query("SELECT driver_id, photo_url FROM drivers WHERE driver_id = %s", (driver_id,), fetch_one=True)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
        
    # Only allow images
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    # Save new file
    file_url = await upload_service.save_file(file, "drivers", custom_filename=driver_id)
    
    # Update database
    try:
        query = "UPDATE drivers SET photo_url = %s, updated_at = CURRENT_TIMESTAMP WHERE driver_id = %s"
        execute_query(query, (file_url, driver_id))
        
        # Delete old file from storage if it's different
        if driver.get('photo_url') and driver['photo_url'] != file_url:
            upload_service.delete_file_by_url(driver['photo_url'])
            
    except Exception as e:
        logger.error(f"Failed to update driver photo URL: {e}")
        
    return {"url": file_url}

# =====================================================
# ROUTE ENDPOINTS
# =====================================================

@router.post("/routes", response_model=RouteResponse, tags=["Routes"])
async def create_route(route: RouteCreate):
    """Create a new route"""
    try:
        route_id = str(uuid.uuid4())
        query = "INSERT INTO routes (route_id, name) VALUES (%s, %s)"
        execute_query(query, (route_id, route.name))
        
        return await get_route(route_id)
    except Exception as e:
        logger.error(f"Create route error: {e}")
        raise HTTPException(status_code=400, detail="Failed to create route")

@router.get("/routes", response_model=List[RouteResponse], tags=["Routes"])
async def get_all_routes(active_filter: ActiveFilter = ActiveFilter.ALL):
    """Get all routes, defaults to ALL"""
    if active_filter == ActiveFilter.ACTIVE_ONLY:
        query = "SELECT * FROM routes WHERE routes_active_status = 'ACTIVE' ORDER BY name"
    else:
        query = "SELECT * FROM routes ORDER BY created_at DESC"
    routes = execute_query(query, fetch_all=True)
    return routes or []


@router.get("/routes/{route_id}", response_model=RouteResponse, tags=["Routes"])
async def get_route(route_id: str):
    """Get route by ID"""
    query = "SELECT * FROM routes WHERE route_id = %s"
    route = execute_query(query, (route_id,), fetch_one=True)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route

@router.put("/routes/{route_id}", response_model=RouteResponse, tags=["Routes"])
async def update_route(route_id: str, route_update: RouteUpdate):
    """Update route with cascade updates"""
    try:
        # Get old data for cascade comparison
        old_route = execute_query("SELECT * FROM routes WHERE route_id = %s", (route_id,), fetch_one=True)
        if not old_route:
            raise HTTPException(status_code=404, detail="Route not found")
        
        update_fields = []
        values = []
        
        for field, value in route_update.dict(exclude_unset=True).items():
            if value is not None:
                update_fields.append(f"{field} = %s")
                values.append(value)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        values.append(route_id)
        query = f"UPDATE routes SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE route_id = %s"
        
        result = execute_query(query, tuple(values))
        if result == 0:
            raise HTTPException(status_code=404, detail="Route not found")
        
        # Trigger cascade updates
        new_data = route_update.dict(exclude_unset=True)
        cascade_service.update_route_cascades(route_id, old_route, new_data)
        
        return await get_route(route_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update route error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update route")

@router.put("/routes/{route_id}/status", response_model=RouteResponse, tags=["Routes"])
async def update_route_status(route_id: str, status_update: StatusUpdate):
    """Update route status only"""
    query = "UPDATE routes SET routes_active_status = %s, updated_at = CURRENT_TIMESTAMP WHERE route_id = %s"
    result = execute_query(query, (status_update.status.value, route_id))
    if result == 0:
        raise HTTPException(status_code=404, detail="Route not found")
    return await get_route(route_id)

@router.delete("/routes/{route_id}", tags=["Routes"])
async def delete_route(route_id: str):
    """Delete route with cascade cleanup"""
    try:
        # Get route data for cascade cleanup
        route_data = execute_query("SELECT * FROM routes WHERE route_id = %s", (route_id,), fetch_one=True)
        if not route_data:
            raise HTTPException(status_code=404, detail="Route not found")
        
        # Perform cascade cleanup
        cascade_service.delete_cascades("routes", route_id, route_data)
        
        # Delete route
        query = "DELETE FROM routes WHERE route_id = %s"
        result = execute_query(query, (route_id,))
        if result == 0:
            raise HTTPException(status_code=404, detail="Route not found")
        
        return {"message": "Route deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete route error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete route")

# =====================================================
# ROUTE STOP ENDPOINTS
# =====================================================

@router.post("/route-stops", response_model=List[RouteStopResponse], tags=["Route Stops"])
async def create_route_stop(route_stop: RouteStopCreate):
    """Create a new route stop with order validation and transactional shifting"""
    route_id = route_stop.route_id
    new_order = route_stop.pickup_stop_order

    # 1. Validate route exists
    route = execute_query("SELECT route_id FROM routes WHERE route_id = %s", (route_id,), fetch_one=True)
    if not route:
        raise HTTPException(status_code=404, detail=f"Route {route_id} not found")

    # 2. Validate pickup_stop_order is >= 1
    if new_order < 1:
        raise HTTPException(status_code=400, detail="pickup_stop_order must be greater than or equal to 1")

    # 3. Get current maximum pickup_stop_order for that route
    max_order_data = execute_query(
        "SELECT MAX(pickup_stop_order) as max_order FROM route_stops WHERE route_id = %s",
        (route_id,),
        fetch_one=True
    )
    max_order = max_order_data['max_order'] if max_order_data and max_order_data['max_order'] is not None else 0

    # 4. If new_order > max_order + 1 → return validation error
    if new_order > max_order + 1:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid order. Next available order is {max_order + 1}, but {new_order} was provided."
        )

    try:
        # 5. Start database transaction
        with get_db() as conn:
            with conn.cursor() as cursor:
                # 6. Shift existing stops
                shift_query = """
                UPDATE route_stops
                SET pickup_stop_order = pickup_stop_order + 1,
                    drop_stop_order = drop_stop_order + 1
                WHERE route_id = %s
                AND pickup_stop_order >= %s
                """
                cursor.execute(shift_query, (route_id, new_order))

                # 7. Insert new stop with given order
                stop_id = str(uuid.uuid4())
                insert_query = """
                INSERT INTO route_stops (stop_id, route_id, stop_name, latitude, longitude, 
                                       pickup_stop_order, drop_stop_order)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                # For now, we keep drop_stop_order same as pickup_stop_order as per existing patterns
                cursor.execute(insert_query, (
                    stop_id, route_id, route_stop.stop_name, 
                    route_stop.latitude, route_stop.longitude, 
                    new_order, new_order
                ))
                # 8. Commit transaction (handled by context manager)

        # 9. Rebuild route_stop_fcm_cache for that route
        cascade_service.update_route_fcm_cache(route_id)

        # 10. Return updated stop list sorted by pickup_stop_order
        return await get_all_route_stops(route_id)

    except Exception as e:
        logger.error(f"Create route stop error: {e}")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"Failed to create route stop: {str(e)}")

@router.get("/route-stops", response_model=List[RouteStopResponse], tags=["Route Stops"])
async def get_all_route_stops(route_id: Optional[str] = None):
    """Get all route stops, optionally filtered by route"""
    if route_id:
        query = "SELECT * FROM route_stops WHERE route_id = %s ORDER BY pickup_stop_order"
        stops = execute_query(query, (route_id,), fetch_all=True)
    else:
        query = "SELECT * FROM route_stops ORDER BY route_id, pickup_stop_order"
        stops = execute_query(query, fetch_all=True)
    return stops or []

@router.get("/route-stops/{stop_id}", response_model=RouteStopResponse, tags=["Route Stops"])
async def get_route_stop(stop_id: str):
    """Get route stop by ID"""
    query = "SELECT * FROM route_stops WHERE stop_id = %s"
    stop = execute_query(query, (stop_id,), fetch_one=True)
    if not stop:
        raise HTTPException(status_code=404, detail="Route stop not found")
    return stop

@router.put("/route-stops/{stop_id}", response_model=RouteStopResponse, tags=["Route Stops"])
async def update_route_stop(stop_id: str, stop_update: RouteStopUpdate):
    """Update route stop and reorder with transactional shifting if order changed"""
    try:
        # Get old data for cascade comparison and route_id
        old_stop = execute_query("SELECT * FROM route_stops WHERE stop_id = %s", (stop_id,), fetch_one=True)
        if not old_stop:
            raise HTTPException(status_code=404, detail="Route stop not found")
        
        # If order is being updated, validate it
        if stop_update.pickup_stop_order is not None and stop_update.pickup_stop_order != old_stop['pickup_stop_order']:
            new_order = stop_update.pickup_stop_order
            
            # Validation: new_order must be within [1, max_order]
            max_order_data = execute_query(
                "SELECT MAX(pickup_stop_order) as max_order FROM route_stops WHERE route_id = %s",
                (old_stop['route_id'],),
                fetch_one=True
            )
            max_order = max_order_data['max_order'] if max_order_data and max_order_data['max_order'] else 1
            
            if new_order < 1 or new_order > max_order:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid order. Order must be between 1 and {max_order}."
                )

        update_fields = []
        values = []
        
        for field, value in stop_update.dict(exclude_unset=True).items():
            if value is not None:
                update_fields.append(f"{field} = %s")
                values.append(value)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Start database transaction for reordering if needed
        with get_db() as conn:
            with conn.cursor() as cursor:
                # 1. Update the stop itself
                update_query = f"UPDATE route_stops SET {', '.join(update_fields)} WHERE stop_id = %s"
                cursor.execute(update_query, tuple(values + [stop_id]))
                
                # 2. If order was updated, handle the shifting of other stops
                if stop_update.pickup_stop_order is not None and stop_update.pickup_stop_order != old_stop['pickup_stop_order']:
                    new_order = stop_update.pickup_stop_order
                    old_order = old_stop['pickup_stop_order']
                    
                    if new_order < old_order:
                        # Moving up: Shift stops in between DOWN
                        shift_query = """
                        UPDATE route_stops 
                        SET pickup_stop_order = pickup_stop_order + 1, 
                            drop_stop_order = drop_stop_order + 1 
                        WHERE route_id = %s AND pickup_stop_order >= %s 
                        AND pickup_stop_order < %s AND stop_id != %s
                        """
                        cursor.execute(shift_query, (old_stop['route_id'], new_order, old_order, stop_id))
                    else:
                        # Moving down: Shift stops in between UP
                        shift_query = """
                        UPDATE route_stops 
                        SET pickup_stop_order = pickup_stop_order - 1, 
                            drop_stop_order = drop_stop_order - 1 
                        WHERE route_id = %s AND pickup_stop_order > %s 
                        AND pickup_stop_order <= %s AND stop_id != %s
                        """
                        cursor.execute(shift_query, (old_stop['route_id'], old_order, new_order, stop_id))
        
        # 3. Trigger cascade updates
        new_data = stop_update.dict(exclude_unset=True)
        cascade_service.update_route_stop_cascades(stop_id, old_stop, new_data)
        
        return await get_route_stop(stop_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update route stop error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update route stop: {str(e)}")

@router.delete("/route-stops/{stop_id}", tags=["Route Stops"])
async def delete_route_stop(stop_id: str):
    """Delete route stop and reorder remaining stops using transactional shifting"""
    try:
        # Get stop data for route_id and current order
        stop_data = execute_query("SELECT * FROM route_stops WHERE stop_id = %s", (stop_id,), fetch_one=True)
        if not stop_data:
            raise HTTPException(status_code=404, detail="Route stop not found")
        
        route_id = stop_data['route_id']
        deleted_order = stop_data['pickup_stop_order']
        
        # Perform cascade cleanup before delete
        cascade_service.delete_cascades("route_stops", stop_id, stop_data)
        
        # Start database transaction
        with get_db() as conn:
            with conn.cursor() as cursor:
                # 1. Delete route stop
                cursor.execute("DELETE FROM route_stops WHERE stop_id = %s", (stop_id,))
                
                # 2. Shift remaining stops down (pickup_stop_order - 1)
                shift_query = """
                UPDATE route_stops
                SET pickup_stop_order = pickup_stop_order - 1,
                    drop_stop_order = drop_stop_order - 1
                WHERE route_id = %s
                AND pickup_stop_order > %s
                """
                cursor.execute(shift_query, (route_id, deleted_order))
                
                # Transaction commits automatically via get_db() context manager
        
        # 3. Update FCM cache for the route
        cascade_service.update_route_fcm_cache(route_id)
        
        return {"message": "Route stop deleted and route shifted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete route stop error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete route stop")

# Removed _reorder_route_stops and manual_reorder_route since shifting is now transactional and robust.

# =====================================================
# BUS ENDPOINTS
# =====================================================

@router.post("/buses", response_model=BusResponse, tags=["Buses"])
async def create_bus(bus: BusCreate):
    """Create a new bus"""
    try:
        bus_id = str(uuid.uuid4())
        query = """
        INSERT INTO buses (bus_id, registration_number, driver_id, route_id, vehicle_type,
                          bus_brand, bus_model, seating_capacity, rc_expiry_date, fc_expiry_date,
                          rc_book_url, fc_certificate_url, bus_name)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        execute_query(query, (bus_id, bus.registration_number, bus.driver_id, bus.route_id,
                             bus.vehicle_type, bus.bus_brand, bus.bus_model, bus.seating_capacity,
                             bus.rc_expiry_date, bus.fc_expiry_date, bus.rc_book_url, 
                             bus.fc_certificate_url, bus.bus_name))
        
        return await get_bus(bus_id)
    except Exception as e:
        logger.error(f"Create bus error: {e}")
        raise HTTPException(status_code=400, detail="Failed to create bus")

@router.get("/buses", response_model=List[BusResponse], tags=["Buses"])
async def get_all_buses(status: BusStatus = BusStatus.ALL):
    """Get all buses, optionally filtered by status"""
    if status != BusStatus.ALL:
        query = "SELECT * FROM buses WHERE status = %s ORDER BY created_at DESC"
        buses = execute_query(query, (status.value,), fetch_all=True)
    else:
        query = "SELECT * FROM buses ORDER BY created_at DESC"
        buses = execute_query(query, fetch_all=True)
    return buses or []


@router.get("/buses/{bus_id}", response_model=BusResponse, tags=["Buses"])
async def get_bus(bus_id: str):
    """Get bus by ID"""
    query = "SELECT * FROM buses WHERE bus_id = %s"
    bus = execute_query(query, (bus_id,), fetch_one=True)
    if not bus:
        raise HTTPException(status_code=404, detail="Bus not found")
    return bus

@router.put("/buses/{bus_id}", response_model=BusResponse, tags=["Buses"])
async def update_bus(bus_id: str, bus_update: BusUpdate):
    """Update bus"""
    update_fields = []
    values = []
    
    for field, value in bus_update.dict(exclude_unset=True).items():
        if value is not None:
            update_fields.append(f"{field} = %s")
            values.append(value)
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    values.append(bus_id)
    query = f"UPDATE buses SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE bus_id = %s"
    
    result = execute_query(query, tuple(values))
    if result == 0:
        raise HTTPException(status_code=404, detail="Bus not found")
    
    return await get_bus(bus_id)

@router.put("/buses/{bus_id}/status", response_model=BusResponse, tags=["Buses"])
async def update_bus_status(bus_id: str, status_update: BusStatusUpdate):
    """Update bus status only (ACTIVE, INACTIVE, MAINTENANCE, SCRAP, SPARE)"""
    query = "UPDATE buses SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE bus_id = %s"
    result = execute_query(query, (status_update.status.value, bus_id))
    if result == 0:
        raise HTTPException(status_code=404, detail="Bus not found")
    
    # Trigger cascade updates for bus status
    cascade_service.update_bus_cascades(bus_id, status_update.status.value)
    
    return await get_bus(bus_id)

@router.patch("/buses/{bus_id}/status", response_model=BusResponse, tags=["Buses"])
async def patch_bus_status(bus_id: str, status_update: BusStatusUpdate):
    """PATCH: Update bus status only (ACTIVE, INACTIVE, MAINTENANCE, SCRAP, SPARE)"""
    query = "UPDATE buses SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE bus_id = %s"
    result = execute_query(query, (status_update.status.value, bus_id))
    if result == 0:
        raise HTTPException(status_code=404, detail="Bus not found")
    
    # Trigger cascade updates for bus status
    cascade_service.update_bus_cascades(bus_id, status_update.status.value)
    
    return await get_bus(bus_id)

@router.patch("/buses/{bus_id}/driver", response_model=BusResponse, tags=["Buses"])
async def assign_bus_driver(bus_id: str, assignment: BusDriverAssign):
    """PATCH: Assign or reasssign driver to bus. Set driver_id to null to unassign."""
    # Verify bus exists
    bus = execute_query("SELECT bus_id FROM buses WHERE bus_id = %s", (bus_id,), fetch_one=True)
    if not bus:
        raise HTTPException(status_code=404, detail="Bus not found")

    # If driver_id is provided, verify driver exists
    if assignment.driver_id:
        driver = execute_query("SELECT driver_id FROM drivers WHERE driver_id = %s", (assignment.driver_id,), fetch_one=True)
        if not driver:
            raise HTTPException(status_code=404, detail="Driver not found")
            
    query = "UPDATE buses SET driver_id = %s, updated_at = CURRENT_TIMESTAMP WHERE bus_id = %s"
    logger.info(f"Assigning driver {assignment.driver_id} to bus {bus_id}")
    execute_query(query, (assignment.driver_id, bus_id))
    
    return await get_bus(bus_id)

@router.patch("/buses/{bus_id}/route", response_model=BusResponse, tags=["Buses"])
async def patch_bus_route(bus_id: str, route_data: dict):
    """PATCH: Assign route to bus"""
    route_id = route_data.get("route_id")
    if not route_id:
        raise HTTPException(status_code=400, detail="route_id is required")
    
    query = "UPDATE buses SET route_id = %s, updated_at = CURRENT_TIMESTAMP WHERE bus_id = %s"
    result = execute_query(query, (route_id, bus_id))
    if result == 0:
        raise HTTPException(status_code=404, detail="Bus not found")
    return await get_bus(bus_id)

@router.patch("/buses/{bus_id}/documents", response_model=BusResponse, tags=["Buses"])
async def patch_bus_documents(bus_id: str, documents: dict):
    """PATCH: Update bus document URLs (rc_book_url, fc_certificate_url)"""
    update_fields = []
    values = []
    
    if "rc_book_url" in documents and documents["rc_book_url"]:
        update_fields.append("rc_book_url = %s")
        values.append(documents["rc_book_url"])
    
    if "fc_certificate_url" in documents and documents["fc_certificate_url"]:
        update_fields.append("fc_certificate_url = %s")
        values.append(documents["fc_certificate_url"])
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No document URLs provided")
    
    values.append(bus_id)
    query = f"UPDATE buses SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE bus_id = %s"
    
    result = execute_query(query, tuple(values))
    if result == 0:
        raise HTTPException(status_code=404, detail="Bus not found")
    return await get_bus(bus_id)

@router.post("/uploads/bus/{bus_id}/rc-book", tags=["Buses"])
async def upload_bus_rc_book(bus_id: str, file: UploadFile = File(...)):
    """Upload bus RC Book and clean up old one"""
    bus = execute_query("SELECT bus_id, rc_book_url FROM buses WHERE bus_id = %s", (bus_id,), fetch_one=True)
    if not bus:
        raise HTTPException(status_code=404, detail="Bus not found")
        
    file_url = await upload_service.save_file(file, "buses/rc_books", custom_filename=f"{bus_id}_rc")
    
    query = "UPDATE buses SET rc_book_url = %s, updated_at = CURRENT_TIMESTAMP WHERE bus_id = %s"
    execute_query(query, (file_url, bus_id))

    if bus.get('rc_book_url') and bus['rc_book_url'] != file_url:
        upload_service.delete_file_by_url(bus['rc_book_url'])
        
    return {"url": file_url}

@router.post("/uploads/bus/{bus_id}/fc-certificate", tags=["Buses"])
async def upload_bus_fc_certificate(bus_id: str, file: UploadFile = File(...)):
    """Upload bus FC Certificate and clean up old one"""
    bus = execute_query("SELECT bus_id, fc_certificate_url FROM buses WHERE bus_id = %s", (bus_id,), fetch_one=True)
    if not bus:
        raise HTTPException(status_code=404, detail="Bus not found")
        
    file_url = await upload_service.save_file(file, "buses/fc_certificates", custom_filename=f"{bus_id}_fc")
    
    query = "UPDATE buses SET fc_certificate_url = %s, updated_at = CURRENT_TIMESTAMP WHERE bus_id = %s"
    execute_query(query, (file_url, bus_id))

    if bus.get('fc_certificate_url') and bus['fc_certificate_url'] != file_url:
        upload_service.delete_file_by_url(bus['fc_certificate_url'])
        
    return {"url": file_url}

@router.get("/buses/driver/{driver_id}", response_model=BusResponse, tags=["Buses"])
async def get_bus_by_driver(driver_id: str):
    """Get bus assigned to a specific driver"""
    query = """
    SELECT bus_id, registration_number, driver_id, route_id, vehicle_type, 
           bus_brand, bus_model, seating_capacity, rc_expiry_date, fc_expiry_date,
           rc_book_url, fc_certificate_url, status, created_at, updated_at
    FROM buses 
    WHERE driver_id = %s
    LIMIT 1
    """
    result = execute_query(query, (driver_id,), fetch_one=True)
    if not result:
        raise HTTPException(status_code=404, detail="No bus found for this driver")
    return result

@router.delete("/buses/{bus_id}", tags=["Buses"])
async def delete_bus(bus_id: str):
    """Delete bus"""
    query = "DELETE FROM buses WHERE bus_id = %s"
    result = execute_query(query, (bus_id,))
    if result == 0:
        raise HTTPException(status_code=404, detail="Bus not found")
    return {"message": "Bus deleted successfully"}

# =====================================================
# CLASS ENDPOINTS
# =====================================================

@router.post("/classes", response_model=ClassResponse, tags=["Classes"])
async def create_class(class_data: ClassCreate):
    """Create a new class"""
    try:
        class_id = str(uuid.uuid4())
        query = """
        INSERT INTO classes (class_id, class_name, section)
        VALUES (%s, %s, %s)
        """
        execute_query(query, (class_id, class_data.class_name, class_data.section))
        
        return await get_class(class_id)
    except Exception as e:
        logger.error(f"Create class error: {e}")
        raise HTTPException(status_code=400, detail="Failed to create class")

@router.get("/classes", response_model=List[ClassResponse], tags=["Classes"])
async def get_all_classes():
    """Get all classes with student count"""
    query = """
    SELECT c.*, 
           (SELECT COUNT(*) FROM students s 
            WHERE s.class_id = c.class_id 
            AND s.student_status IN ('ACTIVE', 'CURRENT')) as number_of_students
    FROM classes c 
    ORDER BY c.class_name, c.section
    """
    classes = execute_query(query, fetch_all=True)
    return classes or []

@router.get("/classes/{class_id}", response_model=ClassResponse, tags=["Classes"])
async def get_class(class_id: str):
    """Get class by ID with student count"""
    query = """
    SELECT c.*, 
           (SELECT COUNT(*) FROM students s 
            WHERE s.class_id = c.class_id 
            AND s.student_status IN ('ACTIVE', 'CURRENT')) as number_of_students
    FROM classes c 
    WHERE c.class_id = %s
    """
    class_data = execute_query(query, (class_id,), fetch_one=True)
    if not class_data:
        raise HTTPException(status_code=404, detail="Class not found")
    return class_data

@router.put("/classes/{class_id}", response_model=ClassResponse, tags=["Classes"])
async def update_class(class_id: str, class_update: ClassUpdate):
    """Update class"""
    update_fields = []
    values = []
    
    for field, value in class_update.dict(exclude_unset=True).items():
        if value is not None:
            update_fields.append(f"{field} = %s")
            values.append(value)
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    values.append(class_id)
    query = f"UPDATE classes SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE class_id = %s"
    
    result = execute_query(query, tuple(values))
    if result == 0:
        raise HTTPException(status_code=404, detail="Class not found")
    
    return await get_class(class_id)

@router.put("/classes/{class_id}/status", response_model=ClassResponse, tags=["Classes"])
async def update_class_status(class_id: str, status_update: StatusUpdate):
    """Update class status only"""
    query = "UPDATE classes SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE class_id = %s"
    result = execute_query(query, (status_update.status.value, class_id))
    if result == 0:
        raise HTTPException(status_code=404, detail="Class not found")
    return await get_class(class_id)

@router.delete("/classes/{class_id}", tags=["Classes"])
async def delete_class(class_id: str):
    """Delete class"""
    query = "DELETE FROM classes WHERE class_id = %s"
    result = execute_query(query, (class_id,))
    if result == 0:
        raise HTTPException(status_code=404, detail="Class not found")
    return {"message": "Class deleted successfully"}

@router.get("/classes/{class_id}/fcm-tokens", tags=["Classes"])
async def get_class_fcm_tokens(class_id: str):
    """Get unique parent FCM tokens for a specific class (flat list)"""
    # Verify class exists
    class_check = execute_query("SELECT class_id FROM classes WHERE class_id = %s", (class_id,), fetch_one=True)
    if not class_check:
        raise HTTPException(status_code=404, detail="Class not found")
        
    query = """
    SELECT DISTINCT f.fcm_token
    FROM students s
    JOIN parents p ON (s.parent_id = p.parent_id OR s.s_parent_id = p.parent_id)
    JOIN fcm_tokens f ON p.parent_id = f.parent_id
    WHERE s.class_id = %s AND f.fcm_token IS NOT NULL
    AND p.parents_active_status = 'ACTIVE'
    """
    token_results = execute_query(query, (class_id,), fetch_all=True)
    fcm_tokens = list({row['fcm_token'] for row in token_results}) if token_results else []
    
    return {"fcm_tokens": fcm_tokens}

@router.get("/fcm-tokens/by-class/{class_id}", tags=["FCM Tokens"])
async def get_fcm_tokens_by_class(class_id: str):
    """Get all unique FCM tokens for parents and students in a specific class"""
    query = """
    SELECT DISTINCT f.fcm_token 
    FROM fcm_tokens f
    JOIN students s ON (f.student_id = s.student_id OR f.parent_id = s.parent_id OR f.parent_id = s.s_parent_id)
    WHERE s.class_id = %s AND f.fcm_token IS NOT NULL AND f.fcm_token != ''
    """
    token_results = execute_query(query, (class_id,), fetch_all=True)
    fcm_tokens = list({row['fcm_token'] for row in token_results}) if token_results else []
    return {"fcm_tokens": fcm_tokens, "count": len(fcm_tokens)}

@router.get("/students/by-class/{class_id}", response_model=List[StudentResponse], tags=["Students"])
async def get_students_by_class(class_id: str):
    """Get all students in a specific class"""
    query = "SELECT * FROM students WHERE class_id = %s ORDER BY name"
    students = execute_query(query, (class_id,), fetch_all=True)
    return students or []

@router.get("/classes/{class_id}/parents", response_model=List[ParentResponse], tags=["Classes"])
async def get_class_parents(class_id: str):
    """Get all parents who have students in a specific class"""
    query = """
    SELECT DISTINCT p.parent_id, p.phone, p.email, p.name, p.parent_role, p.door_no, p.street, 
                    p.city, p.district, p.pincode, p.parents_active_status, p.last_login_at, 
                    p.created_at, p.updated_at 
    FROM parents p
    JOIN students s ON (p.parent_id = s.parent_id OR p.parent_id = s.s_parent_id)
    WHERE s.class_id = %s
    ORDER BY p.name
    """
    parents = execute_query(query, (class_id,), fetch_all=True)
    return parents or []

# =====================================================
# STUDENT ENDPOINTS
# =====================================================

@router.post("/students", response_model=StudentResponse, tags=["Students"])
async def create_student(student: StudentCreate):
    """Create a new student"""
    try:
        student_id = str(uuid.uuid4())
        query = """
        INSERT INTO students (student_id, parent_id, s_parent_id, name, gender, dob, study_year, class_id,
                            pickup_route_id, drop_route_id, pickup_stop_id, drop_stop_id,
                            emergency_contact, student_photo_url, is_transport_user,
                            student_status, transport_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        execute_query(query, (student_id, student.parent_id, student.s_parent_id, student.name, student.gender.value,
                             student.dob, student.study_year, student.class_id, student.pickup_route_id, 
                             student.drop_route_id, student.pickup_stop_id, student.drop_stop_id,
                             student.emergency_contact, student.student_photo_url, student.is_transport_user,
                             student.student_status.value, student.transport_status.value))
        
        return await get_student(student_id)
    except Exception as e:
        logger.error(f"Create student error: {e}")
        # Provide more specific error message
        error_msg = str(e)
        if "foreign key constraint" in error_msg.lower():
            if "parent_id" in error_msg:
                raise HTTPException(status_code=400, detail="Invalid parent_id: Parent not found")
            elif "class_id" in error_msg:
                raise HTTPException(status_code=400, detail="Invalid class_id: Class not found")
            elif "pickup_route_id" in error_msg:
                raise HTTPException(status_code=400, detail="Invalid pickup_route_id: Route not found")
            elif "drop_route_id" in error_msg:
                raise HTTPException(status_code=400, detail="Invalid drop_route_id: Route not found")
            elif "pickup_stop_id" in error_msg:
                raise HTTPException(status_code=400, detail="Invalid pickup_stop_id: Stop not found or doesn't belong to the pickup route")
            elif "drop_stop_id" in error_msg:
                raise HTTPException(status_code=400, detail="Invalid drop_stop_id: Stop not found or doesn't belong to the drop route")
            else:
                raise HTTPException(status_code=400, detail=f"Database constraint error: {error_msg}")
        raise HTTPException(status_code=400, detail=f"Failed to create student: {error_msg}")

@router.get("/students", response_model=List[StudentResponse], tags=["Students"])
async def get_all_students(
    student_status: StudentStatus = StudentStatus.ALL,
    transport_status: TransportStatus = TransportStatus.ALL,
    active_filter: ActiveFilter = ActiveFilter.ALL
):
    """Get all students with optional filters. active_filter=ACTIVE_ONLY returns CURRENT students using ACTIVE transport."""
    conditions = []
    params = []
    
    if active_filter == ActiveFilter.ACTIVE_ONLY:
        conditions.append("student_status = 'CURRENT'")
        conditions.append("transport_status = 'ACTIVE'")
        conditions.append("is_transport_user = True")
    else:
        if student_status != StudentStatus.ALL:
            conditions.append("student_status = %s")
            params.append(student_status.value)
        
        if transport_status != TransportStatus.ALL:
            conditions.append("transport_status = %s")
            params.append(transport_status.value)
    
    if conditions:
        query = f"SELECT * FROM students WHERE {' AND '.join(conditions)} ORDER BY created_at DESC"
        students = execute_query(query, tuple(params), fetch_all=True)
    else:
        query = "SELECT * FROM students ORDER BY created_at DESC"
        students = execute_query(query, fetch_all=True)
    
    return students or []


@router.get("/students/by-route/{route_id}", response_model=List[StudentResponse], tags=["Students"])
async def get_students_by_route(route_id: str):
    """Get all students assigned to a specific route (pickup or drop)"""
    query = """
    SELECT * FROM students 
    WHERE pickup_route_id = %s OR drop_route_id = %s
    ORDER BY name
    """
    students = execute_query(query, (route_id, route_id), fetch_all=True)
    return students or []

@router.get("/students/{student_id}", response_model=StudentResponse, tags=["Students"])
async def get_student(student_id: str):
    """Get student by ID"""
    query = "SELECT * FROM students WHERE student_id = %s"
    student = execute_query(query, (student_id,), fetch_one=True)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student

@router.put("/students/{student_id}", response_model=StudentResponse, tags=["Students"])
async def update_student(student_id: str, student_update: StudentUpdate):
    """Update student with cascade updates"""
    try:
        # Get old data for cascade comparison
        old_student = execute_query("SELECT * FROM students WHERE student_id = %s", (student_id,), fetch_one=True)
        if not old_student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        update_fields = []
        values = []
        
        for field, value in student_update.dict(exclude_unset=True).items():
            if value is not None:
                update_fields.append(f"{field} = %s")
                values.append(value)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        values.append(student_id)
        query = f"UPDATE students SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE student_id = %s"
        
        result = execute_query(query, tuple(values))
        if result == 0:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Trigger cascade updates
        new_data = student_update.dict(exclude_unset=True)
        cascade_service.update_student_cascades(student_id, old_student, new_data)
        
        return await get_student(student_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update student error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update student")

@router.put("/students/{student_id}/status", response_model=StudentResponse, tags=["Students"])
async def update_student_status(student_id: str, status_update: StudentStatusUpdate):
    """Update student status only (CURRENT, ALUMNI, DISCONTINUED, LONG_ABSENT)"""
    query = "UPDATE students SET student_status = %s, updated_at = CURRENT_TIMESTAMP WHERE student_id = %s"
    result = execute_query(query, (status_update.status.value, student_id))
    if result == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    return await get_student(student_id)

@router.patch("/students/{student_id}/status", response_model=StudentResponse, tags=["Students"])
async def patch_student_status(student_id: str, status_update: CombinedStatusUpdate):
    """PATCH: Update student status and/or transport status
    
    - student_status: CURRENT, ALUMNI, DISCONTINUED, LONG_ABSENT
    - transport_status: ACTIVE, INACTIVE
    """
    update_fields = []
    values = []
    
    if status_update.student_status:
        update_fields.append("student_status = %s")
        values.append(status_update.student_status.value)
    
    if status_update.transport_status:
        update_fields.append("transport_status = %s")
        values.append(status_update.transport_status.value)
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="At least one status field must be provided")
    
    values.append(student_id)
    query = f"UPDATE students SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE student_id = %s"
    result = execute_query(query, tuple(values))
    if result == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Trigger cascade updates if needed
    cascade_service.update_student_cascades(student_id)
    
    return await get_student(student_id)

@router.post("/uploads/student/{student_id}/photo", tags=["Students"])
async def upload_student_photo(student_id: str, file: UploadFile = File(...)):
    """Upload student photo and delete old one if exists"""
    # Verify student and get old photo
    student = execute_query("SELECT student_id, student_photo_url FROM students WHERE student_id = %s", (student_id,), fetch_one=True)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    # Only allow images
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    # Save file
    file_url = await upload_service.save_file(file, "students", custom_filename=student_id)
    
    # Update database
    try:
        query = "UPDATE students SET student_photo_url = %s, updated_at = CURRENT_TIMESTAMP WHERE student_id = %s"
        execute_query(query, (file_url, student_id))
        
        # Cleanup storage
        if student.get('student_photo_url') and student['student_photo_url'] != file_url:
            upload_service.delete_file_by_url(student['student_photo_url'])
            
    except Exception as e:
        logger.error(f"Failed to update student photo URL: {e}")
        
    return {"url": file_url}

@router.put("/students/{student_id}/transport-status", response_model=StudentResponse, tags=["Students"])
async def update_student_transport_status(student_id: str, status_update: TransportStatusUpdate):
    """Update student transport status only (ACTIVE, INACTIVE)"""
    query = "UPDATE students SET transport_status = %s, updated_at = CURRENT_TIMESTAMP WHERE student_id = %s"
    result = execute_query(query, (status_update.status.value, student_id))
    if result == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Trigger cascade updates (e.g., updating FCM cache for affected routes)
    cascade_service.update_student_cascades(student_id)
    
    return await get_student(student_id)

@router.patch("/students/{student_id}/secondary-parent", response_model=StudentResponse, tags=["Students"])
async def patch_student_secondary_parent(student_id: str, parent_data: SecondaryParentUpdate):
    """PATCH: Assign secondary parent to student. Set to null to unassign."""
    s_parent_id = parent_data.s_parent_id
    
    if s_parent_id:
        # Verify parent exists
        parent_check = execute_query("SELECT parent_id FROM parents WHERE parent_id = %s", (s_parent_id,), fetch_one=True)
        if not parent_check:
            raise HTTPException(status_code=404, detail="Parent not found")
    
    query = "UPDATE students SET s_parent_id = %s, updated_at = CURRENT_TIMESTAMP WHERE student_id = %s"
    result = execute_query(query, (s_parent_id, student_id))
    if result == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Update FCM cache as related parent changed
    cascade_service.update_student_cascades(student_id)
    
    return await get_student(student_id)

@router.patch("/students/{student_id}/primary-parent", response_model=StudentResponse, tags=["Students"])
async def patch_student_primary_parent(student_id: str, parent_data: PrimaryParentUpdate):
    """PATCH: Reassign primary parent to student."""
    parent_id = parent_data.parent_id
    
    # Verify parent exists
    parent_check = execute_query("SELECT parent_id FROM parents WHERE parent_id = %s", (parent_id,), fetch_one=True)
    if not parent_check:
        raise HTTPException(status_code=404, detail="Parent not found")
    
    query = "UPDATE students SET parent_id = %s, updated_at = CURRENT_TIMESTAMP WHERE student_id = %s"
    result = execute_query(query, (parent_id, student_id))
    if result == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Update FCM cache as related parent changed
    cascade_service.update_student_cascades(student_id)
    
    return await get_student(student_id)

@router.patch("/students/{student_id}/photo", response_model=StudentResponse, tags=["Students"])
async def patch_student_photo(student_id: str, photo_data: StudentPhotoUpdate):
    """PATCH: Update student photo URL"""
    query = "UPDATE students SET student_photo_url = %s, updated_at = CURRENT_TIMESTAMP WHERE student_id = %s"
    result = execute_query(query, (photo_data.student_photo_url, student_id))
    if result == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    return await get_student(student_id)

@router.post("/students/{student_id}/switch-parents", response_model=StudentResponse, tags=["Students"])
async def switch_student_parents(student_id: str):
    """POST: Swap primary and secondary parents for a student."""
    try:
        # Get current parents
        student = execute_query("SELECT parent_id, s_parent_id FROM students WHERE student_id = %s", (student_id,), fetch_one=True)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        old_primary = student['parent_id']
        old_secondary = student['s_parent_id']
        
        if not old_secondary:
            raise HTTPException(status_code=400, detail="Student does not have a secondary parent to switch with")
        
        # Swap them
        query = "UPDATE students SET parent_id = %s, s_parent_id = %s, updated_at = CURRENT_TIMESTAMP WHERE student_id = %s"
        execute_query(query, (old_secondary, old_primary, student_id))
        
        # Update FCM cache
        cascade_service.update_student_cascades(student_id)
        
        return await get_student(student_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Switch parents error: {e}")
        raise HTTPException(status_code=500, detail="Failed to switch parents")

@router.patch("/students/{student_id}/upgrade", response_model=StudentResponse, tags=["Students"])
async def upgrade_single_student(student_id: str, upgrade_data: ClassUpgradeRequest):
    """PATCH: Upgrade a single student to a new class and optionally a new study year."""
    try:
        # Verify class exists
        class_check = execute_query("SELECT class_id FROM classes WHERE class_id = %s", (upgrade_data.new_class_id,), fetch_one=True)
        if not class_check:
            raise HTTPException(status_code=404, detail="New class not found")
        
        update_fields = ["class_id = %s"]
        params = [upgrade_data.new_class_id]
        
        if upgrade_data.new_study_year:
            update_fields.append("study_year = %s")
            params.append(upgrade_data.new_study_year)
            
        params.append(student_id)
        
        query = f"UPDATE students SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE student_id = %s"
        result = execute_query(query, tuple(params))
        
        if result == 0:
            raise HTTPException(status_code=404, detail="Student not found")
            
        return await get_student(student_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upgrade student error: {e}")
        raise HTTPException(status_code=500, detail="Failed to upgrade student")

@router.post("/students/bulk-upgrade-class", response_model=UpgradeResponse, tags=["Students"])
async def bulk_upgrade_class(upgrade_data: BulkClassUpgradeRequest):
    """POST: Upgrade all students from one class to another."""
    try:
        # Verify both classes exist
        curr_class = execute_query("SELECT class_id FROM classes WHERE class_id = %s", (upgrade_data.current_class_id,), fetch_one=True)
        if not curr_class:
            raise HTTPException(status_code=404, detail="Current class not found")
            
        new_class = execute_query("SELECT class_id FROM classes WHERE class_id = %s", (upgrade_data.new_class_id,), fetch_one=True)
        if not new_class:
            raise HTTPException(status_code=404, detail="New class not found")
            
        update_fields = ["class_id = %s"]
        params = [upgrade_data.new_class_id]
        
        if upgrade_data.new_study_year:
            update_fields.append("study_year = %s")
            params.append(upgrade_data.new_study_year)
            
        params.append(upgrade_data.current_class_id)
        
        query = f"UPDATE students SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE class_id = %s"
        affected_rows = execute_query(query, tuple(params))
        
        # If any students were upgraded, we might need to update route FCM caches
        # For simplicity, we can log this. In a real-world scenario, we might want to trigger cache updates for all affected routes.
        if affected_rows > 0:
            logger.info(f"Bulk upgraded {affected_rows} students from {upgrade_data.current_class_id} to {upgrade_data.new_class_id}")
            # Note: Cascade updates for all individual students might be expensive here.
            # Usually class upgrades don't change routes, so FCM cache might still be valid.
        
        return {
            "message": f"Successfully upgraded {affected_rows} students",
            "affected_students": affected_rows
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk upgrade error: {e}")
        raise HTTPException(status_code=500, detail="Failed to perform bulk upgrade")

@router.post("/classes/promote-all", response_model=BulkPromoteResponse, tags=["Classes"])
async def promote_all_classes(promote_data: BulkPromoteRequest):
    """
    Promote ALL students to the next class (increment class number by 1).
    
    Example: Class 9 A → Class 10 A, Class 10 A → Class 11 A
    
    - Students in the max_class (default 12) will be marked as ALUMNI
    - Each student keeps their same section (A stays in A, B stays in B)
    - Optionally updates the study_year for all students
    """
    try:
        max_class = promote_data.max_class or 12
        
        # Get all active classes ordered by class number descending (process highest first to avoid conflicts)
        all_classes = execute_query(
            "SELECT class_id, class_name, section FROM classes WHERE status = 'ACTIVE' ORDER BY class_name DESC, section",
            fetch_all=True
        )
        
        if not all_classes:
            raise HTTPException(status_code=404, detail="No active classes found")
        
        details = []
        total_promoted = 0
        graduated_count = 0
        classes_processed = 0
        
        for cls in all_classes:
            class_name = cls['class_name']
            section = cls['section']
            class_id = cls['class_id']
            
            # Extract the numeric part from class_name (e.g., "10" from "10", "Class 9" from "Class  9")
            import re
            numbers = re.findall(r'\d+', class_name)
            if not numbers:
                details.append({"class": class_name, "section": section, "status": "skipped", "reason": "No numeric class number found"})
                continue
            
            current_num = int(numbers[-1])  # Take the last number found
            
            # Check if at max class (graduation)
            if current_num >= max_class:
                # Count graduating students
                grad_count = execute_query(
                    "SELECT COUNT(*) as cnt FROM students WHERE class_id = %s AND student_status IN ('ACTIVE','CURRENT')",
                    (class_id,), fetch_one=True
                )
                grad = grad_count['cnt'] if grad_count else 0
                if grad > 0:
                    # Mark students as ALUMNI
                    execute_query(
                        "UPDATE students SET student_status = 'ALUMNI', updated_at = CURRENT_TIMESTAMP WHERE class_id = %s AND student_status IN ('ACTIVE','CURRENT')",
                        (class_id,)
                    )
                    graduated_count += grad
                    details.append({"class": class_name, "section": section, "status": "alumni", "students": grad})
                continue
            
            # Find the next class (current_num + 1) with the same section
            next_num = current_num + 1
            # Build search pattern - try exact match first
            next_class = execute_query(
                "SELECT class_id, class_name FROM classes WHERE section = %s AND status = 'ACTIVE' AND class_id != %s",
                (section, class_id), fetch_all=True
            )
            
            # Find the target class that has next_num in its name
            target_class = None
            for nc in (next_class or []):
                nc_numbers = re.findall(r'\d+', nc['class_name'])
                if nc_numbers and int(nc_numbers[-1]) == next_num:
                    target_class = nc
                    break
            
            if not target_class:
                # Auto-create the next class if it doesn't exist
                new_class_id = str(uuid.uuid4())
                new_class_name = class_name.replace(str(current_num), str(next_num))
                execute_query(
                    "INSERT INTO classes (class_id, class_name, section) VALUES (%s, %s, %s)",
                    (new_class_id, new_class_name, section)
                )
                target_class = {"class_id": new_class_id, "class_name": new_class_name}
                details.append({"class": new_class_name, "section": section, "status": "auto_created"})
            
            # Move students from current class to target class
            update_fields = "class_id = %s"
            params = [target_class['class_id']]
            
            if promote_data.new_study_year:
                update_fields += ", study_year = %s"
                params.append(promote_data.new_study_year)
            
            params.append(class_id)
            promoted = execute_query(
                f"UPDATE students SET {update_fields}, updated_at = CURRENT_TIMESTAMP WHERE class_id = %s AND student_status IN ('ACTIVE','CURRENT')",
                tuple(params)
            )
            
            if promoted and promoted > 0:
                total_promoted += promoted
                classes_processed += 1
                details.append({
                    "from_class": class_name, 
                    "to_class": target_class['class_name'],
                    "section": section, 
                    "status": "promoted", 
                    "students_moved": promoted
                })
        
        return {
            "message": f"Promotion complete! {total_promoted} students promoted across {classes_processed} classes. {graduated_count} students moved to ALUMNI status.",
            "total_classes_processed": classes_processed,
            "total_students_promoted": total_promoted,
            "graduated_students": graduated_count,
            "details": details
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Promote all classes error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to promote classes: {str(e)}")

@router.post("/classes/demote-all", response_model=BulkPromoteResponse, tags=["Classes"])
async def demote_all_classes(demote_data: BulkDemoteRequest):
    """
    Demote ALL students to the previous class (decrement class number by 1).
    
    Example: Class 10 A → Class 9 A, Class 11 A → Class 10 A
    
    - Students in the min_class (default 1) will NOT be demoted
    - Each student keeps their same section
    - Optionally updates the study_year for all students
    """
    try:
        min_class = demote_data.min_class or 1
        
        # Get all active classes ordered by class number ascending (process lowest first)
        all_classes = execute_query(
            "SELECT class_id, class_name, section FROM classes WHERE status = 'ACTIVE' ORDER BY class_name ASC, section",
            fetch_all=True
        )
        
        if not all_classes:
            raise HTTPException(status_code=404, detail="No active classes found")
        
        import re
        details = []
        total_demoted = 0
        classes_processed = 0
        
        for cls in all_classes:
            class_name = cls['class_name']
            section = cls['section']
            class_id = cls['class_id']
            
            numbers = re.findall(r'\d+', class_name)
            if not numbers:
                details.append({"class": class_name, "section": section, "status": "skipped", "reason": "No numeric class number found"})
                continue
            
            current_num = int(numbers[-1])
            
            # Skip if at minimum class
            if current_num <= min_class:
                details.append({"class": class_name, "section": section, "status": "skipped", "reason": f"Already at minimum class ({min_class})"})
                continue
            
            # Find the previous class (current_num - 1) with the same section  
            prev_num = current_num - 1
            prev_classes = execute_query(
                "SELECT class_id, class_name FROM classes WHERE section = %s AND status = 'ACTIVE' AND class_id != %s",
                (section, class_id), fetch_all=True
            )
            
            target_class = None
            for pc in (prev_classes or []):
                pc_numbers = re.findall(r'\d+', pc['class_name'])
                if pc_numbers and int(pc_numbers[-1]) == prev_num:
                    target_class = pc
                    break
            
            if not target_class:
                # Auto-create the previous class if it doesn't exist
                new_class_id = str(uuid.uuid4())
                new_class_name = class_name.replace(str(current_num), str(prev_num))
                execute_query(
                    "INSERT INTO classes (class_id, class_name, section) VALUES (%s, %s, %s)",
                    (new_class_id, new_class_name, section)
                )
                target_class = {"class_id": new_class_id, "class_name": new_class_name}
                details.append({"class": new_class_name, "section": section, "status": "auto_created"})
            
            # Move students from current class to target class
            update_fields = "class_id = %s"
            params = [target_class['class_id']]
            
            if demote_data.new_study_year:
                update_fields += ", study_year = %s"
                params.append(demote_data.new_study_year)
            
            params.append(class_id)
            demoted = execute_query(
                f"UPDATE students SET {update_fields}, updated_at = CURRENT_TIMESTAMP WHERE class_id = %s AND student_status IN ('ACTIVE','CURRENT')",
                tuple(params)
            )
            
            if demoted and demoted > 0:
                total_demoted += demoted
                classes_processed += 1
                details.append({
                    "from_class": class_name,
                    "to_class": target_class['class_name'],
                    "section": section,
                    "status": "demoted",
                    "students_moved": demoted
                })
        
        return {
            "message": f"Demotion complete! {total_demoted} students demoted across {classes_processed} classes.",
            "total_classes_processed": classes_processed,
            "total_students_promoted": total_demoted,
            "graduated_students": 0,
            "details": details
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Demote all classes error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to demote classes: {str(e)}")

@router.delete("/students/{student_id}", tags=["Students"])
async def delete_student(student_id: str):
    """Delete student with cascade cleanup"""
    try:
        # Get student data for cascade cleanup
        student_data = execute_query("SELECT * FROM students WHERE student_id = %s", (student_id,), fetch_one=True)
        if not student_data:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Perform cascade cleanup
        cascade_service.delete_cascades("students", student_id, student_data)
        
        # Delete student
        query = "DELETE FROM students WHERE student_id = %s"
        result = execute_query(query, (student_id,))
        if result == 0:
            raise HTTPException(status_code=404, detail="Student not found")
        
        return {"message": "Student deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete student error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete student")

# =====================================================
# TRIP ENDPOINTS
# =====================================================

@router.post("/trips", response_model=TripResponse, tags=["Trips"])
async def create_trip(trip: TripCreate):
    """Create a new trip"""
    try:
        trip_id = str(uuid.uuid4())
        query = """
        INSERT INTO trips (trip_id, bus_id, driver_id, route_id, trip_date, trip_type)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        execute_query(query, (trip_id, trip.bus_id, trip.driver_id, trip.route_id,
                             trip.trip_date, trip.trip_type))
        
        return await get_trip(trip_id)
    except Exception as e:
        logger.error(f"Create trip error: {e}")
        raise HTTPException(status_code=400, detail="Failed to create trip")

@router.get("/trips", response_model=List[TripResponse], tags=["Trips"])
async def get_all_trips():
    """Get all trips"""
    query = "SELECT * FROM trips ORDER BY trip_date DESC, created_at DESC"
    trips = execute_query(query, fetch_all=True)
    return trips or []

@router.get("/trips/{trip_id}", response_model=TripResponse, tags=["Trips"])
async def get_trip(trip_id: str):
    """Get trip by ID"""
    query = "SELECT * FROM trips WHERE trip_id = %s"
    trip = execute_query(query, (trip_id,), fetch_one=True)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip

@router.get("/trips/ongoing/all", response_model=List[TripResponse], tags=["Trips"])
async def get_active_trips():
    """Get all ongoing trips"""
    query = "SELECT * FROM trips WHERE status = 'ONGOING' ORDER BY started_at DESC"
    trips = execute_query(query, fetch_all=True)
    return trips or []

@router.put("/trips/{trip_id}", response_model=TripResponse, tags=["Trips"])
async def update_trip(trip_id: str, trip_update: TripUpdate):
    """Update trip"""
    update_fields = []
    values = []
    
    for field, value in trip_update.dict(exclude_unset=True).items():
        update_fields.append(f"{field} = %s")
        values.append(value)
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    values.append(trip_id)
    query = f"UPDATE trips SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE trip_id = %s"
    
    result = execute_query(query, tuple(values))
    if result == 0:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    return await get_trip(trip_id)

@router.put("/trips/{trip_id}/status", response_model=TripResponse, tags=["Trips"])
async def update_trip_status(trip_id: str, status_update: TripStatusUpdate):
    """Update trip status only"""
    query = "UPDATE trips SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE trip_id = %s"
    result = execute_query(query, (status_update.status.value, trip_id))
    if result == 0:
        raise HTTPException(status_code=404, detail="Trip not found")
    return await get_trip(trip_id)

@router.delete("/trips/{trip_id}", tags=["Trips"])
async def delete_trip(trip_id: str):
    """Delete trip"""
    query = "DELETE FROM trips WHERE trip_id = %s"
    result = execute_query(query, (trip_id,))
    if result == 0:
        raise HTTPException(status_code=404, detail="Trip not found")
    return {"message": "Trip deleted successfully"}

# =====================================================
# ERROR HANDLING ENDPOINTS
# =====================================================

@router.post("/error-handling", response_model=ErrorHandlingResponse, tags=["Error Handling"])
async def create_error_log(error: ErrorHandlingCreate):
    """Create a new error log"""
    try:
        error_id = str(uuid.uuid4())
        query = """
        INSERT INTO error_logs (error_id, error_type, error_code, error_description)
        VALUES (%s, %s, %s, %s)
        """
        execute_query(query, (error_id, error.error_type, error.error_code, error.error_description))
        
        return await get_error_log(error_id)
    except Exception as e:
        logger.error(f"Create error log error: {e}")
        raise HTTPException(status_code=400, detail="Failed to create error log")

@router.get("/error-handling", response_model=List[ErrorHandlingResponse], tags=["Error Handling"])
async def get_all_error_logs():
    """Get all error logs"""
    query = "SELECT * FROM error_logs ORDER BY created_at DESC"
    errors = execute_query(query, fetch_all=True)
    return errors or []

@router.get("/error-handling/{error_id}", response_model=ErrorHandlingResponse, tags=["Error Handling"])
async def get_error_log(error_id: str):
    """Get error log by ID"""
    query = "SELECT * FROM error_logs WHERE error_id = %s"
    error = execute_query(query, (error_id,), fetch_one=True)
    if not error:
        raise HTTPException(status_code=404, detail="Error log not found")
    return error

@router.put("/error-handling/{error_id}", response_model=ErrorHandlingResponse, tags=["Error Handling"])
async def update_error_log(error_id: str, error_update: ErrorHandlingUpdate):
    """Update error log"""
    update_fields = []
    values = []
    
    for field, value in error_update.dict(exclude_unset=True).items():
        if value is not None:
            update_fields.append(f"{field} = %s")
            values.append(value)
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    values.append(error_id)
    query = f"UPDATE error_handling SET {', '.join(update_fields)} WHERE error_id = %s"
    
    result = execute_query(query, tuple(values))
    if result == 0:
        raise HTTPException(status_code=404, detail="Error log not found")
    
    return await get_error_log(error_id)

@router.delete("/error-handling/{error_id}", tags=["Error Handling"])
async def delete_error_log(error_id: str):
    """Delete error log"""
    query = "DELETE FROM error_logs WHERE error_id = %s"
    result = execute_query(query, (error_id,))
    if result == 0:
        raise HTTPException(status_code=404, detail="Error log not found")
    return {"message": "Error log deleted successfully"}


# =====================================================
# UTILITY ENDPOINTS
# =====================================================

@router.get("/students/by-parent/{parent_id}", response_model=List[StudentResponse], tags=["Students"])
async def get_students_by_parent(parent_id: str, active_only: bool = True):
    """Get students for a parent. By default, only returns active transport users."""
    if active_only:
        query = """
        SELECT * FROM students 
        WHERE (parent_id = %s OR s_parent_id = %s) 
        AND student_status = 'CURRENT' 
        AND transport_status = 'ACTIVE'
        AND is_transport_user = True
        ORDER BY name
        """
    else:
        query = "SELECT * FROM students WHERE parent_id = %s OR s_parent_id = %s ORDER BY name"
    
    students = execute_query(query, (parent_id, parent_id), fetch_all=True)
    return students or []

@router.get("/trips/by-driver/{driver_id}", response_model=List[TripResponse], tags=["Trips"])
async def get_trips_by_driver(driver_id: str):
    """Get all trips for a specific driver"""
    query = "SELECT * FROM trips WHERE driver_id = %s ORDER BY trip_date DESC"
    trips = execute_query(query, (driver_id,), fetch_all=True)
    return trips or []

@router.get("/trips/by-route/{route_id}", response_model=List[TripResponse], tags=["Trips"])
async def get_trips_by_route(route_id: str):
    """Get all trips for a specific route"""
    query = "SELECT * FROM trips WHERE route_id = %s ORDER BY trip_date DESC"
    trips = execute_query(query, (route_id,), fetch_all=True)
    return trips or []

@router.get("/students/by-route/{route_id}", response_model=List[StudentResponse], tags=["Students"])
async def get_students_by_route(route_id: str, active_filter: ActiveFilter = ActiveFilter.ACTIVE_ONLY):
    """Get students on a route. By default, only returns active transport users."""
    if active_filter == ActiveFilter.ACTIVE_ONLY:
        query = """
        SELECT * FROM students 
        WHERE (pickup_route_id = %s OR drop_route_id = %s) 
        AND (student_status = 'CURRENT' OR student_status = 'ACTIVE')
        AND transport_status = 'ACTIVE'
        AND is_transport_user = True
        ORDER BY name
        """
    else:
        query = """
        SELECT * FROM students 
        WHERE pickup_route_id = %s OR drop_route_id = %s 
        ORDER BY name
        """
    
    students = execute_query(query, (route_id, route_id), fetch_all=True)
    return students or []


@router.get("/parents/by-route/{route_id}", response_model=List[ParentResponse], tags=["Parents"])
async def get_parents_by_route(route_id: str):
    """Get all parents who have students on a specific route"""
    query = """
    SELECT DISTINCT p.parent_id, p.phone, p.email, p.name, p.parent_role, p.door_no, p.street, 
                    p.city, p.district, p.pincode, p.parents_active_status, p.last_login_at, 
                    p.created_at, p.updated_at 
    FROM parents p
    JOIN students s ON (p.parent_id = s.parent_id OR p.parent_id = s.s_parent_id)
    WHERE s.pickup_route_id = %s OR s.drop_route_id = %s
    ORDER BY p.name
    """
    parents = execute_query(query, (route_id, route_id), fetch_all=True)
    return parents or []

@router.get("/students/count/by-route/{route_id}", tags=["Students"])
async def get_student_count_by_route(route_id: str):
    """Get the total count of students on a specific route"""
    query = """
    SELECT COUNT(DISTINCT student_id) as student_count FROM students 
    WHERE pickup_route_id = %s OR drop_route_id = %s
    """
    result = execute_query(query, (route_id, route_id), fetch_one=True)
    return {"route_id": route_id, "student_count": result["student_count"] if result else 0}

# =====================================================
# FCM TOKEN ENDPOINTS
# =====================================================

@router.post("/fcm-tokens", response_model=FCMTokenResponse, tags=["FCM Tokens"])
async def create_fcm_token(fcm_token: FCMTokenCreate):
    """Create or update FCM token with Force Logout for single device login"""
    try:
        fcm_id = str(uuid.uuid4())
        
        # Logic for Parent Single Device Login (Force Logout)
        if fcm_token.parent_id:
            # Check if parent already has an FCM token
            old_token_query = "SELECT fcm_token FROM fcm_tokens WHERE parent_id = %s"
            old_token_data = execute_query(old_token_query, (fcm_token.parent_id,), fetch_one=True)
            
            # If old token exists and is different from the new one
            if old_token_data and old_token_data['fcm_token'] != fcm_token.fcm_token:
                logger.info(f"Force logging out old device for parent: {fcm_token.parent_id}")
                # 1. Send FCM notification to old token with logout command
                await notification_service.send_force_logout(old_token_data['fcm_token'])
                
                # 2. Delete old token from database to maintain single device rule
                delete_query = "DELETE FROM fcm_tokens WHERE parent_id = %s"
                execute_query(delete_query, (fcm_token.parent_id,))

        # 3. Save/Update new token
        query = """
        INSERT INTO fcm_tokens (fcm_id, fcm_token, student_id, parent_id)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        student_id = VALUES(student_id),
        parent_id = VALUES(parent_id),
        updated_at = CURRENT_TIMESTAMP
        """
        execute_query(query, (fcm_id, fcm_token.fcm_token, fcm_token.student_id, fcm_token.parent_id))
        
        # Get the actual ID of the token (either new or updated)
        # If it was updated, we need to find the ID by token
        final_token = execute_query("SELECT fcm_id FROM fcm_tokens WHERE fcm_token = %s", (fcm_token.fcm_token,), fetch_one=True)
        return await get_fcm_token(final_token['fcm_id'])
    except Exception as e:
        logger.error(f"Create FCM token error: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to create FCM token: {str(e)}")


@router.get("/fcm-tokens", tags=["FCM Tokens"])
async def get_all_fcm_tokens():
    """Get all unique FCM tokens (flat list)"""
    query = "SELECT DISTINCT fcm_token FROM fcm_tokens WHERE fcm_token IS NOT NULL"
    token_results = execute_query(query, fetch_all=True)
    fcm_tokens = list({row['fcm_token'] for row in token_results}) if token_results else []
    return {"fcm_tokens": fcm_tokens}

@router.get("/fcm-tokens/{fcm_id}", response_model=FCMTokenResponse, tags=["FCM Tokens"])
async def get_fcm_token(fcm_id: str):
    """Get FCM token by ID"""
    query = "SELECT * FROM fcm_tokens WHERE fcm_id = %s"
    token = execute_query(query, (fcm_id,), fetch_one=True)
    if not token:
        raise HTTPException(status_code=404, detail="FCM token not found")
    return token

@router.get("/fcm-tokens/by-student/{student_id}", tags=["FCM Tokens"])
async def get_fcm_tokens_by_student(student_id: str):
    """Get unique FCM tokens registered for a specific student"""
    query = "SELECT DISTINCT fcm_token FROM fcm_tokens WHERE student_id = %s"
    token_results = execute_query(query, (student_id,), fetch_all=True)
    fcm_tokens = list({row['fcm_token'] for row in token_results}) if token_results else []
    return {"fcm_tokens": fcm_tokens}

@router.get("/fcm-tokens/by-parent/{parent_id}", tags=["FCM Tokens"])
async def get_fcm_tokens_by_parent(parent_id: str):
    """Get unique FCM tokens registered for a specific parent"""
    query = "SELECT DISTINCT fcm_token FROM fcm_tokens WHERE parent_id = %s"
    token_results = execute_query(query, (parent_id,), fetch_all=True)
    fcm_tokens = list({row['fcm_token'] for row in token_results}) if token_results else []
    return {"fcm_tokens": fcm_tokens}

@router.get("/fcm-tokens/by-class/{class_id}", tags=["FCM Tokens"])
async def get_fcm_tokens_by_class(class_id: str):
    """Get all unique FCM tokens for parents and students in a specific class"""
    query = """
    SELECT DISTINCT f.fcm_token 
    FROM fcm_tokens f
    JOIN students s ON (f.student_id = s.student_id OR f.parent_id = s.parent_id OR f.parent_id = s.s_parent_id)
    WHERE s.class_id = %s AND f.fcm_token IS NOT NULL AND f.fcm_token != ''
    """
    token_results = execute_query(query, (class_id,), fetch_all=True)
    fcm_tokens = list({row['fcm_token'] for row in token_results}) if token_results else []
    return {"fcm_tokens": fcm_tokens, "count": len(fcm_tokens)}

@router.put("/fcm-tokens/{fcm_id}", response_model=FCMTokenResponse, tags=["FCM Tokens"])
async def update_fcm_token(fcm_id: str, fcm_update: FCMTokenUpdate):
    """Update FCM token with cascade updates"""
    try:
        # Get old data for cascade comparison
        old_token = execute_query("SELECT * FROM fcm_tokens WHERE fcm_id = %s", (fcm_id,), fetch_one=True)
        if not old_token:
            raise HTTPException(status_code=404, detail="FCM token not found")
        
        update_fields = []
        values = []
        
        for field, value in fcm_update.dict(exclude_unset=True).items():
            if value is not None:
                update_fields.append(f"{field} = %s")
                values.append(value)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        values.append(fcm_id)
        query = f"UPDATE fcm_tokens SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE fcm_id = %s"
        
        result = execute_query(query, tuple(values))
        if result == 0:
            raise HTTPException(status_code=404, detail="FCM token not found")
        
        # Trigger cascade updates
        new_data = fcm_update.dict(exclude_unset=True)
        cascade_service.update_fcm_token_cascades(fcm_id, old_token, new_data)
        
        return await get_fcm_token(fcm_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update FCM token error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update FCM token")

@router.get("/fcm-tokens/by-route/{route_id}", tags=["FCM Tokens"])
async def get_fcm_tokens_by_route(route_id: str):
    """Get FCM tokens for all stops in a route"""
    try:
        query = """
        SELECT 
            rs.stop_id,
            rs.stop_name,
            rs.pickup_stop_order,
            rs.drop_stop_order,
            s.student_id,
            s.name as student_name,
            ft.fcm_token,
            ft.parent_id,
            p.name as parent_name
        FROM route_stops rs
        LEFT JOIN students s ON (
            (rs.stop_id = s.pickup_stop_id AND s.pickup_route_id = rs.route_id) OR
            (rs.stop_id = s.drop_stop_id AND s.drop_route_id = rs.route_id)
        ) AND s.transport_status = 'ACTIVE' AND s.student_status = 'CURRENT' AND s.is_transport_user = True
        LEFT JOIN fcm_tokens ft ON (s.student_id = ft.student_id OR s.parent_id = ft.parent_id OR s.s_parent_id = ft.parent_id)
        LEFT JOIN parents p ON ft.parent_id = p.parent_id
        WHERE rs.route_id = %s
        ORDER BY rs.pickup_stop_order, s.name
        """
        
        results = execute_query(query, (route_id,), fetch_all=True)
        
        # Also catch students on this route who DON'T have a stop assigned
        unassigned_query = """
        SELECT 
            s.student_id,
            s.name as student_name,
            ft.fcm_token,
            ft.parent_id,
            p.name as parent_name
        FROM students s
        LEFT JOIN fcm_tokens ft ON (s.student_id = ft.student_id OR s.parent_id = ft.parent_id OR s.s_parent_id = ft.parent_id)
        LEFT JOIN parents p ON ft.parent_id = p.parent_id
        WHERE (s.pickup_route_id = %s OR s.drop_route_id = %s)
        AND s.pickup_stop_id IS NULL AND s.drop_stop_id IS NULL
        AND s.transport_status = 'ACTIVE' AND s.student_status = 'CURRENT' AND s.is_transport_user = True
        """
        unassigned_results = execute_query(unassigned_query, (route_id, route_id), fetch_all=True)

        # Group by stops
        stops_data = {}
        for row in results:
            stop_id = row['stop_id']
            if stop_id not in stops_data:
                stops_data[stop_id] = {
                    "stop_id": stop_id,
                    "stop_name": row['stop_name'],
                    "pickup_stop_order": row['pickup_stop_order'],
                    "drop_stop_order": row['drop_stop_order'],
                    "fcm_tokens": []
                }
            
            if row['fcm_token']:
                # Ensure each stop has unique tokens
                existing_tokens = {t['fcm_token'] for t in stops_data[stop_id]["fcm_tokens"]}
                if row['fcm_token'] not in existing_tokens:
                    token_entry = {
                        "fcm_token": row['fcm_token'],
                        "parent_id": row['parent_id'],
                        "parent_name": row['parent_name']
                    }
                    stops_data[stop_id]["fcm_tokens"].append(token_entry)
        
        # Add unassigned students if any
        if unassigned_results:
            unassigned_stop_id = "unassigned"
            stops_data[unassigned_stop_id] = {
                "stop_id": "unassigned",
                "stop_name": "Unassigned/General Route",
                "pickup_stop_order": 999,
                "drop_stop_order": 999,
                "fcm_tokens": []
            }
            for row in unassigned_results:
                if row['fcm_token']:
                    existing_tokens = {t['fcm_token'] for t in stops_data[unassigned_stop_id]["fcm_tokens"]}
                    if row['fcm_token'] not in existing_tokens:
                        token_entry = {
                            "fcm_token": row['fcm_token'],
                            "parent_id": row['parent_id'],
                            "parent_name": row['parent_name']
                        }
                        stops_data[unassigned_stop_id]["fcm_tokens"].append(token_entry)

        return {
            "route_id": route_id,
            "stops": list(stops_data.values()),
            "total_stops": len(stops_data),
            "total_tokens": sum(len(stop["fcm_tokens"]) for stop in stops_data.values())
        }
        
    except Exception as e:
        logger.error(f"Get FCM tokens by route error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get FCM tokens by route")

@router.get("/fcm-tokens/by-stop/{stop_id}", tags=["FCM Tokens"])
async def get_fcm_tokens_by_stop(stop_id: str):
    """Get FCM tokens for one specific stop"""
    try:
        query = """
        SELECT 
            rs.stop_id,
            rs.stop_name,
            rs.pickup_stop_order,
            rs.drop_stop_order,
            s.student_id,
            s.name as student_name,
            ft.fcm_token,
            ft.parent_id,
            p.name as parent_name
        FROM route_stops rs
        LEFT JOIN students s ON (
            (rs.stop_id = s.pickup_stop_id) OR
            (rs.stop_id = s.drop_stop_id)
        ) AND s.transport_status = 'ACTIVE' AND s.student_status = 'CURRENT' AND s.is_transport_user = True
        LEFT JOIN fcm_tokens ft ON (s.student_id = ft.student_id OR s.parent_id = ft.parent_id OR s.s_parent_id = ft.parent_id)
        LEFT JOIN parents p ON ft.parent_id = p.parent_id
        WHERE rs.stop_id = %s 
        ORDER BY s.name
        """
        
        results = execute_query(query, (stop_id,), fetch_all=True)
        
        if not results:
            raise HTTPException(status_code=404, detail="Stop not found")
        
        fcm_tokens = []
        stop_info = None
        
        for row in results:
            if not stop_info:
                stop_info = {
                    "stop_id": row['stop_id'],
                    "stop_name": row['stop_name'],
                    "pickup_stop_order": row['pickup_stop_order'],
                    "drop_stop_order": row['drop_stop_order']
                }
            
            if row['fcm_token']:
                existing_tokens = {t['fcm_token'] for t in fcm_tokens}
                if row['fcm_token'] not in existing_tokens:
                    token_entry = {
                        "fcm_token": row['fcm_token'],
                        "parent_id": row['parent_id'],
                        "parent_name": row['parent_name']
                    }
                    fcm_tokens.append(token_entry)
        
        return {
            "stop_info": stop_info,
            "fcm_tokens": fcm_tokens,
            "total_tokens": len(fcm_tokens)
        }
        
    except Exception as e:
        logger.error(f"Get FCM tokens by stop error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get FCM tokens by stop")

@router.delete("/fcm-tokens/{fcm_id}", tags=["FCM Tokens"])
async def delete_fcm_token(fcm_id: str):
    """Delete FCM token"""
    query = "DELETE FROM fcm_tokens WHERE fcm_id = %s"
    result = execute_query(query, (fcm_id,))
    if result == 0:
        raise HTTPException(status_code=404, detail="FCM token not found")
    return {"message": "FCM token deleted successfully"}

# =====================================================
# BUS TRACKING ENDPOINTS
# =====================================================

@router.post("/bus-tracking/location", tags=["Bus Tracking"])
async def update_bus_location(location_data: BusLocationUpdate):
    """Automatic bus tracking - handles stop progression and trip completion"""
    try:
        result = await bus_tracking_service.update_bus_location(
            trip_id=location_data.trip_id,
            latitude=location_data.latitude,
            longitude=location_data.longitude
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("message", "Failed to process location"))
            
    except Exception as e:
        logger.error(f"Bus location processing error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process bus location")

@router.post("/bus-tracking/notify", tags=["Bus Tracking"])
async def send_custom_notification(notification: NotificationRequest):
    """Send custom notification to parents"""
    try:
        # Get trip details
        trip_query = "SELECT * FROM trips WHERE trip_id = %s"
        trip = execute_query(trip_query, (notification.trip_id,), fetch_one=True)
        
        if not trip:
            raise HTTPException(status_code=404, detail="Trip not found")
        
        # Get students for the route
        if notification.stop_id:
            students_query = """
            SELECT s.student_id FROM students s
            WHERE (s.pickup_stop_id = %s OR s.drop_stop_id = %s)
            AND s.transport_status = 'ACTIVE'
            AND s.student_status = 'CURRENT'
            AND s.is_transport_user = True
            """
            students = execute_query(students_query, (notification.stop_id, notification.stop_id), fetch_all=True)
        else:
            students_query = """
            SELECT s.student_id FROM students s
            WHERE (s.pickup_route_id = %s OR s.drop_route_id = %s)
            AND s.transport_status = 'ACTIVE'
            AND s.student_status = 'CURRENT'
            AND s.is_transport_user = True
            """
            students = execute_query(students_query, (trip['route_id'], trip['route_id']), fetch_all=True)
        
        if students:
            student_ids = [s['student_id'] for s in students]
            parent_tokens = bus_tracking_service.get_parent_tokens_for_students(student_ids)
            
            if parent_tokens:
                results = []
                for token in parent_tokens:
                    res = await notification_service.send_to_device(
                        title="Bus Notification",
                        body=notification.message,
                        token=token,
                        recipient_type="parent",
                        message_type="custom"
                    )
                    results.append(res)
                
                return {
                    "success": True,
                    "parents_notified": len(results),
                    "students_count": len(students)
                }
        
        return {"success": False, "message": "No parents to notify"}
        
    except Exception as e:
        logger.error(f"Custom notification error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send notification")

@router.post("/bus-tracking/cache-update/{route_id}", tags=["Bus Tracking"])
async def update_fcm_cache(route_id: str):
    """Update FCM token cache for a route"""
    try:
        result = bus_tracking_service.update_route_fcm_cache(route_id)
        return result
    except Exception as e:
        logger.error(f"FCM cache update error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update FCM cache")

@router.get("/bus-tracking/cache/{route_id}", tags=["Bus Tracking"])
async def get_fcm_cache(route_id: str):
    """Get FCM cache for a route"""
    query = "SELECT * FROM route_stop_fcm_cache WHERE route_id = %s"
    cache = execute_query(query, (route_id,), fetch_one=True)
    
    if not cache:
        raise HTTPException(status_code=404, detail="FCM cache not found for route")
    
    return {
        "route_id": cache['route_id'],
        "stop_fcm_map": json.loads(cache['stop_fcm_map']),
        "updated_at": cache['updated_at']
    }

@router.get("/trips/active", response_model=List[TripResponse], tags=["Trips"])
async def get_active_trips():
    """Get all active/ongoing trips"""
    query = "SELECT * FROM trips WHERE status IN ('ONGOING', 'NOT_STARTED') ORDER BY trip_date DESC"
    trips = execute_query(query, fetch_all=True)
    return trips or []

@router.put("/trips/{trip_id}/start", response_model=TripResponse, tags=["Trips"])
async def start_trip(trip_id: str):
    """Driver starts trip - everything else becomes automatic"""
    try:
        # Update trip status to ONGOING
        query = """
        UPDATE trips SET 
        status = 'ONGOING', 
        started_at = CURRENT_TIMESTAMP,
        current_stop_order = 0,
        updated_at = CURRENT_TIMESTAMP 
        WHERE trip_id = %s AND status = 'NOT_STARTED'
        """
        
        result = execute_query(query, (trip_id,))
        if result == 0:
            raise HTTPException(status_code=404, detail="Trip not found or already started")
        
        # Notify all parents on this route that the trip has started
        trip_data = await get_trip(trip_id)
        students_query = """
        SELECT s.student_id FROM students s
        WHERE (s.pickup_route_id = %s OR s.drop_route_id = %s)
        AND s.transport_status = 'ACTIVE'
        AND s.student_status = 'CURRENT'
        AND s.is_transport_user = True
        """
        students = execute_query(students_query, (trip_data['route_id'], trip_data['route_id']), fetch_all=True)
        if students:
            student_ids = [s['student_id'] for s in students]
            parent_tokens = bus_tracking_service.get_parent_tokens_for_students(student_ids)
            if parent_tokens:
                for token in set(parent_tokens):
                    await notification_service.send_to_device(
                        title="Bus Trip Started",
                        body=f"The bus trip for route '{trip_data['route_id']}' has started.",
                        token=token,
                        recipient_type="parent",
                        message_type="trip_started"
                    )



        return trip_data
    except Exception as e:
        logger.error(f"Start trip error: {e}")
        raise HTTPException(status_code=500, detail="Failed to start trip")

@router.get("/buses/by-route/{route_id}", response_model=List[BusResponse], tags=["Buses"])
async def get_buses_by_route(route_id: str):
    """Get all buses assigned to a specific route"""
    query = "SELECT * FROM buses WHERE route_id = %s"
    buses = execute_query(query, (route_id,), fetch_all=True)
    return buses or []

@router.get("/dashboard/summary", tags=["Utility"])
async def get_dashboard_summary():
    """Get counts of all main entities for dashboard"""
    try:
        counts = {}
        counts["admins"] = execute_query("SELECT COUNT(*) as count FROM admins", fetch_one=True)["count"]
        counts["parents"] = execute_query("SELECT COUNT(*) as count FROM parents", fetch_one=True)["count"]
        counts["drivers"] = execute_query("SELECT COUNT(*) as count FROM drivers", fetch_one=True)["count"]
        counts["buses"] = execute_query("SELECT COUNT(*) as count FROM buses", fetch_one=True)["count"]
        counts["routes"] = execute_query("SELECT COUNT(*) as count FROM routes", fetch_one=True)["count"]
        counts["students"] = execute_query("SELECT COUNT(*) as count FROM students", fetch_one=True)["count"]
        counts["ongoing_trips"] = execute_query("SELECT COUNT(*) as count FROM trips WHERE status = 'ONGOING'", fetch_one=True)["count"]
        return counts
    except Exception as e:
        logger.error(f"Summary error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get summary")

# =====================================================
# DRIVER LIVE LOCATION ENDPOINTS
# =====================================================

@router.put("/drivers/{driver_id}/location", tags=["Drivers"])
async def update_driver_location(driver_id: str, location: DriverLocationUpdate):
    """Update driver's real-time location"""
    try:
        # Check if driver exists
        driver_check = "SELECT driver_id FROM drivers WHERE driver_id = %s"
        if not execute_query(driver_check, (driver_id,), fetch_one=True):
            raise HTTPException(status_code=404, detail="Driver not found")

        # Update or Insert live location
        query = """
        INSERT INTO driver_live_locations (driver_id, latitude, longitude, updated_at)
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
        ON DUPLICATE KEY UPDATE 
            latitude = VALUES(latitude),
            longitude = VALUES(longitude),
            updated_at = CURRENT_TIMESTAMP
        """
        execute_query(query, (driver_id, location.latitude, location.longitude))
        return {"message": "Location updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating driver location: {e}")
        raise HTTPException(status_code=500, detail="Failed to update location")

@router.get("/drivers/{driver_id}/location", response_model=DriverLocationResponse, tags=["Drivers"])
async def get_driver_location(driver_id: str):
    """Get a specific driver's live location"""
    query = "SELECT * FROM driver_live_locations WHERE driver_id = %s"
    location = execute_query(query, (driver_id,), fetch_one=True)
    if not location:
        raise HTTPException(status_code=404, detail="Live location not found for this driver")
    return location

@router.get("/drivers/locations/all", response_model=List[DriverLocationResponse], tags=["Drivers"])
async def get_all_driver_locations():
    """Get all drivers' live locations (useful for admin map)"""
    query = "SELECT * FROM driver_live_locations"
    locations = execute_query(query, fetch_all=True)
    return locations or []

