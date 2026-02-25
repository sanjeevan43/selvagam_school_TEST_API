from fastapi import APIRouter, Header, HTTPException, Body, status
from app.notification_api.service import notification_service, ADMIN_KEY
from typing import Optional, List
from app.api.models import *
from app.core.database import execute_query
from app.core.auth import create_access_token
from datetime import datetime
import asyncio
import os

router = APIRouter()

@router.post("/auth/admin/login", response_model=Token, tags=["Authentication"])
async def admin_login(login_data: LoginRequest):
    """Login for Admin users"""
    try:
        query = "SELECT admin_id, phone, password_hash, name FROM admins WHERE phone = %s AND status = 'ACTIVE'"
        admin = execute_query(query, (login_data.phone,), fetch_one=True)
        
        if admin and admin['password_hash'] == login_data.password:
            # Update last login
            execute_query("UPDATE admins SET last_login_at = %s WHERE admin_id = %s", 
                         (datetime.now(), admin['admin_id']))
            
            access_token = create_access_token(
                data={"sub": admin['admin_id'], "user_type": "admin", "phone": admin['phone']}
            )
            return {"access_token": access_token, "token_type": "bearer"}
        
        raise HTTPException(status_code=401, detail="Invalid admin credentials or account inactive")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Admin login failed: {str(e)}")

@router.post("/auth/parent/login", response_model=Token, tags=["Authentication"])
async def parent_login(login_data: LoginRequest):
    """Login for Parent users"""
    try:
        query = "SELECT parent_id, phone, password_hash, name FROM parents WHERE phone = %s AND parents_active_status = 'ACTIVE'"
        parent = execute_query(query, (login_data.phone,), fetch_one=True)
        
        if parent and parent['password_hash'] == login_data.password:
            # Update last login
            execute_query("UPDATE parents SET last_login_at = %s WHERE parent_id = %s", 
                         (datetime.now(), parent['parent_id']))
            
            access_token = create_access_token(
                data={"sub": parent['parent_id'], "user_type": "parent", "phone": parent['phone']}
            )
            return {"access_token": access_token, "token_type": "bearer"}
        
        raise HTTPException(status_code=401, detail="Invalid parent credentials or account inactive")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parent login failed: {str(e)}")

@router.post("/auth/driver/login", response_model=Token, tags=["Authentication"])
async def driver_login(login_data: LoginRequest):
    """Login for Driver users"""
    try:
        query = "SELECT driver_id, phone, password_hash, name FROM drivers WHERE phone = %s AND status = 'ACTIVE'"
        driver = execute_query(query, (login_data.phone,), fetch_one=True)
        
        if driver and driver['password_hash'] == login_data.password:
            # Update last login
            execute_query("UPDATE drivers SET updated_at = CURRENT_TIMESTAMP WHERE driver_id = %s", 
                         (driver['driver_id'],))
            
            access_token = create_access_token(
                data={"sub": driver['driver_id'], "user_type": "driver", "phone": driver['phone']}
            )
            return {"access_token": access_token, "token_type": "bearer"}
        
        raise HTTPException(status_code=401, detail="Invalid driver credentials or account inactive")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Driver login failed: {str(e)}")

@router.get("/notifications/status", tags=["Notifications"])
async def get_status():
    """Check notification service status with detailed diagnostics"""
    return {
        "status": "online" if notification_service.initialized else "offline",
        "initialized": notification_service.initialized,
        "creds_found": notification_service.creds_path is not None,
        "creds_path": str(notification_service.creds_path) if notification_service.creds_path else None,
        "last_error": notification_service.last_error,
        "project_id": os.environ.get('GOOGLE_CLOUD_PROJECT')
    }

@router.post("/send-notification", tags=["Notifications"])
async def send_notification(
    title: str = Body(...),
    body: str = Body(...),
    topic: str = Body("all_users"),
    message_type: str = Body("audio"),
    x_admin_key: str = Header(..., alias="x-admin-key")
):
    """Send a notification to a specific topic"""
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    result = await notification_service.send_to_topic(title, body, topic, message_type)
    return result

@router.post("/notifications/send-device", tags=["Notifications"])
async def send_device_notification(
    title: str = Body(...),
    body: str = Body(...),
    token: str = Body(...),
    recipient_type: str = Body("parent"),
    message_type: str = Body("audio"),
    x_admin_key: str = Header(..., alias="x-admin-key")
):
    """Send a notification to a specific device token"""
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    result = await notification_service.send_to_device(title, body, token, recipient_type, message_type)
    return result

@router.post("/notifications/broadcast/drivers", tags=["Notifications"])
async def broadcast_drivers(
    title: str = Body(...),
    body: str = Body(...),
    message_type: str = Body("audio"),
    x_admin_key: str = Header(..., alias="x-admin-key")
):
    """Send a notification to all drivers concurrently"""
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Fetch all driver tokens
    drivers = execute_query("SELECT fcm_token FROM drivers WHERE fcm_token IS NOT NULL AND status = 'ACTIVE'", fetch_all=True)
    driver_tokens = {d['fcm_token'] for d in drivers if d['fcm_token']}
    
    if not driver_tokens:
        return {"success": True, "delivered_count": 0, "total_found": 0, "message": "No active driver tokens found"}

    # Send concurrently
    tasks = [
        notification_service.send_to_device(title, body, token, recipient_type="driver", message_type=message_type)
        for token in driver_tokens
    ]
    results = await asyncio.gather(*tasks)
    
    success_count = sum(1 for r in results if r.get("success"))
    return {
        "success": True, 
        "delivered_count": success_count, 
        "total_tokens": len(driver_tokens),
        "message": f"Broadcast sent to {success_count} drivers"
    }

@router.post("/notifications/broadcast/parents", tags=["Notifications"])
async def broadcast_parents(
    title: str = Body(..., description="The title of the notification"),
    body: str = Body(..., description="The message body"),
    message_type: str = Body("audio", alias="messageType", description="Type of message (default: audio)"),
    x_admin_key: str = Header(..., alias="x-admin-key")
):
    """Send a notification to all parents concurrently"""
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Fetch all unique parent tokens from database for ACTIVE parents only
    query = """
    SELECT DISTINCT ft.fcm_token 
    FROM fcm_tokens ft
    JOIN parents p ON ft.parent_id = p.parent_id
    WHERE ft.parent_id IS NOT NULL 
    AND p.parents_active_status = 'ACTIVE'
    """
    tokens = execute_query(query, fetch_all=True)
    all_tokens = {t['fcm_token'] for t in tokens if t['fcm_token']}
    
    if not all_tokens:
        return {"success": True, "delivered_count": 0, "total_found": 0, "message": "No active parent tokens found"}

    # Send concurrently
    tasks = [
        notification_service.send_to_device(title, body, t_val, recipient_type="parent", message_type=message_type)
        for t_val in all_tokens
    ]
    results = await asyncio.gather(*tasks)
    
    success_count = sum(1 for r in results if r.get("success"))
    return {
        "success": True, 
        "delivered_count": success_count, 
        "total_tokens": len(all_tokens), 
        "message": f"Broadcast sent to {success_count} parents"
    }

@router.post("/notifications/student/{student_id}", tags=["Notifications"])
async def send_student_notification(
    student_id: str,
    title: str = Body(...),
    body: str = Body(...),
    message_type: str = Body("audio"),
    x_admin_key: str = Header(..., alias="x-admin-key")
):
    """Send a notification to all FCM tokens associated with a student"""
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    tokens = execute_query("SELECT fcm_token FROM fcm_tokens WHERE student_id = %s", (student_id,), fetch_all=True)
    if not tokens:
        raise HTTPException(status_code=404, detail="No FCM tokens found for this student")
    
    unique_tokens = {t['fcm_token'] for t in tokens if t['fcm_token']}
    tasks = [
        notification_service.send_to_device(title, body, t_val, recipient_type="student", message_type=message_type)
        for t_val in unique_tokens
    ]
    results = await asyncio.gather(*tasks)
    
    success_count = sum(1 for r in results if r.get("success"))
    return {"success": True, "delivered_count": success_count, "total_tokens": len(unique_tokens)}

@router.post("/notifications/parent/{parent_id}", tags=["Notifications"])
async def send_parent_notification(
    parent_id: str,
    title: str = Body(...),
    body: str = Body(...),
    message_type: str = Body("audio"),
    x_admin_key: str = Header(..., alias="x-admin-key")
):
    """Send a notification to all FCM tokens associated with a parent"""
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    tokens = execute_query("SELECT fcm_token FROM fcm_tokens WHERE parent_id = %s", (parent_id,), fetch_all=True)
    if not tokens:
        parent_check = execute_query("SELECT parent_id FROM parents WHERE parent_id = %s", (parent_id,), fetch_one=True)
        if not parent_check:
            raise HTTPException(status_code=404, detail="Parent not found")
        return {"success": True, "message": "No FCM tokens found for this parent", "delivered_count": 0}
    
    unique_tokens = {t['fcm_token'] for t in tokens if t['fcm_token']}
    tasks = [
        notification_service.send_to_device(title, body, t_val, recipient_type="parent", message_type=message_type)
        for t_val in unique_tokens
    ]
    results = await asyncio.gather(*tasks)
    
    success_count = sum(1 for r in results if r.get("success"))
    return {"success": True, "delivered_count": success_count, "total_tokens": len(unique_tokens)}

@router.post("/notifications/route/{route_id}", tags=["Notifications"])
async def send_route_notification(
    route_id: str,
    title: str = Body(...),
    body: str = Body(...),
    message_type: str = Body("audio"),
    x_admin_key: str = Header(..., alias="x-admin-key")
):
    """Send a notification to everyone (parents/students) on a specific route"""
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    query = """
    SELECT DISTINCT ft.fcm_token 
    FROM fcm_tokens ft
    JOIN students s ON (ft.student_id = s.student_id OR ft.parent_id = s.parent_id OR ft.parent_id = s.s_parent_id)
    WHERE s.pickup_route_id = %s OR s.drop_route_id = %s
    """
    tokens = execute_query(query, (route_id, route_id), fetch_all=True)
    if not tokens:
        raise HTTPException(status_code=404, detail="No FCM tokens found for this route")
    
    unique_tokens = {t['fcm_token'] for t in tokens if t['fcm_token']}
    tasks = [
        notification_service.send_to_device(title, body, t_val, recipient_type="route", message_type=message_type)
        for t_val in unique_tokens
    ]
    results = await asyncio.gather(*tasks)
    
    success_count = sum(1 for r in results if r.get("success"))
    return {"success": True, "delivered_count": success_count, "total_tokens": len(unique_tokens)}

@router.post("/notifications/class/{class_id}", tags=["Notifications"])
async def send_class_notification(
    class_id: str,
    title: str = Body(...),
    body: str = Body(...),
    message_type: str = Body("audio"),
    x_admin_key: str = Header(..., alias="x-admin-key")
):
    """Send a notification to everyone (parents/students) in a specific class"""
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    query = """
    SELECT DISTINCT ft.fcm_token 
    FROM fcm_tokens ft
    JOIN students s ON (ft.student_id = s.student_id OR ft.parent_id = s.parent_id OR ft.parent_id = s.s_parent_id)
    WHERE s.class_id = %s
    """
    tokens = execute_query(query, (class_id,), fetch_all=True)
    if not tokens:
        raise HTTPException(status_code=404, detail="No FCM tokens found for this class")
    
    unique_tokens = {t['fcm_token'] for t in tokens if t['fcm_token']}
    tasks = [
        notification_service.send_to_device(title, body, t_val, recipient_type="class", message_type=message_type)
        for t_val in unique_tokens
    ]
    results = await asyncio.gather(*tasks)
    
    success_count = sum(1 for r in results if r.get("success"))
    return {"success": True, "delivered_count": success_count, "total_tokens": len(unique_tokens)}

from app.services.proximity_service import proximity_service

@router.post("/bus-tracking/location", tags=["Proximity Alerts"])
async def update_bus_location_proximity(location_data: BusLocationUpdate):
    """Automatic bus tracking with proximity/geofence notifications (Ported from notification_app)"""
    try:
        result = await proximity_service.process_location_update(
            trip_id=location_data.trip_id,
            lat=location_data.latitude,
            lng=location_data.longitude
        )
        return result
    except Exception as e:
        import traceback
        logger.error(f"Proximity update error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/trip/start", tags=["Proximity Alerts"])
async def start_trip_v2(trip_id: str, route_id: str, x_admin_key: str = Header(..., alias="x-admin-key")):
    """Start trip and notify parents (Ported from notification_app)"""
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await proximity_service.start_trip(trip_id, route_id)

@router.post("/trip/complete", tags=["Proximity Alerts"])
async def complete_trip_v2(trip_id: str, route_id: str, x_admin_key: str = Header(..., alias="x-admin-key")):
    """Complete trip and notify parents (Ported from notification_app)"""
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await proximity_service.complete_trip(trip_id, route_id)

@router.post("/notifications/manual-send", tags=["Proximity Alerts"])
async def manual_send(
    title: str = Body(...),
    message: str = Body(...),
    tokens: List[str] = Body(...),
    x_admin_key: str = Header(..., alias="x-admin-key")
):
    """Manual send to specific tokens (Ported from notification_app)"""
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await notification_service.broadcast_to_tokens(tokens, title, message)


