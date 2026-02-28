import logging
import asyncio
import os
import httpx
from typing import Dict, Any, List, Set, Optional
from geopy.distance import distance as geodesic
from app.notification_api.service import notification_service
from app.core.database import execute_query

logger = logging.getLogger(__name__)

# Constants
APPROACHING_RADIUS = 1000  # 1km - notification to be ready
ARRIVED_RADIUS = 300       # 300m - actual arrival/location notification

class ProximityTrackingService:
    def __init__(self):
        # In-memory storage for active tracking state
        self.active_trips: Dict[str, Dict[str, Any]] = {}
        self.notified_stops: Dict[str, Set[str]] = {}
        self.main_backend_url = os.getenv("MAIN_BACKEND_URL", "http://localhost:8080/api/v1")

    async def fetch_tokens_by_route(self, route_id: str) -> List[str]:
        """Fetch all parent tokens for a route (simplified fallback)"""
        try:
            query = """
            SELECT DISTINCT ft.fcm_token 
            FROM fcm_tokens ft
            JOIN students s ON (ft.student_id = s.student_id OR ft.parent_id = s.parent_id OR ft.parent_id = s.s_parent_id)
            WHERE (s.pickup_route_id = %s OR s.drop_route_id = %s)
            AND s.transport_status = 'ACTIVE'
            AND s.student_status = 'CURRENT'
            AND s.is_transport_user = 1
            AND ft.fcm_token IS NOT NULL
            """
            rows = execute_query(query, (route_id, route_id), fetch_all=True)
            return [r['fcm_token'] for r in rows if r['fcm_token']]
        except Exception as e:
            logger.error(f"Error fetching route tokens: {e}")
            return []

    async def fetch_route_stops(self, route_id: str, trip_type: str = "PICKUP") -> List[Dict]:
        """Fetch stops for a route with coordinates, aware of trip type"""
        order_field = "pickup_stop_order" if trip_type == "PICKUP" else "drop_stop_order"
        try:
            query = f"""
            SELECT stop_id, stop_name, latitude, longitude, {order_field} as stop_order
            FROM route_stops
            WHERE route_id = %s
            ORDER BY {order_field}
            """
            return execute_query(query, (route_id,), fetch_all=True) or []
        except Exception as e:
            logger.error(f"Error fetching route stops: {e}")
            return []


    async def process_location_update(self, trip_id: str, lat: float, lng: float):
        """Core proximity logic moved from notification_app"""
        logger.info(f"📍 Proximity Check: {trip_id} -> {lat}, {lng}")
        
        # Get trip details from DB to find the CURRENT stop order
        try:
            trip_info = execute_query("SELECT current_stop_order, route_id, trip_type FROM trips WHERE trip_id = %s", (trip_id,), fetch_one=True)
            if not trip_info:
                return {"success": False, "message": "Trip not found"}
            
            # Use current_stop_order from DB as the source of truth for order-based logic
            current_order = trip_info['current_stop_order']
            route_id = trip_info['route_id']
            
            # Initialize trip data in cache if missing (or if order changed significantly)
            if trip_id not in self.active_trips:
                stops = await self.fetch_route_stops(route_id, trip_info['trip_type'])
                self.active_trips[trip_id] = {
                    "trip_id": trip_id,
                    "route_id": route_id,
                    "stops": stops
                }
                self.notified_stops[trip_id] = set()
                logger.info(f"✅ Initialized proximity tracking for {trip_id}")
            
            trip_data = self.active_trips[trip_id]
            stops = trip_data.get("stops", [])
            current_notified = self.notified_stops[trip_id]
            current_loc = (lat, lng)
            
            results = []

            # Find the "Active" stop (just reached) and "Next" stop (approaching)
            active_stop = next((s for s in stops if s['stop_order'] == current_order), None)
            next_stop = next((s for s in stops if s['stop_order'] == current_order + 1), None)

            # --- 1. Handle Arrived Alert for Active Stop ---
            if active_stop:
                try:
                    stop_loc = (float(active_stop['latitude']), float(active_stop['longitude']))
                    dist = geodesic(current_loc, stop_loc).meters
                    
            # DEACTIVATED: Distance-based triggering removed per user request.
            # All notifications are now handled strictly by stop-order in BusTrackingService.
            return {
                "success": True, 
                "trip_id": trip_id, 
                "current_order": current_order,
                "notifications_sent": []
            }
            
        except Exception as e:
            import traceback
            logger.error(f"Proximity processing error: {e}")
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}

    async def get_stop_tokens(self, route_id: str, stop_id: str) -> List[str]:
        """Fetch tokens for students at a specific stop specifically"""
        try:
            query = """
            SELECT DISTINCT ft.fcm_token
            FROM students s
            JOIN fcm_tokens ft ON (s.student_id = ft.student_id OR s.parent_id = ft.parent_id OR s.s_parent_id = ft.parent_id)
            WHERE (s.pickup_stop_id = %s OR s.drop_stop_id = %s)
            AND (s.pickup_route_id = %s OR s.drop_route_id = %s)
            AND s.transport_status = 'ACTIVE'
            AND s.student_status = 'CURRENT'
            AND s.is_transport_user = 1
            AND ft.fcm_token IS NOT NULL
            """
            rows = execute_query(query, (stop_id, stop_id, route_id, route_id), fetch_all=True)
            return [r['fcm_token'] for r in rows if r['fcm_token']]
        except Exception as e:
            logger.error(f"Error fetching stop tokens: {e}")
            return []

    async def start_trip(self, trip_id: str, route_id: str):
        """Manual Start Trip Logic - updates DB status to ONGOING"""
        try:
            # Update trip status in DB, making sure to null out ended_at to satisfy CHECK constraints
            execute_query(
                "UPDATE trips SET status = 'ONGOING', started_at = CURRENT_TIMESTAMP, ended_at = NULL, updated_at = CURRENT_TIMESTAMP WHERE trip_id = %s",
                (trip_id,)
            )
            logger.info(f"✅ Trip {trip_id} marked as ONGOING in DB")
        except Exception as e:
            logger.error(f"Failed to update trip status to ONGOING: {e}")

        tokens = await self.fetch_tokens_by_route(route_id)
        if tokens:
            await notification_service.broadcast_to_tokens(
                tokens, "🚌 Bus Started", "Your bus has started the trip", 
                {"trip_id": trip_id, "route_id": route_id, "status": "STARTED"}
            )
        return {"success": True, "recipients": len(tokens)}

    async def complete_trip(self, trip_id: str, route_id: str):
        """Manual Complete Trip Logic - updates DB status to COMPLETED"""
        try:
            # Update trip status in DB
            execute_query(
                "UPDATE trips SET status = 'COMPLETED', ended_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE trip_id = %s",
                (trip_id,)
            )
            logger.info(f"✅ Trip {trip_id} marked as COMPLETED in DB")
        except Exception as e:
            logger.error(f"Failed to update trip status to COMPLETED: {e}")

        tokens = await self.fetch_tokens_by_route(route_id)
        if tokens:
            await notification_service.broadcast_to_tokens(
                tokens, "✅ Trip Completed", "Your bus has completed the trip", 
                {"trip_id": trip_id, "route_id": route_id, "status": "COMPLETED"}
            )
        
        # Cleanup in-memory state
        if trip_id in self.active_trips:
            del self.active_trips[trip_id]
        if trip_id in self.notified_stops:
            del self.notified_stops[trip_id]
            
        return {"success": True, "recipients": len(tokens)}

# Global instance
proximity_service = ProximityTrackingService()
