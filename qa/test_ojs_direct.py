"""
Direct test of OJS API connectivity.
"""
import requests
import os
from django.conf import settings

# Read from .env
OJS_API_BASE_URL = "http://cheapradius.com/jpahs/index.php/jpahs/api/v1"
OJS_API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.IjRjYmUwOWRhM2FmYWVlYTc5ZDM1ODc4YWVjZWVlY2JkMTg1MjVhNTki.CaZPfWIoUs88bQEiTRPhAmAiepfk-Ag4xBIwGVJ-BuY"

def test_ojs_direct():
    """Test direct connection to OJS API."""
    print("Testing OJS API Connection")
    print(f"URL: {OJS_API_BASE_URL}")
    print(f"API Key: {OJS_API_KEY[:20]}...")
    print("="*60)
    
    # Test 1: List Journals
    print("\n1. Testing GET /journals")
    try:
        url = f"{OJS_API_BASE_URL}/journals"
        headers = {"Authorization": f"Bearer {OJS_API_KEY}"}
        print(f"   URL: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"   Error: {str(e)}")
    
    # Test 2: List Submissions
    print("\n2. Testing GET /submissions")
    try:
        url = f"{OJS_API_BASE_URL}/submissions"
        headers = {"Authorization": f"Bearer {OJS_API_KEY}"}
        print(f"   URL: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"   Error: {str(e)}")
    
    # Test 3: API root
    print("\n3. Testing GET /")
    try:
        url = OJS_API_BASE_URL
        headers = {"Authorization": f"Bearer {OJS_API_KEY}"}
        print(f"   URL: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:500]}")
    except Exception as e:
        print(f"   Error: {str(e)}")

if __name__ == "__main__":
    test_ojs_direct()
