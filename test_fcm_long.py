import requests
import uuid

BASE_URL = "http://localhost:8080/api/v1"

def test_driver_fcm_patch():
    # 1. Get a driver
    r = requests.get(f"{BASE_URL}/drivers")
    if r.status_code != 200 or not r.json():
        print("No drivers found")
        return
    driver_id = r.json()[0]['driver_id']
    print(f"Testing driver: {driver_id}")

    # 2. Try to patch a long token
    # A standard long token might be around 250+ characters
    long_token = "f" * 300 
    payload = {
        "fcm_token": long_token,
        "device_info": "Test Script"
    }
    
    print(f"Patching token (length {len(long_token)})...")
    r = requests.patch(f"{BASE_URL}/drivers/{driver_id}/fcm-token", json=payload)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")

if __name__ == "__main__":
    test_driver_fcm_patch()
