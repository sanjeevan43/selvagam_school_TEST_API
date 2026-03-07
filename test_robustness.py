import requests
import json

BASE_URL = "http://localhost:8080/api/v1"
ADMIN_KEY = "selvagam-admin-key-2024"
HEADERS = {"x-admin-key": ADMIN_KEY}

def test_trips_robust():
    try:
        res = requests.get(f"{BASE_URL}/trips", headers=HEADERS)
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            print(f"Total Trips: {len(data)}")
            # Check a few items
            for i in range(min(5, len(data))):
                print(f"Trip {i} stop_logs type: {type(data[i].get('stop_logs'))}")
                print(f"Trip {i} stop_logs: {data[i].get('stop_logs')}")
        else:
            print(f"Error: {res.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_trips_robust()
