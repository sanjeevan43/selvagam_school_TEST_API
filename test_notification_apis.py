import requests
import json

BASE_URL = "http://localhost:8080/api/v1"
ADMIN_KEY = "selvagam-admin-key-2024"
HEADERS = {"x-admin-key": ADMIN_KEY}

def test_status():
    print("\n[1] Testing /notifications/status")
    try:
        response = requests.get(f"{BASE_URL}/notifications/status")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

def test_send_notification():
    print("\n[2] Testing /send-notification")
    payload = {
        "title": "Test Title",
        "body": "Test Body",
        "topic": "all_users",
        "message_type": "audio"
    }
    try:
        response = requests.post(f"{BASE_URL}/send-notification", json=payload, headers=HEADERS)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

def test_broadcast_drivers():
    print("\n[3] Testing /notifications/broadcast/drivers")
    payload = {
        "title": "Driver Broadcast",
        "body": "Message for all drivers",
        "message_type": "audio"
    }
    try:
        response = requests.post(f"{BASE_URL}/notifications/broadcast/drivers", json=payload, headers=HEADERS)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

def test_broadcast_parents():
    print("\n[4] Testing /notifications/broadcast/parents")
    payload = {
        "title": "Parent Broadcast",
        "body": "Message for all parents",
        "messageType": "audio"
    }
    try:
        response = requests.post(f"{BASE_URL}/notifications/broadcast/parents", json=payload, headers=HEADERS)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

def test_student_notification(student_id):
    print(f"\n[5] Testing /notifications/student/{student_id}")
    payload = {
        "title": "Student Alert",
        "body": "Notification for student",
        "message_type": "audio"
    }
    try:
        response = requests.post(f"{BASE_URL}/notifications/student/{student_id}", json=payload, headers=HEADERS)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

def test_parent_notification(parent_id):
    print(f"\n[6] Testing /notifications/parent/{parent_id}")
    payload = {
        "title": "Parent Alert",
        "body": "Notification for parent",
        "message_type": "audio"
    }
    try:
        response = requests.post(f"{BASE_URL}/notifications/parent/{parent_id}", json=payload, headers=HEADERS)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

def test_route_notification(route_id):
    print(f"\n[7] Testing /notifications/route/{route_id}")
    payload = {
        "title": "Route Update",
        "body": "Notification for route users",
        "message_type": "audio"
    }
    try:
        response = requests.post(f"{BASE_URL}/notifications/route/{route_id}", json=payload, headers=HEADERS)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

def test_class_notification(class_id):
    print(f"\n[8] Testing /notifications/class/{class_id}")
    payload = {
        "title": "Class Announcement",
        "body": "Notification for class students",
        "message_type": "audio"
    }
    try:
        response = requests.post(f"{BASE_URL}/notifications/class/{class_id}", json=payload, headers=HEADERS)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

def test_trip_start(trip_id):
    print(f"\n[9] Testing /trip/start?trip_id={trip_id}")
    try:
        response = requests.post(f"{BASE_URL}/trip/start", params={"trip_id": trip_id}, headers=HEADERS)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

def test_trip_complete(trip_id):
    print(f"\n[10] Testing /trip/complete?trip_id={trip_id}")
    try:
        response = requests.post(f"{BASE_URL}/trip/complete", params={"trip_id": trip_id}, headers=HEADERS)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Real IDs from DB
    student_id = "6e4c5102-20a6-413b-8ffc-7ad5d662f228"
    parent_id = "7d92eafb-76eb-41ca-bc3b-633eb0afa71b"
    route_id = "3af62acb-491e-4dbc-b25f-fe0a8b35171f"
    class_id = "02dc54f3-1977-4829-94f1-70549e09a031"
    trip_id = "6348b2c4-f060-4405-b56c-602460d7e543"

    test_status()
    test_send_notification()
    test_broadcast_drivers()
    test_broadcast_parents()
    test_student_notification(student_id)
    test_parent_notification(parent_id)
    test_route_notification(route_id)
    test_class_notification(class_id)
    test_trip_start(trip_id)
    test_trip_complete(trip_id)
