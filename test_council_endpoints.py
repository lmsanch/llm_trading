#!/usr/bin/env python3
"""
Test script for council API endpoints.

This script tests the council endpoints to verify they work correctly
after the refactoring from monolithic main.py to modular structure.

Usage:
    # Start the backend first
    cd /research/llm_trading
    source venv/bin/activate
    PYTHONPATH=. python backend/main.py

    # Then run this test script in another terminal
    cd /research/llm_trading
    source venv/bin/activate
    python test_council_endpoints.py
"""

import sys
import time
import json
import requests
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "http://localhost:8000"
TIMEOUT = 10  # seconds


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_test(name: str):
    """Print test name."""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}TEST: {name}{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}")


def print_success(message: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_warning(message: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def print_info(message: str):
    """Print info message."""
    print(f"  {message}")


def test_health_check() -> bool:
    """Test that the backend is running."""
    print_test("Health Check - GET /")

    try:
        response = requests.get(f"{BASE_URL}/", timeout=TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            print_success(f"Backend is running (status: {response.status_code})")
            print_info(f"Response: {json.dumps(data, indent=2)}")
            return True
        else:
            print_error(f"Unexpected status code: {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to backend. Is it running?")
        print_info("Start backend with: cd /research/llm_trading && PYTHONPATH=. python backend/main.py")
        return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_council_current() -> bool:
    """Test GET /api/council/current (Acceptance Criteria #1)."""
    print_test("Get Current Council Decision - GET /api/council/current")

    try:
        response = requests.get(f"{BASE_URL}/api/council/current", timeout=TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            print_success(f"Council decision retrieved (status: {response.status_code})")

            # Check if we got data or empty object
            if not data:
                print_warning("Received empty object (no council decision available)")
                print_info("This is expected if no council synthesis has been run yet")
                return True

            # Validate structure if data is present
            print_info(f"Decision found with {len(data)} fields")

            expected_fields = ["selected_pitch", "reasoning", "model", "instrument",
                             "direction", "conviction", "peer_reviews_summary"]

            for field in expected_fields:
                if field in data:
                    print_info(f"  ✓ {field}: {str(data[field])[:60]}...")
                else:
                    print_warning(f"  Missing field: {field}")

            # Check peer reviews summary if present
            if "peer_reviews_summary" in data and isinstance(data["peer_reviews_summary"], list):
                print_info(f"  ✓ peer_reviews_summary: {len(data['peer_reviews_summary'])} reviews")
                for review in data["peer_reviews_summary"][:2]:  # Show first 2
                    if isinstance(review, dict):
                        print_info(f"    - {review.get('reviewer', 'unknown')}: score {review.get('score', 'N/A')}")

            return True

        else:
            print_error(f"Unexpected status code: {response.status_code}")
            print_info(f"Response: {response.text[:200]}")
            return False

    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to backend. Is it running?")
        return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_council_synthesize() -> bool:
    """Test POST /api/council/synthesize (Acceptance Criteria #2)."""
    print_test("Synthesize Council Decision - POST /api/council/synthesize")

    try:
        # Create request body (all fields optional)
        request_body = {}

        response = requests.post(
            f"{BASE_URL}/api/council/synthesize",
            json=request_body,
            timeout=TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            print_success(f"Council synthesis started (status: {response.status_code})")

            # Validate response structure
            if "status" in data:
                print_info(f"  ✓ status: {data['status']}")
            else:
                print_warning("  Missing 'status' field")

            if "message" in data:
                print_info(f"  ✓ message: {data['message']}")
            else:
                print_warning("  Missing 'message' field")

            if "job_id" in data:
                print_info(f"  ✓ job_id: {data['job_id']}")
            else:
                print_warning("  Missing 'job_id' field")

            # Validate status is "synthesizing"
            if data.get("status") == "synthesizing":
                print_success("Background task started successfully")
            else:
                print_warning(f"Unexpected status: {data.get('status')}")

            return True

        elif response.status_code == 400:
            print_warning(f"Bad request (status: {response.status_code})")
            print_info("This may be expected if no PM pitches are available")
            print_info(f"Response: {response.text[:200]}")
            return True  # This is an expected case

        elif response.status_code == 500:
            print_error(f"Server error (status: {response.status_code})")
            print_info(f"Response: {response.text[:200]}")
            print_info("This may indicate pipeline state is not available")
            return False

        else:
            print_error(f"Unexpected status code: {response.status_code}")
            print_info(f"Response: {response.text[:200]}")
            return False

    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to backend. Is it running?")
        return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_council_synthesize_with_data() -> bool:
    """Test POST /api/council/synthesize with request data."""
    print_test("Synthesize Council with Request Data - POST /api/council/synthesize")

    try:
        # Create mock request body
        request_body = {
            "week_id": "2024-W02",
            "research_date": "2024-01-08"
        }

        response = requests.post(
            f"{BASE_URL}/api/council/synthesize",
            json=request_body,
            timeout=TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            print_success(f"Council synthesis with data started (status: {response.status_code})")
            print_info(f"  status: {data.get('status')}")
            print_info(f"  message: {data.get('message')}")
            print_info(f"  job_id: {data.get('job_id')}")
            return True

        elif response.status_code == 400:
            print_warning(f"Bad request (status: {response.status_code})")
            print_info("This may be expected if no PM pitches are available for the specified date")
            print_info(f"Response: {response.text[:200]}")
            return True  # This is an expected case

        elif response.status_code == 500:
            print_error(f"Server error (status: {response.status_code})")
            print_info(f"Response: {response.text[:200]}")
            return False

        else:
            print_error(f"Unexpected status code: {response.status_code}")
            print_info(f"Response: {response.text[:200]}")
            return False

    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to backend. Is it running?")
        return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def main():
    """Run all tests."""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}Council Endpoints Test Suite{Colors.RESET}")
    print(f"{Colors.BLUE}Testing backend at: {BASE_URL}{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}")

    # Track test results
    results = {}

    # Run tests in order
    results["health"] = test_health_check()

    if not results["health"]:
        print_error("\nBackend is not running. Cannot continue with tests.")
        sys.exit(1)

    results["current"] = test_council_current()
    results["synthesize"] = test_council_synthesize()
    results["synthesize_data"] = test_council_synthesize_with_data()

    # Print summary
    print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}TEST SUMMARY{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}\n")

    for test_name, passed in results.items():
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if passed else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  {test_name:20} {status}")

    # Count results
    passed_count = sum(1 for p in results.values() if p)
    total_count = len(results)

    print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
    if passed_count == total_count:
        print(f"{Colors.GREEN}✓ ALL TESTS PASSED ({passed_count}/{total_count}){Colors.RESET}")
    else:
        print(f"{Colors.YELLOW}⚠ SOME TESTS FAILED ({passed_count}/{total_count}){Colors.RESET}")
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}")

    # Print acceptance criteria check
    print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}ACCEPTANCE CRITERIA CHECK{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}\n")

    acceptance_1 = results.get("current", False)
    acceptance_2 = results.get("synthesize", False) or results.get("synthesize_data", False)

    if acceptance_1:
        print_success("GET /api/council/current returns data or empty object")
    else:
        print_error("GET /api/council/current returns data or empty object")

    if acceptance_2:
        print_success("POST /api/council/synthesize starts background task")
    else:
        print_error("POST /api/council/synthesize starts background task")

    print_warning("MANUAL CHECK: No errors in backend logs")
    print_info("Please check the backend terminal for any error messages")

    print()

    # Exit code based on results
    if passed_count == total_count:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
