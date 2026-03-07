import requests
import json
import sys

BASE_URL = "http://localhost:8080/api/v1"
ADMIN_KEY = "selvagam-admin-key-2024" 
HEADERS = {"x-admin-key": ADMIN_KEY}

def test_endpoint(f, name, method, path, payload=None, params=None):
    f.write(f"\n--- Testing {name} ({method} {path}) ---\n")
    url = f"{BASE_URL}{path}"
    try:
        if method == "GET":
            response = requests.get(url, params=params, headers=HEADERS)
        elif method == "POST":
            response = requests.post(url, json=payload, headers=HEADERS)
        
        f.write(f"Status Code: {response.status_code}\n")
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                f.write(f"Count: {len(data)}\n")
                if len(data) > 0:
                    f.write(f"First item: {json.dumps(data[0], indent=2)}\n")
            else:
                f.write(f"Response: {json.dumps(data, indent=2)}\n")
        else:
            f.write(f"Error Response: {response.text}\n")
    except Exception as e:
        f.write(f"Exception: {e}\n")

if __name__ == "__main__":
    trip_id = "6348b2c4-f060-4405-b56c-602460d7e543"
    student_id = "6e4c5102-20a6-413b-8ffc-7ad5d662f228"
    admin_id = "5081a93e-1533-4932-bf34-cd5b33a3606e"
    
    with open("test_results_detailed.txt", "w") as f:
        test_endpoint(f, "Get All Trips", "GET", "/trips")
        test_endpoint(f, "Get Single Trip", "GET", f"/trips/{trip_id}")
        
        notif_payload = {
            "title": "Test Title",
            "message": "Test Message",
            "student_id": student_id,
            "sent_by_admin_id": admin_id
        }
        test_endpoint(f, "Create Notification", "POST", "/admin-parent-notifications", payload=notif_payload)
        test_endpoint(f, "Get Notifs by Student", "GET", f"/admin-parent-notifications/student/{student_id}")
        test_endpoint(f, "Get FCM Tokens by Location", "GET", "/fcm-tokens/by-location/test")
    
    print("Test completed. See test_results_detailed.txt")
