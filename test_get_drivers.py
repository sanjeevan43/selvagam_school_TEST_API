import httpx
import json

def test_get_drivers():
    url = "http://localhost:8080/api/v1/drivers"
    try:
        response = httpx.get(url)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("Successfully fetched drivers:")
            print(json.dumps(response.json(), indent=2)[:500] + "...")
        else:
            print(f"Failed to fetch drivers: {response.text}")
    except Exception as e:
        print(f"Error testing endpoint: {e}")

if __name__ == "__main__":
    test_get_drivers()
