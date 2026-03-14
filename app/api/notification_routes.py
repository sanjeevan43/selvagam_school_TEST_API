from fastapi import APIRouter, Header, HTTPException, Body, status
from app.notification_api.service import notification_service, ADMIN_KEY
from typing import Optional, List
from app.api.models import *
from app.core.database import execute_query
from app.core.auth import create_access_token
from app.core.security import verify_password
from datetime import datetime
import asyncio
import os
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/auth/admin/login", response_model=Token, tags=["Authentication"])
async def admin_login(login_data: LoginRequest):
    """Login for Admin users"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Admin login attempt for phone: {login_data.phone}")
        
        query = "SELECT admin_id, phone, password_hash, name FROM admins WHERE phone = %s AND status = 'ACTIVE'"
        admin = execute_query(query, (login_data.phone,), fetch_one=True)
        
        if admin:
            logger.info(f"Admin found: {admin['name']}")
            if verify_password(login_data.password, admin['password_hash']):
                logger.info(f"Password verified for admin: {admin['name']}")
                # Update last login
                try:
                    execute_query("UPDATE admins SET last_login_at = %s WHERE admin_id = %s", 
                                 (datetime.now(), admin['admin_id']))
                except Exception as update_err:
                    logger.warning(f"Failed to update last_login_at: {update_err}")
                
                access_token = create_access_token(
                    data={"sub": admin['admin_id'], "user_type": "admin", "phone": admin['phone']}
                )
                return {"access_token": access_token, "token_type": "bearer"}
            else:
                logger.warning(f"Invalid password for admin: {admin['name']}")
        else:
            logger.warning(f"Admin not found for phone: {login_data.phone}")
        
        raise HTTPException(status_code=401, detail="Invalid admin credentials or account inactive")
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"System error in admin_login: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Admin login failed: {str(e)}")

@router.post("/auth/parent/login", response_model=Token, tags=["Authentication"])
async def parent_login(login_data: LoginRequest):
    """Login for Parent users"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Parent login attempt for phone: {login_data.phone}")
        
        query = "SELECT parent_id, phone, password_hash, name FROM parents WHERE phone = %s AND parents_active_status = 'ACTIVE'"
        parent = execute_query(query, (login_data.phone,), fetch_one=True)
        
        if parent:
            logger.info(f"Parent found: {parent['name']}")
            if verify_password(login_data.password, parent['password_hash']):
                logger.info(f"Password verified for parent: {parent['name']}")
                # Update last login
                try:
                    execute_query("UPDATE parents SET last_login_at = %s WHERE parent_id = %s", 
                                 (datetime.now(), parent['parent_id']))
                except Exception as update_err:
                    logger.warning(f"Failed to update last_login_at: {update_err}")
                
                access_token = create_access_token(
                    data={"sub": parent['parent_id'], "user_type": "parent", "phone": parent['phone']}
                )
                return {"access_token": access_token, "token_type": "bearer"}
            else:
                logger.warning(f"Invalid password for parent: {parent['name']}")
        else:
            logger.warning(f"Parent not found or inactive for phone: {login_data.phone}")
        
        raise HTTPException(status_code=401, detail="Invalid parent credentials or account inactive")
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"System error in parent_login: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Parent login failed: {str(e)}")

@router.post("/auth/driver/login", response_model=Token, tags=["Authentication"])
async def driver_login(login_data: LoginRequest):
    """Login for Driver users"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Driver login attempt for phone: {login_data.phone}")
        
        query = "SELECT driver_id, phone, password_hash, name FROM drivers WHERE phone = %s AND status = 'ACTIVE'"
        driver = execute_query(query, (login_data.phone,), fetch_one=True)
        
        if driver:
            logger.info(f"Driver found: {driver['name']}")
            if verify_password(login_data.password, driver['password_hash']):
                logger.info(f"Password verified for driver: {driver['name']}")
                # Update status/update time
                try:
                    execute_query("UPDATE drivers SET updated_at = CURRENT_TIMESTAMP WHERE driver_id = %s", 
                                 (driver['driver_id'],))
                except Exception as update_err:
                    logger.warning(f"Failed to update driver timestamp: {update_err}")
                
                access_token = create_access_token(
                    data={"sub": driver['driver_id'], "user_type": "driver", "phone": driver['phone']}
                )
                return {"access_token": access_token, "token_type": "bearer"}
            else:
                logger.warning(f"Invalid password for driver: {driver['name']}")
        else:
            logger.warning(f"Driver not found or inactive for phone: {login_data.phone}")
        
        raise HTTPException(status_code=401, detail="Invalid driver credentials or account inactive")
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"System error in driver_login: {str(e)}")
        logger.error(traceback.format_exc())
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
    """Send a notification to all parents concurrently (Saves to DB history first)"""
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # 1. Log the broadcast in history FIRST
    notification_id = str(uuid.uuid4())
    try:
        log_query = """
        INSERT INTO admin_parent_notifications (notification_id, title, message, recipient_type, sent_by_admin_id)
        VALUES (%s, %s, %s, 'ALL', %s)
        """
        execute_query(log_query, (notification_id, title, body, "SYSTEM_ADMIN"))
    except Exception as log_err:
        logger.warning(f"Failed to log broadcast notification: {log_err}")

    # 2. Fetch all unique parent tokens from database for ACTIVE parents only
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
        return {"success": True, "delivered_count": 0, "total_found": 0, "message": "No active parent tokens found", "notification_id": notification_id}

    # 3. Send concurrently
    tasks = [
        notification_service.send_to_device(title, body, t_val, recipient_type="parent", message_type=message_type)
        for t_val in all_tokens
    ]
    results = await asyncio.gather(*tasks)
    
    success_count = sum(1 for r in results if r.get("success"))
    failure_reasons = [r.get("error") for r in results if not r.get("success")]
    
    return {
        "success": True, 
        "delivered_count": success_count, 
        "total_tokens": len(all_tokens), 
        "failure_reasons": failure_reasons[:10], # Show first 10 errors
        "message": f"Broadcast sent to {success_count} parents",
        "notification_id": notification_id
    }

@router.post("/notifications/student/{student_id}", tags=["Notifications"])
async def send_student_notification(
    student_id: str,
    title: str = Body(...),
    body: str = Body(...),
    message_type: str = Body("audio"),
    x_admin_key: str = Header(..., alias="x-admin-key")
):
    """Send a notification to all FCM tokens associated with a student (Saves to DB history first)"""
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # 1. Log in history FIRST
    notification_id = str(uuid.uuid4())
    try:
        log_query = """
        INSERT INTO admin_parent_notifications (notification_id, title, message, recipient_type, student_id, sent_by_admin_id)
        VALUES (%s, %s, %s, 'STUDENT', %s, %s)
        """
        execute_query(log_query, (notification_id, title, body, student_id, "SYSTEM_ADMIN"))
    except Exception as log_err:
        logger.warning(f"Failed to log student notification: {log_err}")

    tokens = execute_query("SELECT fcm_token FROM fcm_tokens WHERE student_id = %s", (student_id,), fetch_all=True)
    if not tokens:
        return {"success": True, "message": "No tokens for student", "delivered_count": 0, "notification_id": notification_id}
    
    unique_tokens = {t['fcm_token'] for t in tokens if t['fcm_token']}
    tasks = [
        notification_service.send_to_device(title, body, t_val, recipient_type="student", message_type=message_type)
        for t_val in unique_tokens
    ]
    results = await asyncio.gather(*tasks)
    
    success_count = sum(1 for r in results if r.get("success"))
    failure_reasons = [r.get("error") for r in results if not r.get("success")]
    
    return {
        "success": True, 
        "delivered_count": success_count, 
        "total_tokens": len(unique_tokens), 
        "failure_reasons": failure_reasons,
        "notification_id": notification_id
    }

@router.post("/notifications/parent/{parent_id}", tags=["Notifications"])
async def send_parent_notification(
    parent_id: str,
    title: str = Body(...),
    body: str = Body(...),
    message_type: str = Body("audio"),
    x_admin_key: str = Header(..., alias="x-admin-key")
):
    """Send a notification to all FCM tokens associated with a parent (Saves to DB history first)"""
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # 1. Log in history FIRST
    notification_id = str(uuid.uuid4())
    try:
        log_query = """
        INSERT INTO admin_parent_notifications (notification_id, title, message, recipient_type, recipient_id, sent_by_admin_id)
        VALUES (%s, %s, %s, 'PARENT_DIRECT', %s, %s)
        """
        execute_query(log_query, (notification_id, title, body, parent_id, "SYSTEM_ADMIN"))
    except Exception as log_err:
        logger.warning(f"Failed to log parent notification: {log_err}")

    tokens = execute_query("SELECT fcm_token FROM fcm_tokens WHERE parent_id = %s", (parent_id,), fetch_all=True)
    if not tokens:
        return {"success": True, "message": "No tokens for parent", "delivered_count": 0, "notification_id": notification_id}
    
    unique_tokens = {t['fcm_token'] for t in tokens if t['fcm_token']}
    tasks = [
        notification_service.send_to_device(title, body, t_val, recipient_type="parent", message_type=message_type)
        for t_val in unique_tokens
    ]
    results = await asyncio.gather(*tasks)
    
    success_count = sum(1 for r in results if r.get("success"))
    failure_reasons = [r.get("error") for r in results if not r.get("success")]
    
    return {
        "success": True, 
        "delivered_count": success_count, 
        "total_tokens": len(unique_tokens), 
        "failure_reasons": failure_reasons,
        "notification_id": notification_id
    }

@router.post("/notifications/route/{route_id}", tags=["Notifications"])
async def send_route_notification(
    route_id: str,
    title: str = Body(...),
    body: str = Body(...),
    message_type: str = Body("audio"),
    x_admin_key: str = Header(..., alias="x-admin-key")
):
    """Send a notification to everyone (parents/students) on a specific route (Saves to DB history first)"""
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # 1. Log in history FIRST
    notification_id = str(uuid.uuid4())
    try:
        log_query = """
        INSERT INTO admin_parent_notifications (notification_id, title, message, recipient_type, route_id, sent_by_admin_id)
        VALUES (%s, %s, %s, 'ROUTE', %s, %s)
        """
        execute_query(log_query, (notification_id, title, body, route_id, "SYSTEM_ADMIN"))
    except Exception as log_err:
        logger.warning(f"Failed to log route notification: {log_err}")

    query = """
    SELECT DISTINCT ft.fcm_token 
    FROM fcm_tokens ft
    JOIN students s ON (ft.student_id = s.student_id OR ft.parent_id = s.parent_id OR ft.parent_id = s.s_parent_id)
    WHERE s.pickup_route_id = %s OR s.drop_route_id = %s
    """
    tokens = execute_query(query, (route_id, route_id), fetch_all=True)
    if not tokens:
        return {"success": True, "message": "No tokens for route", "delivered_count": 0, "notification_id": notification_id}
    
    unique_tokens = {t['fcm_token'] for t in tokens if t['fcm_token']}
    tasks = [
        notification_service.send_to_device(title, body, t_val, recipient_type="route", message_type=message_type)
        for t_val in unique_tokens
    ]
    results = await asyncio.gather(*tasks)
    
    success_count = sum(1 for r in results if r.get("success"))
    return {"success": True, "delivered_count": success_count, "total_tokens": len(unique_tokens), "notification_id": notification_id}

@router.post("/notifications/class/{class_id}", tags=["Notifications"])
async def send_class_notification(
    class_id: str,
    title: str = Body(...),
    body: str = Body(...),
    message_type: str = Body("audio"),
    x_admin_key: str = Header(..., alias="x-admin-key")
):
    """Send a notification to everyone (parents/students) in a specific class (Saves to DB history first)"""
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # 1. Log in history FIRST
    notification_id = str(uuid.uuid4())
    try:
        log_query = """
        INSERT INTO admin_parent_notifications (notification_id, title, message, recipient_type, class_id, sent_by_admin_id)
        VALUES (%s, %s, %s, 'CLASS', %s, %s)
        """
        execute_query(log_query, (notification_id, title, body, class_id, "SYSTEM_ADMIN"))
    except Exception as log_err:
        logger.warning(f"Failed to log class notification: {log_err}")

    query = """
    SELECT DISTINCT ft.fcm_token 
    FROM fcm_tokens ft
    JOIN students s ON (ft.student_id = s.student_id OR ft.parent_id = s.parent_id OR ft.parent_id = s.s_parent_id)
    WHERE s.class_id = %s
    """
    tokens = execute_query(query, (class_id,), fetch_all=True)
    if not tokens:
        return {"success": True, "message": "No tokens for class", "delivered_count": 0, "notification_id": notification_id}
    
    unique_tokens = {t['fcm_token'] for t in tokens if t['fcm_token']}
    tasks = [
        notification_service.send_to_device(title, body, t_val, recipient_type="class", message_type=message_type)
        for t_val in unique_tokens
    ]
    results = await asyncio.gather(*tasks)
    
    success_count = sum(1 for r in results if r.get("success"))
    return {"success": True, "delivered_count": success_count, "total_tokens": len(unique_tokens), "notification_id": notification_id}

@router.post("/notifications/location/{location_name}", tags=["Notifications"])
async def send_location_notification(
    location_name: str,
    title: str = Body(...),
    body: str = Body(...),
    route_id: Optional[str] = Body(None),
    message_type: str = Body("audio"),
    x_admin_key: str = Header(..., alias="x-admin-key")
):
    """Send a notification to everyone (parents/students) at a specific location name (Saves to DB history first)"""
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # 1. Log in history FIRST
    notification_id = str(uuid.uuid4())
    try:
        log_query = """
        INSERT INTO admin_parent_notifications (notification_id, title, message, recipient_type, location_name, route_id, sent_by_admin_id)
        VALUES (%s, %s, %s, 'LOCATION', %s, %s, %s)
        """
        execute_query(log_query, (notification_id, title, body, location_name, route_id, "SYSTEM_ADMIN"))
    except Exception as log_err:
        logger.warning(f"Failed to log location notification: {log_err}")

    if route_id:
        query = """
        SELECT DISTINCT ft.fcm_token 
        FROM fcm_tokens ft
        JOIN students s ON (ft.student_id = s.student_id OR ft.parent_id = s.parent_id OR ft.parent_id = s.s_parent_id)
        JOIN route_stops rs ON (s.pickup_stop_id = rs.stop_id OR s.drop_stop_id = rs.stop_id)
        WHERE (s.pickup_route_id = %s OR s.drop_route_id = %s) AND rs.location = %s
        """
        params = (route_id, route_id, location_name)
    else:
        query = """
        SELECT DISTINCT ft.fcm_token 
        FROM fcm_tokens ft
        JOIN students s ON (ft.student_id = s.student_id OR ft.parent_id = s.parent_id OR ft.parent_id = s.s_parent_id)
        JOIN route_stops rs ON (s.pickup_stop_id = rs.stop_id OR s.drop_stop_id = rs.stop_id)
        WHERE rs.location = %s
        """
        params = (location_name,)

    tokens = execute_query(query, params, fetch_all=True)
    if not tokens:
        return {"success": True, "message": "No tokens for location", "delivered_count": 0, "notification_id": notification_id}
    
    unique_tokens = {t['fcm_token'] for t in tokens if t['fcm_token']}
    tasks = [
        notification_service.send_to_device(title, body, t_val, recipient_type="location", message_type=message_type)
        for t_val in unique_tokens
    ]
    results = await asyncio.gather(*tasks)
    
    success_count = sum(1 for r in results if r.get("success"))
    return {"success": True, "delivered_count": success_count, "total_tokens": len(unique_tokens), "notification_id": notification_id}

from app.services.proximity_service import proximity_service
from app.services.bus_tracking import bus_tracking_service
import logging

logger = logging.getLogger(__name__)

@router.post("/bus-tracking/location", tags=["Proximity Alerts"])
async def update_bus_location_combined(location_data: BusLocationUpdate):
    """Combined bus tracking: handles stop progression, trip completion, AND proximity/geofence notifications"""
    try:
        # 1. Run stop progression (updates current_stop_order, auto-completes trip, sends stop arrival notifications)
        stop_result = await bus_tracking_service.update_bus_location(
            trip_id=location_data.trip_id,
            latitude=location_data.latitude,
            longitude=location_data.longitude
        )
        
        # 2. Run proximity alerts (approaching/arrived geofence notifications)
        proximity_result = await proximity_service.process_location_update(
            trip_id=location_data.trip_id,
            lat=location_data.latitude,
            lng=location_data.longitude
        )
        
        # Combine results
        return {
            "success": stop_result.get("success", False) or proximity_result.get("success", False),
            "trip_id": location_data.trip_id,
            "stop_progression": stop_result,
            "proximity_alerts": proximity_result
        }
    except Exception as e:
        import traceback
        logger.error(f"Combined bus tracking error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/trip/start", tags=["Proximity Alerts"])
async def start_trip_v2(trip_id: str, x_admin_key: str = Header(..., alias="x-admin-key")):
    """Start trip: marks trip as ONGOING in DB and notifies all parents on the route. Only needs trip_id."""
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    # Fetch the route_id from DB
    trip = execute_query("SELECT route_id FROM trips WHERE trip_id = %s", (trip_id,), fetch_one=True)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return await proximity_service.start_trip(trip_id, trip["route_id"])

@router.post("/trip/complete", tags=["Proximity Alerts"])
async def complete_trip_v2(trip_id: str, x_admin_key: str = Header(..., alias="x-admin-key")):
    """Complete trip: marks trip as COMPLETED in DB and notifies all parents on the route. Only needs trip_id."""
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    # Fetch the route_id from DB
    trip = execute_query("SELECT route_id FROM trips WHERE trip_id = %s", (trip_id,), fetch_one=True)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return await proximity_service.complete_trip(trip_id, trip["route_id"])

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


