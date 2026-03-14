import logging
from typing import Dict, Any, List
from app.core.database import execute_query, get_db
import json

logger = logging.getLogger(__name__)

class CascadeUpdateService:
    """Handle cascading updates across related tables"""
    
    def update_parent_cascades(self, parent_id: str, old_data: Dict = None, new_data: Dict = None):
        """Update all tables related to parent changes"""
        try:
            # Update FCM tokens cache for routes where this parent's students are enrolled
            routes_query = """
            SELECT DISTINCT s.pickup_route_id as route_id FROM students s 
            WHERE s.parent_id = %s OR s.s_parent_id = %s
            UNION
            SELECT DISTINCT s.drop_route_id as route_id FROM students s 
            WHERE s.parent_id = %s OR s.s_parent_id = %s
            """
            routes = execute_query(routes_query, (parent_id, parent_id, parent_id, parent_id), fetch_all=True)
            
            for route in routes:
                self.update_route_fcm_cache(route['route_id'])
                
            logger.info(f"Updated cascades for parent {parent_id}")
            return True
        except Exception as e:
            logger.error(f"Parent cascade update error: {e}")
            return False
    
    def update_student_cascades(self, student_id: str, old_data: Dict = None, new_data: Dict = None):
        """Update all tables related to student changes"""
        try:
            # Get student's routes
            student_query = "SELECT pickup_route_id, drop_route_id FROM students WHERE student_id = %s"
            student = execute_query(student_query, (student_id,), fetch_one=True)
            
            if student:
                # Update FCM cache for both pickup and drop routes
                self.update_route_fcm_cache(student['pickup_route_id'])
                if student['drop_route_id'] != student['pickup_route_id']:
                    self.update_route_fcm_cache(student['drop_route_id'])
                
                # If route changed, update old routes too
                if old_data:
                    if old_data.get('pickup_route_id') != student['pickup_route_id']:
                        self.update_route_fcm_cache(old_data['pickup_route_id'])
                    if old_data.get('drop_route_id') != student['drop_route_id']:
                        self.update_route_fcm_cache(old_data['drop_route_id'])
            
            logger.info(f"Updated cascades for student {student_id}")
            return True
        except Exception as e:
            logger.error(f"Student cascade update error: {e}")
            return False
    
    def update_route_cascades(self, route_id: str, old_data: Dict = None, new_data: Dict = None):
        """Update all tables related to route changes"""
        try:
            # Update FCM cache
            self.update_route_fcm_cache(route_id)
            
            # If route is deactivated, handle active trips
            if new_data and new_data.get('routes_active_status') == 'INACTIVE':
                execute_query(
                    "UPDATE trips SET status = 'CANCELED' WHERE route_id = %s AND status IN ('NOT_STARTED', 'ONGOING')",
                    (route_id,)
                )
            
            logger.info(f"Updated cascades for route {route_id}")
            return True
        except Exception as e:
            logger.error(f"Route cascade update error: {e}")
            return False
    
    def update_bus_cascades(self, bus_id: str, new_status: str):
        """Update cascades when bus status changes"""
        try:
            # If bus is scrapped or inactive, unassign from driver and route
            if new_status in ['SCRAP', 'INACTIVE']:
                execute_query(
                    "UPDATE buses SET driver_id = NULL, route_id = NULL WHERE bus_id = %s",
                    (bus_id,)
                )
                # Cancel any ongoing trips for this bus
                execute_query(
                    "UPDATE trips SET status = 'CANCELED' WHERE bus_id = %s AND status IN ('NOT_STARTED', 'ONGOING')",
                    (bus_id,)
                )
            logger.info(f"Updated cascades for bus {bus_id} with status {new_status}")
            return True
        except Exception as e:
            logger.error(f"Bus cascade update error: {e}")
            return False

    def update_bus_reassignment_cascades(self, bus_id: str, driver_id: str = None, route_id: str = None):
        """Update upcoming trips when bus driver or route is reassigned"""
        try:
            updates = []
            params = []
            if driver_id:
                updates.append("driver_id = %s")
                params.append(driver_id)
            if route_id:
                updates.append("route_id = %s")
                params.append(route_id)
            
            if updates:
                params.append(bus_id)
                query = f"UPDATE trips SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE bus_id = %s AND status = 'NOT_STARTED'"
                execute_query(query, tuple(params))
                logger.info(f"Updated NOT_STARTED trips for bus {bus_id} with new assignments")
            return True
        except Exception as e:
            logger.error(f"Bus reassignment cascade error: {e}")
            return False
    
    def update_route_stop_cascades(self, stop_id: str, old_data: Dict = None, new_data: Dict = None):
        """Update all tables related to route stop changes"""
        try:
            # Get route for this stop
            stop_query = "SELECT route_id FROM route_stops WHERE stop_id = %s"
            stop = execute_query(stop_query, (stop_id,), fetch_one=True)
            
            if stop:
                self.update_route_fcm_cache(stop['route_id'])
            
            logger.info(f"Updated cascades for route stop {stop_id}")
            return True
        except Exception as e:
            logger.error(f"Route stop cascade update error: {e}")
            return False
    
    def update_fcm_token_cascades(self, fcm_id: str, old_data: Dict = None, new_data: Dict = None):
        """Update all tables related to FCM token changes"""
        try:
            # Get affected routes through student/parent relationships
            if new_data and new_data.get('parent_id'):
                parent_id = new_data['parent_id']
                routes_query = """
                SELECT DISTINCT s.pickup_route_id as route_id FROM students s 
                WHERE s.parent_id = %s OR s.s_parent_id = %s
                UNION
                SELECT DISTINCT s.drop_route_id as route_id FROM students s 
                WHERE s.parent_id = %s OR s.s_parent_id = %s
                """
                routes = execute_query(routes_query, (parent_id, parent_id, parent_id, parent_id), fetch_all=True)
                
                for route in routes:
                    self.update_route_fcm_cache(route['route_id'])
            
            if new_data and new_data.get('student_id'):
                student_id = new_data['student_id']
                student_query = "SELECT pickup_route_id, drop_route_id FROM students WHERE student_id = %s"
                student = execute_query(student_query, (student_id,), fetch_one=True)
                
                if student:
                    self.update_route_fcm_cache(student['pickup_route_id'])
                    if student['drop_route_id'] != student['pickup_route_id']:
                        self.update_route_fcm_cache(student['drop_route_id'])
            
            logger.info(f"Updated cascades for FCM token {fcm_id}")
            return True
        except Exception as e:
            logger.error(f"FCM token cascade update error: {e}")
            return False
    
    def update_route_fcm_cache(self, route_id: str):
        """Update FCM token cache for a specific route"""
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
            logger.info(f"Updated FCM cache for route {route_id}")
            
        except Exception as e:
            logger.error(f"FCM cache update error for route {route_id}: {e}")
    
    def delete_cascades(self, table: str, record_id: str, record_data: Dict = None):
        """Handle cascading deletes"""
        try:
            if table == "parents":
                # Clean up FCM tokens
                execute_query("DELETE FROM fcm_tokens WHERE parent_id = %s", (record_id,))
                # Update routes where this parent's students were enrolled
                if record_data:
                    self.update_parent_cascades(record_id, record_data)
                    
            elif table == "students":
                # Clean up FCM tokens
                execute_query("DELETE FROM fcm_tokens WHERE student_id = %s", (record_id,))
                # Update route caches
                if record_data:
                    self.update_student_cascades(record_id, record_data)
                    
            elif table == "routes":
                # Clean up route cache
                execute_query("DELETE FROM route_stop_fcm_cache WHERE route_id = %s", (record_id,))
                # Cancel active trips
                execute_query(
                    "UPDATE trips SET status = 'CANCELED' WHERE route_id = %s AND status IN ('NOT_STARTED', 'ONGOING')",
                    (record_id,)
                )
                
            elif table == "route_stops":
                # Update route cache
                if record_data and record_data.get('route_id'):
                    self.update_route_fcm_cache(record_data['route_id'])
            
            logger.info(f"Completed delete cascades for {table} {record_id}")
            return True
        except Exception as e:
            logger.error(f"Delete cascade error for {table} {record_id}: {e}")
            return False

# Global instance
cascade_service = CascadeUpdateService()