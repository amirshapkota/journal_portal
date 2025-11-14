"""
Test script for Analytics API endpoints.
Tests all 6 analytics endpoints with proper authentication.

Run this script after starting the Django development server:
python manage.py runserver

Then in another terminal:
python test_analytics_api.py
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:8000/api/v1"
ANALYTICS_URL = f"{BASE_URL}/analytics"

# Test credentials (update with your test users)
ADMIN_EMAIL = "analytics_test@test.com"
ADMIN_PASSWORD = "test123456"

EDITOR_EMAIL = "editor@test.com"
EDITOR_PASSWORD = "editor123"

AUTHOR_EMAIL = "author@test.com"
AUTHOR_PASSWORD = "author123"

REVIEWER_EMAIL = "reviewer@test.com"
REVIEWER_PASSWORD = "reviewer123"


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.END}\n")


def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def get_auth_token(email, password):
    """Get JWT access token."""
    print_info(f"Authenticating as {email}...")
    
    response = requests.post(
        f"{BASE_URL}/auth/login/",  # Updated path
        json={"email": email, "password": password}
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data.get('access')
        if token:
            print_success(f"Authentication successful for {email}")
            return token
        else:
            print_error(f"No access token in response")
            return None
    else:
        print_error(f"Authentication failed: {response.status_code}")
        print_error(f"Response: {response.text}")
        return None


def test_endpoint(name, url, token, method="GET", params=None, expected_status=200):
    """Test a single endpoint."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    print_info(f"Testing: {method} {url}")
    if params:
        print_info(f"Parameters: {json.dumps(params, indent=2)}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=params)
        else:
            print_error(f"Unsupported method: {method}")
            return False
        
        print_info(f"Status Code: {response.status_code}")
        
        if response.status_code == expected_status:
            print_success(f"✓ {name} - Status code correct ({expected_status})")
            
            try:
                data = response.json()
                print_success(f"✓ {name} - Valid JSON response")
                
                # Pretty print first level of response
                print(f"\n{Colors.CYAN}Response Structure:{Colors.END}")
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, dict):
                            print(f"  {key}: {{...}} ({len(value)} keys)")
                        elif isinstance(value, list):
                            print(f"  {key}: [...] ({len(value)} items)")
                        else:
                            print(f"  {key}: {value}")
                else:
                    print(f"  {type(data).__name__}")
                
                return True
            except json.JSONDecodeError:
                print_error(f"✗ {name} - Invalid JSON response")
                print_error(f"Response: {response.text[:200]}")
                return False
        else:
            print_error(f"✗ {name} - Expected {expected_status}, got {response.status_code}")
            print_error(f"Response: {response.text[:500]}")
            return False
            
    except requests.exceptions.RequestException as e:
        print_error(f"✗ {name} - Request failed: {str(e)}")
        return False


def test_analytics_dashboard(token):
    """Test analytics dashboard overview."""
    print_header("TEST 1: Dashboard Overview")
    
    success = test_endpoint(
        "Dashboard Overview",
        f"{ANALYTICS_URL}/dashboard/",
        token
    )
    
    return success


def test_submission_analytics(token, journal_id=None):
    """Test submission analytics endpoint."""
    print_header("TEST 2: Submission Analytics")
    
    # Test 1: Default (30 days)
    print(f"\n{Colors.BOLD}Test 2.1: Default parameters{Colors.END}")
    success1 = test_endpoint(
        "Submission Analytics - Default",
        f"{ANALYTICS_URL}/submissions/",
        token
    )
    
    # Test 2: Custom days
    print(f"\n{Colors.BOLD}Test 2.2: Custom time period (90 days){Colors.END}")
    success2 = test_endpoint(
        "Submission Analytics - 90 days",
        f"{ANALYTICS_URL}/submissions/",
        token,
        params={"days": 90}
    )
    
    # Test 3: With journal filter (if journal_id provided)
    success3 = True
    if journal_id:
        print(f"\n{Colors.BOLD}Test 2.3: Filter by journal{Colors.END}")
        success3 = test_endpoint(
            "Submission Analytics - Journal Filter",
            f"{ANALYTICS_URL}/submissions/",
            token,
            params={"days": 30, "journal_id": journal_id}
        )
    
    return success1 and success2 and success3


def test_reviewer_analytics(token):
    """Test reviewer analytics endpoint."""
    print_header("TEST 3: Reviewer Analytics")
    
    # Test 1: Default (90 days)
    print(f"\n{Colors.BOLD}Test 3.1: Default parameters{Colors.END}")
    success1 = test_endpoint(
        "Reviewer Analytics - Default",
        f"{ANALYTICS_URL}/reviewers/",
        token
    )
    
    # Test 2: Custom days
    print(f"\n{Colors.BOLD}Test 3.2: Custom time period (180 days){Colors.END}")
    success2 = test_endpoint(
        "Reviewer Analytics - 180 days",
        f"{ANALYTICS_URL}/reviewers/",
        token,
        params={"days": 180}
    )
    
    return success1 and success2


def test_journal_analytics(token, journal_id):
    """Test journal analytics endpoint."""
    print_header("TEST 4: Journal Analytics")
    
    if not journal_id:
        print_warning("Skipping journal analytics - no journal_id provided")
        return True
    
    # Test 1: Default parameters
    print(f"\n{Colors.BOLD}Test 4.1: Default parameters{Colors.END}")
    success1 = test_endpoint(
        "Journal Analytics - Default",
        f"{ANALYTICS_URL}/journals/",
        token,
        params={"journal_id": journal_id}
    )
    
    # Test 2: Custom days
    print(f"\n{Colors.BOLD}Test 4.2: Custom time period (90 days){Colors.END}")
    success2 = test_endpoint(
        "Journal Analytics - 90 days",
        f"{ANALYTICS_URL}/journals/",
        token,
        params={"journal_id": journal_id, "days": 90}
    )
    
    # Test 3: Missing journal_id (should fail)
    print(f"\n{Colors.BOLD}Test 4.3: Missing journal_id (expect 400){Colors.END}")
    success3 = test_endpoint(
        "Journal Analytics - No journal_id",
        f"{ANALYTICS_URL}/journals/",
        token,
        expected_status=400
    )
    
    return success1 and success2 and success3


def test_user_analytics(token):
    """Test user analytics endpoint."""
    print_header("TEST 5: User Analytics")
    
    # Test 1: Default (30 days)
    print(f"\n{Colors.BOLD}Test 5.1: Default parameters{Colors.END}")
    success1 = test_endpoint(
        "User Analytics - Default",
        f"{ANALYTICS_URL}/users/",
        token
    )
    
    # Test 2: Custom days
    print(f"\n{Colors.BOLD}Test 5.2: Custom time period (60 days){Colors.END}")
    success2 = test_endpoint(
        "User Analytics - 60 days",
        f"{ANALYTICS_URL}/users/",
        token,
        params={"days": 60}
    )
    
    return success1 and success2


def test_personal_analytics(token, user_role):
    """Test personal analytics endpoint."""
    print_header(f"TEST 6: Personal Analytics ({user_role})")
    
    success = test_endpoint(
        f"Personal Analytics - {user_role}",
        f"{ANALYTICS_URL}/my-analytics/",
        token
    )
    
    return success


def test_permissions():
    """Test permission restrictions."""
    print_header("TEST 7: Permission Restrictions")
    
    # Get author token (should NOT have access to admin analytics)
    author_token = get_auth_token(AUTHOR_EMAIL, AUTHOR_PASSWORD)
    
    if not author_token:
        print_warning("Skipping permission tests - author authentication failed")
        return True
    
    # Test 1: Author trying to access dashboard (should fail with 403)
    print(f"\n{Colors.BOLD}Test 7.1: Author accessing dashboard (expect 403){Colors.END}")
    success1 = test_endpoint(
        "Dashboard - Author (Forbidden)",
        f"{ANALYTICS_URL}/dashboard/",
        author_token,
        expected_status=403
    )
    
    # Test 2: Author trying to access submission analytics (should fail with 403)
    print(f"\n{Colors.BOLD}Test 7.2: Author accessing submission analytics (expect 403){Colors.END}")
    success2 = test_endpoint(
        "Submission Analytics - Author (Forbidden)",
        f"{ANALYTICS_URL}/submissions/",
        author_token,
        expected_status=403
    )
    
    # Test 3: Author accessing personal analytics (should succeed)
    print(f"\n{Colors.BOLD}Test 7.3: Author accessing personal analytics (expect 200){Colors.END}")
    success3 = test_endpoint(
        "Personal Analytics - Author (Allowed)",
        f"{ANALYTICS_URL}/my-analytics/",
        author_token,
        expected_status=200
    )
    
    # Test 4: Unauthenticated access (should fail with 401)
    print(f"\n{Colors.BOLD}Test 7.4: Unauthenticated access (expect 401){Colors.END}")
    success4 = test_endpoint(
        "Dashboard - No Auth (Unauthorized)",
        f"{ANALYTICS_URL}/dashboard/",
        None,
        expected_status=401
    )
    
    return success1 and success2 and success3 and success4


def get_journal_id(token):
    """Get a journal ID for testing."""
    print_info("Fetching journal ID for testing...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/journals/",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            if results:
                journal_id = results[0].get('id')
                journal_name = results[0].get('name', 'Unknown')
                print_success(f"Using journal: {journal_name} (ID: {journal_id})")
                return journal_id
            else:
                print_warning("No journals found in database")
                return None
        else:
            print_warning(f"Failed to fetch journals: {response.status_code}")
            return None
    except Exception as e:
        print_warning(f"Error fetching journal ID: {str(e)}")
        return None


def main():
    """Main test runner."""
    print_header("ANALYTICS API TEST SUITE")
    print_info(f"Base URL: {BASE_URL}")
    print_info(f"Analytics URL: {ANALYTICS_URL}")
    print_info(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0
    }
    
    # Get admin token for main tests
    admin_token = get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
    
    if not admin_token:
        print_error("Failed to authenticate as admin. Please check credentials.")
        print_error("Update ADMIN_EMAIL and ADMIN_PASSWORD in the script.")
        return
    
    # Get journal ID for testing
    journal_id = get_journal_id(admin_token)
    
    # Run tests
    tests = [
        ("Dashboard Overview", lambda: test_analytics_dashboard(admin_token)),
        ("Submission Analytics", lambda: test_submission_analytics(admin_token, journal_id)),
        ("Reviewer Analytics", lambda: test_reviewer_analytics(admin_token)),
        ("Journal Analytics", lambda: test_journal_analytics(admin_token, journal_id)),
        ("User Analytics", lambda: test_user_analytics(admin_token)),
        ("Personal Analytics (Admin)", lambda: test_personal_analytics(admin_token, "Admin")),
        ("Permission Restrictions", lambda: test_permissions()),
    ]
    
    # Test with different user roles if credentials are available
    try:
        editor_token = get_auth_token(EDITOR_EMAIL, EDITOR_PASSWORD)
        if editor_token:
            tests.append(("Personal Analytics (Editor)", lambda: test_personal_analytics(editor_token, "Editor")))
    except:
        print_warning("Editor authentication not available")
    
    try:
        reviewer_token = get_auth_token(REVIEWER_EMAIL, REVIEWER_PASSWORD)
        if reviewer_token:
            tests.append(("Personal Analytics (Reviewer)", lambda: test_personal_analytics(reviewer_token, "Reviewer")))
    except:
        print_warning("Reviewer authentication not available")
    
    # Execute all tests
    for test_name, test_func in tests:
        results["total"] += 1
        try:
            if test_func():
                results["passed"] += 1
            else:
                results["failed"] += 1
        except Exception as e:
            print_error(f"Test failed with exception: {str(e)}")
            results["failed"] += 1
    
    # Print summary
    print_header("TEST SUMMARY")
    print(f"\n{Colors.BOLD}Total Tests:{Colors.END} {results['total']}")
    print(f"{Colors.GREEN}{Colors.BOLD}Passed:{Colors.END} {results['passed']}")
    print(f"{Colors.RED}{Colors.BOLD}Failed:{Colors.END} {results['failed']}")
    
    success_rate = (results['passed'] / results['total'] * 100) if results['total'] > 0 else 0
    print(f"\n{Colors.BOLD}Success Rate:{Colors.END} {success_rate:.1f}%")
    
    if results['failed'] == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}{'🎉 ALL TESTS PASSED! 🎉'.center(80)}{Colors.END}")
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}{'⚠ SOME TESTS FAILED ⚠'.center(80)}{Colors.END}")
    
    print_info(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


if __name__ == "__main__":
    main()
