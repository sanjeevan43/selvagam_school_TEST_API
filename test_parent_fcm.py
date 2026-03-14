import requests
import uuid

BASE_URL = "http://localhost:8080/api/v1"

def test_parent_fcm_patch():
    # 1. Get a parent
    r = requests.get(f"{BASE_URL}/parents")
    if r.status_code != 200 or not r.json():
        print("No parents found")
        return
    parent_id = r.json()[0]['parent_id']
    print(f"Testing parent: {parent_id}")

    # 2. Try to patch
    token = "test_token_" + str(uuid.uuid4())
    payload = {
        "fcm_token": token,
        "device_info": "Test Script"
    }
    
    print(f"Patching token...")
    r = requests.patch(f"{BASE_URL}/parents/{parent_id}/fcm-token", json=payload)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")

if __name__ == "__main__":
    test_parent_fcm_patch()
