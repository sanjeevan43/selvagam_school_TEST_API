import logging
import math
import json
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from app.core.database import execute_query
from app.notification_api.service import notification_service

logger = logging.getLogger(__name__)

class BusTrackingService:
    def __init__(self):
        pass
        
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers"""
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def get_students_for_route_stop(self, route_id: str, stop_order: int, trip_type: str) -> List[Dict]:
        """Get students for a specific route stop based on trip type"""
        if trip_type == "PICKUP":
            query = """
            SELECT s.student_id, s.name, ft.fcm_token, rs.stop_name
            FROM students s
            JOIN route_stops rs ON s.pickup_stop_id = rs.stop_id
            LEFT JOIN fcm_tokens ft ON s.student_id = ft.student_id
            WHERE s.pickup_route_id = %s AND rs.pickup_stop_order = %s 
            AND s.transport_status = 'ACTIVE' AND s.student_status = 'CURRENT'
            AND s.is_transport_user = True
            """
        else:  # DROP
            query = """
            SELECT s.student_id, s.name, ft.fcm_token, rs.stop_name
            FROM students s
            JOIN route_stops rs ON s.drop_stop_id = rs.stop_id
            LEFT JOIN fcm_tokens ft ON s.student_id = ft.student_id
            WHERE s.drop_route_id = %s AND rs.drop_stop_order = %s 
            AND s.transport_status = 'ACTIVE' AND s.student_status = 'CURRENT'
            AND s.is_transport_user = True
            """
        
        return execute_query(query, (route_id, stop_order), fetch_all=True) or []
    
    def get_parent_tokens_for_students(self, student_ids: List[str]) -> List[str]:
        """Get parent FCM tokens for given students"""
        if not student_ids:
            return []
            
        placeholders = ','.join(['%s'] * len(student_ids))
        query = f"""
        SELECT DISTINCT ft.fcm_token
        FROM students s
        JOIN fcm_tokens ft ON (s.parent_id = ft.parent_id OR s.s_parent_id = ft.parent_id)
        WHERE s.student_id IN ({placeholders}) AND ft.fcm_token IS NOT NULL
        """
        
        tokens = execute_query(query, tuple(student_ids), fetch_all=True)
        return [token['fcm_token'] for token in tokens if token['fcm_token']]
    
    async def update_bus_location(self, trip_id: str, latitude: float, longitude: float):
        """Automatic bus tracking - handle stop progression and trip completion"""
        try:
            # Get trip details
            trip_query = """
            SELECT t.*, r.name as route_name, b.registration_number
            FROM trips t
            JOIN routes r ON t.route_id = r.route_id
            JOIN buses b ON t.bus_id = b.bus_id
            WHERE t.trip_id = %s AND t.status = 'ONGOING'
            """
            trip = execute_query(trip_query, (trip_id,), fetch_one=True)
            
            if not trip:
                return {"success": False, "message": "Trip not found or not ongoing"}
            
            # Get route stops based on trip type
            order_field = "pickup_stop_order" if trip['trip_type'] == "PICKUP" else "drop_stop_order"
            stops_query = f"""
            SELECT stop_id, stop_name, latitude, longitude, {order_field} as stop_order
            FROM route_stops 
            WHERE route_id = %s AND latitude IS NOT NULL AND longitude IS NOT NULL
            ORDER BY {order_field}
            """
            
            stops = execute_query(stops_query, (trip['route_id'],), fetch_all=True)
            
            if not stops:
                return {"success": False, "message": "No stops with coordinates found"}
            
            current_stop_order = trip['current_stop_order']
            
            # --- Logic for First Stop 500m Alert (Stored in DB) ---
            if current_stop_order < 1 and not trip.get('is_first_stop_notified'):
                first_stop = next((s for s in stops if s['stop_order'] == 1), None)
                if first_stop:
                    dist_to_first = self.calculate_distance(
                        latitude, longitude,
                        float(first_stop['latitude']), float(first_stop['longitude'])
                    )
                    if dist_to_first <= 0.5: # 500m
                        logger.info(f"🔔 Notifying first stop 500m alert: {first_stop['stop_name']}")
                        students = self.get_students_for_route_stop(trip['route_id'], 1, trip['trip_type'])
                        if students:
                            await self._broadcast_helper(students, "🚌 Bus Upcoming", f"Your bus is approaching {first_stop['stop_name']}.", {"trip_id": trip_id, "stop_name": first_stop['stop_name'], "status": "UPCOMING"})
                        
                        execute_query("UPDATE trips SET is_first_stop_notified = 1 WHERE trip_id = %s", (trip_id,))
            
            # --- Smart Lookahead Stop Logic (Handles Skips) ---
            # Consider the next 5 stops, but EXCLUDE any that are explicitly marked as "skipped"
            skipped_list = json.loads(trip['skipped_stops']) if trip.get('skipped_stops') else []
            
            lookahead_stops = [s for s in stops if s['stop_order'] > current_stop_order and s['stop_order'] not in skipped_list][:5]
            
            stops_passed = 0
            current_stop_info = None
            arrived_stop = None

            # Find if we have reached any of the upcoming stops
            for stop in lookahead_stops:
                distance = self.calculate_distance(
                    latitude, longitude, 
                    float(stop['latitude']), float(stop['longitude'])
                )
                
                # Check if we have REACHED the stop (within 50m)
                if distance <= 0.05:
                    arrived_stop = stop
                    break

            if arrived_stop:
                target_order = arrived_stop['stop_order']
                logger.info(f"📍 Stop Reached: {arrived_stop['stop_name']} (Order {target_order})")
                
                # 1. Update Database (skips over previous stops automatically and updates stop_logs)
                new_stop_logs = []
                if trip.get('stop_logs'):
                    try:
                        import json
                        current_logs = trip['stop_logs']
                        if isinstance(current_logs, str):
                            current_logs = json.loads(current_logs)
                        
                        if isinstance(current_logs, list):
                            for entry in current_logs:
                                # Update reached stop AND skip over any prior stops missed by the GPS ping
                                if entry['stop_order'] <= target_order and entry['arrived_at'] is None:
                                    entry['arrived_at'] = datetime.now().isoformat()
                            new_stop_logs = current_logs
                    except Exception as json_err:
                        logger.error(f"Error updating stop_logs JSON: {json_err}")
                        new_stop_logs = None

                update_query = """
                UPDATE trips SET 
                    current_stop_order = %s, 
                    stop_logs = %s,
                    updated_at = CURRENT_TIMESTAMP 
                WHERE trip_id = %s
                """
                execute_query(update_query, (target_order, json.dumps(new_stop_logs) if new_stop_logs else trip.get('stop_logs'), trip_id))
                
                stops_passed = target_order - current_stop_order
                current_stop_order = target_order
                current_stop_info = {"stop_name": arrived_stop['stop_name'], "stop_order": target_order}

                # 2. Sequential Notifications
                # A. Arrival Notification for current stop (Stop N)
                students_N = self.get_students_for_route_stop(trip['route_id'], target_order, trip['trip_type'])
                if students_N:
                    await self._broadcast_helper(students_N, "🚌 Bus Arrived", f"Your bus has arrived at {arrived_stop['stop_name']}.", {"trip_id": trip_id, "stop_name": arrived_stop['stop_name'], "status": "ARRIVED"})

                # B. Approaching Notification for the future next stop (Stop N + 1)
                next_next_order = target_order + 1
                students_N1 = self.get_students_for_route_stop(trip['route_id'], next_next_order, trip['trip_type'])
                if students_N1:
                    await self._broadcast_helper(students_N1, "🚌 Bus Approaching", f"Your bus reached on {arrived_stop['stop_name']}", {"trip_id": trip_id, "stop_name": arrived_stop['stop_name'], "status": "APPROACHING"})

                # C. Upcoming Notification for Stop N + 2
                upcoming_order = target_order + 2
                students_N2 = self.get_students_for_route_stop(trip['route_id'], upcoming_order, trip['trip_type'])
                if students_N2:
                    await self._broadcast_helper(students_N2, "🚌 Bus Upcoming", f"Your bus reached {arrived_stop['stop_name']}.", {"trip_id": trip_id, "status": "UPCOMING"})

                # D. Early Notification for Stop N + 3
                upcoming_order_3 = target_order + 3
                students_N3 = self.get_students_for_route_stop(trip['route_id'], upcoming_order_3, trip['trip_type'])
                if students_N3:
                    await self._broadcast_helper(students_N3, "🚌 Bus Upcoming", f"Your bus reached {arrived_stop['stop_name']}.", {"trip_id": trip_id, "status": "UPCOMING"})

                # E. Early Notification for Stop N + 4
                upcoming_order_4 = target_order + 4
                students_N4 = self.get_students_for_route_stop(trip['route_id'], upcoming_order_4, trip['trip_type'])
                if students_N4:
                    await self._broadcast_helper(students_N4, "🚌 Bus Upcoming", f"Your bus reached {arrived_stop['stop_name']}.", {"trip_id": trip_id, "status": "UPCOMING"})

                # F. Early Notification for Stop N + 5
                upcoming_order_5 = target_order + 5
                students_N5 = self.get_students_for_route_stop(trip['route_id'], upcoming_order_5, trip['trip_type'])
                if students_N5:
                    await self._broadcast_helper(students_N5, "🚌 Bus Upcoming", f"Your bus reached {arrived_stop['stop_name']}.", {"trip_id": trip_id, "status": "UPCOMING"})

            return {
                "success": True,
                "trip_id": trip_id,
                "current_stop_order": current_stop_order,
                "current_stop_info": current_stop_info,
                "stops_passed": stops_passed,
                "trip_completed": False,
                "message": f"Reached {current_stop_info['stop_name']}" if current_stop_info else "In transit"
            }
            
        except Exception as e:
            logger.error(f"Bus location processing error: {e}")
            return {"success": False, "error": str(e)}

    async def _broadcast_helper(self, students: List[Dict], title: str, body: str, data: Dict):
        """Helper to broadcast notifications asynchronously"""
        student_ids = [st['student_id'] for st in students]
        tokens = self.get_parent_tokens_for_students(student_ids)
        if tokens:
            await notification_service.broadcast_to_tokens(list(set(tokens)), title, body, data)

    async def skip_specific_stop(self, trip_id: str, stop_order: int):
        """Mark a specific stop_order as skipped for the current trip"""
        try:
            # 1. Fetch current skipped stops
            query = "SELECT skipped_stops FROM trips WHERE trip_id = %s"
            result = execute_query(query, (trip_id,), fetch_one=True)
            if not result:
                return {"success": False, "message": "Trip not found"}

            skipped = json.loads(result['skipped_stops']) if result.get('skipped_stops') else []
            
            # 2. Add new stop order if not already skipped
            if stop_order not in skipped:
                skipped.append(stop_order)
            
            # 3. Update DB
            execute_query(
                "UPDATE trips SET skipped_stops = %s, updated_at = CURRENT_TIMESTAMP WHERE trip_id = %s",
                (json.dumps(skipped), trip_id)
            )

            # 4. Trigger alert for next stops just in case we were currently "at" the skipped stop
            logger.info(f"🚫 Stop {stop_order} manually excluded from trip {trip_id}")

            return {"success": True, "message": f"Stop {stop_order} skipped for this trip", "skipped_stops": skipped}
        except Exception as e:
            logger.error(f"Error skipping specific stop: {e}")
            return {"success": False, "error": str(e)}

    async def skip_stop(self, trip_id: str):
        """Manually skip the current target stop for a trip"""
        try:
            # 1. Get trip details
            trip_query = "SELECT * FROM trips WHERE trip_id = %s AND status = 'ONGOING'"
            trip = execute_query(trip_query, (trip_id,), fetch_one=True)
            if not trip:
                return {"success": False, "message": "Trip not found or not ongoing"}

            current_order = trip['current_stop_order']
            target_skip_order = current_order + 1
            
            # 2. Get stop name for logging/response
            order_field = "pickup_stop_order" if trip['trip_type'] == "PICKUP" else "drop_stop_order"
            stop_query = f"SELECT stop_name FROM route_stops WHERE route_id = %s AND {order_field} = %s"
            skipped_stop = execute_query(stop_query, (trip['route_id'], target_skip_order), fetch_one=True)
            
            if not skipped_stop:
                 return {"success": False, "message": "No more stops to skip"}

            # 3. Update DB: Move to the next stop order
            execute_query(
                "UPDATE trips SET current_stop_order = %s, updated_at = CURRENT_TIMESTAMP WHERE trip_id = %s",
                (target_skip_order, trip_id)
            )

            logger.info(f"⏭️ Manual Skip: Stop {skipped_stop['stop_name']} (Order {target_skip_order})")

            # 4. Trigger "Next Stop" notifications (Approaching/Upcoming) for upcoming students
            # A. Approaching Notification for Stop N + 1
            next_order = target_skip_order + 1
            students_N1 = self.get_students_for_route_stop(trip['route_id'], next_order, trip['trip_type'])
            if students_N1:
                await self._broadcast_helper(students_N1, "🚌 Bus Approaching", f"Your bus passed {skipped_stop['stop_name']}", {"trip_id": trip_id, "stop_name": skipped_stop['stop_name'], "status": "APPROACHING"})

            # B. Upcoming Notification for Stop N + 2
            upcoming_order = target_skip_order + 2
            students_N2 = self.get_students_for_route_stop(trip['route_id'], upcoming_order, trip['trip_type'])
            if students_N2:
                await self._broadcast_helper(students_N2, "🚌 Bus Upcoming", f"Your bus passed {skipped_stop['stop_name']}", {"trip_id": trip_id, "status": "UPCOMING"})

            # C. Early Notification for Stop N + 3
            upcoming_order_3 = target_skip_order + 3
            students_N3 = self.get_students_for_route_stop(trip['route_id'], upcoming_order_3, trip['trip_type'])
            if students_N3:
                await self._broadcast_helper(students_N3, "🚌 Bus Upcoming", f"Your bus passed {skipped_stop['stop_name']}", {"trip_id": trip_id, "status": "UPCOMING"})

            # D. Early Notification for Stop N + 4
            upcoming_order_4 = target_skip_order + 4
            students_N4 = self.get_students_for_route_stop(trip['route_id'], upcoming_order_4, trip['trip_type'])
            if students_N4:
                await self._broadcast_helper(students_N4, "🚌 Bus Upcoming", f"Your bus passed {skipped_stop['stop_name']}", {"trip_id": trip_id, "status": "UPCOMING"})

            # E. Early Notification for Stop N + 5
            upcoming_order_5 = target_skip_order + 5
            students_N5 = self.get_students_for_route_stop(trip['route_id'], upcoming_order_5, trip['trip_type'])
            if students_N5:
                await self._broadcast_helper(students_N5, "🚌 Bus Upcoming", f"Your bus passed {skipped_stop['stop_name']}", {"trip_id": trip_id, "status": "UPCOMING"})

            return {
                "success": True, 
                "message": f"Stop {skipped_stop['stop_name']} skipped",
                "new_stop_order": target_skip_order
            }
        except Exception as e:
            logger.error(f"Manual skip error: {e}")
            return {"success": False, "error": str(e)}

    
    def update_route_fcm_cache(self, route_id: str):
        """Update FCM token cache for route stops"""
        try:
            # Get all stops for route with student/parent FCM tokens
            query = """
            SELECT 
                rs.stop_id,
                rs.stop_name,
                rs.pickup_stop_order,
                rs.drop_stop_order,
                JSON_ARRAYAGG(
                    JSON_OBJECT(
                        'fcm_token', ft.fcm_token,
                        'parent_id', ft.parent_id,
                        'parent_name', p.name
                    )
                ) as fcm_data
            FROM route_stops rs
            LEFT JOIN students s ON (
                (rs.stop_id = s.pickup_stop_id AND s.pickup_route_id = rs.route_id) OR
                (rs.stop_id = s.drop_stop_id AND s.drop_route_id = rs.route_id)
            )
            LEFT JOIN fcm_tokens ft ON (s.student_id = ft.student_id OR s.parent_id = ft.parent_id OR s.s_parent_id = ft.parent_id)
            LEFT JOIN parents p ON ft.parent_id = p.parent_id
            WHERE rs.route_id = %s AND s.transport_status = 'ACTIVE' 
            AND s.student_status = 'CURRENT' AND s.is_transport_user = True
            AND ft.fcm_token IS NOT NULL
            GROUP BY rs.stop_id, rs.stop_name, rs.pickup_stop_order, rs.drop_stop_order
            """
            
            stops_data = execute_query(query, (route_id,), fetch_all=True)
            
            # Create FCM cache map
            fcm_map = {}
            for stop in stops_data:
                fcm_map[stop['stop_id']] = {
                    "stop_name": stop['stop_name'],
                    "pickup_order": stop['pickup_stop_order'],
                    "drop_order": stop['drop_stop_order'],
                    "fcm_tokens": json.loads(stop['fcm_data']) if stop['fcm_data'] else []
                }
            
            # Update cache table
            cache_query = """
            INSERT INTO route_stop_fcm_cache (route_id, stop_fcm_map) 
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE 
            stop_fcm_map = VALUES(stop_fcm_map),
            updated_at = CURRENT_TIMESTAMP
            """
            
            execute_query(cache_query, (route_id, json.dumps(fcm_map)))
            
            return {"success": True, "route_id": route_id, "stops_cached": len(fcm_map)}
            
        except Exception as e:
            logger.error(f"FCM cache update error: {e}")
            return {"success": False, "error": str(e)}

# Global instances
bus_tracking_service = BusTrackingService()