import requests
import json
import time

BASE_URL = "http://localhost:8080/api/v1"
ADMIN_KEY = "selvagam-admin-key-2024"
HEADERS = {"x-admin-key": ADMIN_KEY}

def print_result(name, response):
    print(f"\n--- {name} ---")
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
    except:
        print(f"Response: {response.text}")

def test_all():
    # 1. Status
    print_result("Notifications Status", requests.get(f"{BASE_URL}/notifications/status"))

    # 2. Topic
    print_result("Send Topic", requests.post(f"{BASE_URL}/send-notification", json={
        "title": "Topic Test",
        "body": "Test message for all",
        "topic": "all_users"
    }, headers=HEADERS))

    # 3. Broadcast Drivers
    print_result("Broadcast Drivers", requests.post(f"{BASE_URL}/notifications/broadcast/drivers", json={
        "title": "Driver Alert",
        "body": "Daily check-in required"
    }, headers=HEADERS))

    # 4. Broadcast Parents
    print_result("Broadcast Parents", requests.post(f"{BASE_URL}/notifications/broadcast/parents", json={
        "title": "Parent Alert",
        "body": "Holiday announcement"
    }, headers=HEADERS))

    # IDs for specific tests
    ids = {
        "student": "6e4c5102-20a6-413b-8ffc-7ad5d662f228",
        "parent": "7d92eafb-76eb-41ca-bc3b-633eb0afa71b",
        "route": "3af62acb-491e-4dbc-b25f-fe0a8b35171f",
        "class": "02dc54f3-1977-4829-94f1-70549e09a031",
        "trip": "6348b2c4-f060-4405-b56c-602460d7e543",
        "token": "c3EZWcJzRCuge2sSLS4Qt_:APA91bFPc33ExEbUPvNpFeuDLqGSRlmpAWj48eyYClh7WHwoV9tRpnk0zdfhTEKQhPgU69XP1pGnNKpeajU"
    }

    # 5. Device
    print_result("Send Device", requests.post(f"{BASE_URL}/notifications/send-device", json={
        "title": "Direct Message",
        "body": "Testing device notification",
        "token": ids["token"]
    }, headers=HEADERS))

    # 6. Student
    print_result("Send Student", requests.post(f"{BASE_URL}/notifications/student/{ids['student']}", json={
        "title": "Student Found",
        "body": "Your bus is approaching"
    }, headers=HEADERS))

    # 7. Route
    print_result("Send Route", requests.post(f"{BASE_URL}/notifications/route/{ids['route']}", json={
        "title": "Route Update",
        "body": "Bus delayed on your route"
    }, headers=HEADERS))

    # 8. Class
    print_result("Send Class", requests.post(f"{BASE_URL}/notifications/class/{ids['class']}", json={
        "title": "Class Alert",
        "body": "Special announcement for class"
    }, headers=HEADERS))

    # 9. Trip Start
    print_result("Trip Start", requests.post(f"{BASE_URL}/trip/start", params={"trip_id": ids["trip"]}, headers=HEADERS))

    # 10. Bus Location Tracking
    print_result("Bus Tracking (Approach Stop 3)", requests.post(f"{BASE_URL}/bus-tracking/location", json={
        "trip_id": ids["trip"],
        "latitude": 11.0168, # Sample coords
        "longitude": 76.9558
    }, headers=HEADERS))

    # 11. Trip Complete
    print_result("Trip Complete", requests.post(f"{BASE_URL}/trip/complete", params={"trip_id": ids["trip"]}, headers=HEADERS))

    # 12. Manual Send
    print_result("Manual Send", requests.post(f"{BASE_URL}/notifications/manual-send", json={
        "title": "Manual Alert",
        "message": "Direct message to tokens",
        "tokens": [ids["token"]]
    }, headers=HEADERS))

if __name__ == "__main__":
    test_all()
