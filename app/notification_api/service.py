import os
import json
import time
import asyncio
from typing import List, Dict, Any
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, messaging
import logging

logger = logging.getLogger(__name__)

# Configuration
ADMIN_KEY = 'selvagam-admin-key-2024'

class FCMService:
    def __init__(self):
        self.creds_path = self._resolve_creds_path()
        self.initialized = False
        self.last_error = None
        if self.creds_path:
            self.init_firebase()

    def _resolve_creds_path(self):
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent
        possible_paths = [
            project_root / 'firebase-credentials.json',
            current_dir / 'firebase-credentials.json',
            Path(os.getcwd()) / 'firebase-credentials.json',
            Path('./firebase-credentials.json')
        ]
        path = next((p for p in possible_paths if p.exists()), None)
        if path:
            logger.info(f"FCM: Found credentials at {path}")
        else:
            logger.warning("FCM: firebase-credentials.json NOT FOUND in any expected location")
        return path

    def init_firebase(self):
        try:
            if not self.creds_path:
                self.creds_path = self._resolve_creds_path()
            
            if not self.creds_path:
                self.last_error = "firebase-credentials.json NOT FOUND"
                return False, self.last_error

            # Check if already initialized to avoid "app already exists" error
            try:
                firebase_admin.get_app()
                self.initialized = True
                return True, "Already initialized"
            except ValueError:
                # App not initialized, proceed
                pass

            with open(self.creds_path, 'r', encoding='utf-8') as f:
                service_account = json.load(f)
            
            project_id = service_account.get('project_id')
            if not project_id:
                self.last_error = "project_id MISSING in credentials JSON"
                logger.error(self.last_error)
                return False, self.last_error

            # Set environment variables for other SDKs if needed
            os.environ['GOOGLE_CLOUD_PROJECT'] = project_id
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(self.creds_path)

            cred = credentials.Certificate(service_account)
            firebase_admin.initialize_app(cred, {
                'projectId': project_id
            })

            logger.info(f"✅ Firebase Admin initialized for: {firebase_admin.get_app().project_id}")
            self.initialized = True
            self.last_error = None
            return True, "Success"
        except Exception as error:
            self.last_error = str(error)
            logger.error(f"❌ Firebase Error during init: {self.last_error}")
            return False, self.last_error

    def _get_sound_config(self, message_type: str):
        # Default to sound for almost everything unless explicitly silent
        is_silent = message_type in ["silent", "background", "data_only"]
        sound = "default" if not is_silent else None
        channel_id = "voice_notification_channel" if not is_silent else "default_channel"
        return sound, channel_id

    async def send_to_topic(self, title: str, body: str, topic: str = 'all_users', message_type: str = 'audio'):
        try:
            if not self.initialized:
                success, error = self.init_firebase()
                if not success:
                    return {"success": False, "error": f"Firebase not initialized: {error}"}

            sound, channel_id = self._get_sound_config(message_type)

            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data={
                    'type': 'admin_notification',
                    'title': title,
                    'body': body,
                    'messageType': message_type,
                    'timestamp': str(int(time.time() * 1000)),
                    'source': 'admin_panel'
                },
                android=messaging.AndroidConfig(
                    priority='high',
                    ttl=3600,
                    notification=messaging.AndroidNotification(
                        sound=sound,
                        channel_id=channel_id,
                        priority='high',
                        default_sound=True,
                        default_vibrate_timings=True
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(sound=sound, content_available=True)
                    )
                ),
                topic=topic
            )

            response = messaging.send(message)
            logger.info(f"Successfully sent topic message: {response}")
            return {"success": True, "messageId": response}
        except Exception as error:
            logger.error(f"FCM Topic Send Error: {error}")
            return {"success": False, "error": str(error)}

    async def send_to_device(self, title: str, body: str, token: str, recipient_type: str = 'parent', message_type: str = 'audio', data: Dict[str, Any] = None):
        if not token or token == "undefined" or token == "null":
            return {"success": False, "error": "Invalid token"}
            
        try:
            if not self.initialized:
                success, error = self.init_firebase()
                if not success:
                    return {"success": False, "error": f"Firebase not initialized: {error}"}

            sound, channel_id = self._get_sound_config(message_type)

            # Build data payload for Flutter compatibility
            fcm_data = {
                'type': str(data.get('type', 'admin_notification')) if data and 'type' in data else 'admin_notification',
                'title': str(title),
                'body': str(body),
                'messageType': str(message_type),
                'timestamp': str(int(time.time() * 1000)),
                'source': str(data.get('source', 'admin_panel')) if data and 'source' in data else 'admin_panel',
            }
            
            # Merge custom data
            if data:
                for k, v in data.items():
                    fcm_data[str(k)] = str(v)

            message = messaging.Message(
                token=token,
                notification=messaging.Notification(title=title, body=body),
                data=fcm_data,
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        sound=sound,
                        channel_id=channel_id,
                        priority='high',
                        default_sound=True,
                        default_vibrate_timings=True
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(sound=sound, content_available=True)
                    )
                )
            )

            # Using loop.run_in_executor to avoid blocking the event loop with the sync messaging.send
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: messaging.send(message))
            logger.info(f"FCM: Sent to device {token[:10]}... | ID: {response}")
            return {"success": True, "messageId": response}
        except Exception as error:
            err_msg = str(error)
            logger.error(f"FCM Device Send Error for token {token[:10]}...: {err_msg}")
            return {"success": False, "error": err_msg}

    async def send_force_logout(self, token: str):
        if not token: return {"success": False, "error": "No token"}
        try:
            if not self.initialized:
                self.init_firebase()

            message = messaging.Message(
                token=token,
                notification=messaging.Notification(
                    title="Session Expired",
                    body="You have been logged in on another device"
                ),
                data={
                    "type": "FORCE_LOGOUT",
                    "messageType": "text",
                    "source": "system"
                }
            )

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: messaging.send(message))
            return {"success": True, "messageId": response}
        except Exception as error:
            logger.error(f"FCM Force Logout Error: {error}")
            return {"success": False, "error": str(error)}

    async def send_login_request(self, token: str, request_id: str, device_info: str = "New Device"):
        """Send a permission request to the old device to allow a new login"""
        if not token: return {"success": False, "error": "No token"}
        try:
            if not self.initialized:
                self.init_firebase()

            message = messaging.Message(
                token=token,
                notification=messaging.Notification(
                    title="Login Permission Requested",
                    body=f"Someone is trying to login on a {device_info}. Do you allow this?"
                ),
                data={
                    "type": "LOGIN_PERMISSION_REQUEST",
                    "request_id": request_id,
                    "device_info": device_info,
                    "messageType": "action"
                }
            )
            response = messaging.send(message)
            return {"success": True, "message_id": response}
        except Exception as e:
            logger.error(f"FCM login request error: {e}")
            return {"success": False, "error": str(e)}

    async def broadcast_to_tokens(self, tokens: List[str], title: str, body: str, data: Dict[str, Any] = None, message_type: str = "audio"):
        if not tokens:
            return {"success": True, "delivered": 0, "total": 0}
            
        tasks = [
            self.send_to_device(title, body, token, data=data, message_type=message_type)
            for token in set(tokens) if token
        ]
        
        results = await asyncio.gather(*tasks)
        success_count = sum(1 for r in results if r.get("success"))
        
        return {"success": True, "delivered": success_count, "total": len(tokens)}


# Global instance
notification_service = FCMService()

