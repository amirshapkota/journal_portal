"""
Discover available OJS API endpoints.
"""
import requests

OJS_API_BASE_URL = "http://cheapradius.com/jpahs/index.php/jpahs/api/v1"
OJS_API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.IjRjYmUwOWRhM2FmYWVlYTc5ZDM1ODc4YWVjZWVlY2JkMTg1MjVhNTki.CaZPfWIoUs88bQEiTRPhAmAiepfk-Ag4xBIwGVJ-BuY"

endpoints = [
    "/submissions",
    "/submissions/1",
    "/contexts",
    "/issues",
    "/publications",
    "/_submissions",
    "/users",
    "/reviews",
    "/reviewRounds",
    "/discussions",
]

headers = {"Authorization": f"Bearer {OJS_API_KEY}"}

print("Testing OJS API Endpoints")
print("="*60)

for endpoint in endpoints:
    url = f"{OJS_API_BASE_URL}{endpoint}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        status_emoji = "OK" if response.status_code == 200 else "NO"
        print(f"{status_emoji} {endpoint:30} Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   → {response.text[:100]}...")
    except Exception as e:
        print(f"NO {endpoint:30} Error: {str(e)[:50]}")
