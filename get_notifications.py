import requests
import json

BASE_URL = "http://127.0.0.1:8080/api/v1"

def get_all_notifications():
    url = f"{BASE_URL}/admin-parent-notifications"
    params = {"limit": 10} # Just get the last 10 for a quick view
    
    try:
        print(f"Fetching notifications from {url}...")
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            notifications = response.json()
            if not notifications:
                print("\nNo notification records found in the database.")
                return
            
            print(f"\n--- Latest {len(notifications)} Notifications ---")
            for n in notifications:
                print(f"Date: {n.get('created_at')}")
                print(f"Title: {n.get('title')}")
                print(f"Message: {n.get('message')}")
                print(f"Sent By Admin: {n.get('sent_by_admin_id')}")
                print("-" * 30)
        else:
            print(f"Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Failed to connect to API: {e}")

if __name__ == "__main__":
    get_all_notifications()
