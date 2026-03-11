import requests
import json
import uuid

BASE_URL = "http://localhost:8080/api/v1"
ADMIN_KEY = "selvagam-admin-key-2024"
HEADERS = {"x-admin-key": ADMIN_KEY}

def print_result(name, response):
    status = response.status_code
    summary = "PASS" if status < 400 else "FAIL"
    print(f"[{summary}] {name:<40} | Status: {status}")
    if status >= 400:
        try:
            print(f"      Error: {response.json().get('detail', response.text[:100])}")
        except:
            print(f"      Error: {response.text[:100]}")

def test_a_to_z():
    print("=== School Transport Management API: A to Z Verification ===\n")

    # 1. System Health & Docs
    try:
        health = requests.get("http://localhost:8080/health")
        print_result("System Health Check", health)
    except:
        print("[FAIL] System Health Check | Connection Refused")

    # 2. Authentication / Profiles
    # Note: Using a phone number that might exist or just checking the endpoint exists
    print_result("Admins List", requests.get(f"{BASE_URL}/admins", headers=HEADERS))
    
    # 3. Parents
    print_result("Parents List", requests.get(f"{BASE_URL}/parents", headers=HEADERS))
    print_result("Parent FCM Tokens", requests.get(f"{BASE_URL}/parents/fcm-tokens/all", headers=HEADERS))

    # 4. Drivers
    print_result("Drivers List", requests.get(f"{BASE_URL}/drivers", headers=HEADERS))
    print_result("Driver FCM Tokens", requests.get(f"{BASE_URL}/drivers/fcm-tokens/all", headers=HEADERS))

    # 5. Buses
    print_result("Buses List", requests.get(f"{BASE_URL}/buses", headers=HEADERS))

    # 6. Routes
    print_result("Routes List", requests.get(f"{BASE_URL}/routes", headers=HEADERS))

    # 7. Students
    print_result("Students List", requests.get(f"{BASE_URL}/students", headers=HEADERS))

    # 8. Trips
    print_result("Ongoing Trips", requests.get(f"{BASE_URL}/trips/ongoing/all", headers=HEADERS))

    # 9. Notifications
    print_result("Notification Service Status", requests.get(f"{BASE_URL}/notifications/status", headers=HEADERS))

    # 10. NEW FEATURES (Verification of recent work)
    print("\n--- Verifying Recent Features ---")
    
    # Test Permission Login Logic (Parent)
    parent_id = "7d92eafb-76eb-41ca-bc3b-633eb0afa71b"
    # Ensure parent has an active token first
    requests.put(f"{BASE_URL}/parents/{parent_id}/fcm-token", json={"fcm_token": "active-token-123"}, headers=HEADERS)
    
    # Attempt second login (should be PENDING)
    new_token = "verify-pending-token-" + str(uuid.uuid4())
    login_res = requests.put(f"{BASE_URL}/parents/{parent_id}/fcm-token", json={"fcm_token": new_token}, headers=HEADERS)
    print_result("Multi-device login (Parent - PENDING)", login_res)
    
    if login_res.status_code == 200 and login_res.json().get('status') == "PENDING_APPROVAL":
        req_id = login_res.json().get('request_id')
        # Test Status Endpoint
        status_res = requests.get(f"{BASE_URL}/auth/login-requests/{req_id}")
        print_result("Login Request Status Check", status_res)
        
        # Test Response Endpoint (Reject in this test for safety)
        respond_res = requests.post(f"{BASE_URL}/auth/login-requests/{req_id}/respond", json={"action": "REJECT"})
        print_result("Login Request Respond (REJECT)", respond_res)

    print("\n=== Verification Complete ===")

if __name__ == "__main__":
    test_a_to_z()
