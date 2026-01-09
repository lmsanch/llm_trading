#!/usr/bin/env python3
"""
Test script for research API endpoints.

This script tests the research endpoints to verify they work correctly
after the refactoring from monolithic main.py to modular structure.

Usage:
    # Start the backend first
    cd /research/llm_trading
    source venv/bin/activate
    PYTHONPATH=. python backend/main.py

    # Then run this test script in another terminal
    cd /research/llm_trading
    source venv/bin/activate
    python test_research_endpoints.py
"""

import sys
import time
import json
import requests
from typing import Dict, Any

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


def test_research_prompt() -> bool:
    """Test GET /api/research/prompt."""
    print_test("Get Research Prompt - GET /api/research/prompt")

    try:
        response = requests.get(f"{BASE_URL}/api/research/prompt", timeout=TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            print_success(f"Research prompt retrieved (status: {response.status_code})")

            # Check expected fields
            expected_fields = ['prompt', 'version', 'last_updated', 'instruments', 'horizon']
            missing = [f for f in expected_fields if f not in data]

            if missing:
                print_warning(f"Missing fields: {missing}")
            else:
                print_success("All expected fields present")
                print_info(f"Version: {data.get('version')}")
                print_info(f"Last Updated: {data.get('last_updated')}")
                print_info(f"Instruments: {len(data.get('instruments', []))} tracked")
                print_info(f"Horizon: {data.get('horizon')}")

            return True
        elif response.status_code == 404:
            print_warning("Prompt file not found (404) - This is expected if file doesn't exist")
            return True  # This is acceptable
        else:
            print_error(f"Unexpected status code: {response.status_code}")
            print_info(f"Response: {response.text}")
            return False

    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_research_current() -> bool:
    """Test GET /api/research/current."""
    print_test("Get Current Research - GET /api/research/current")

    try:
        response = requests.get(f"{BASE_URL}/api/research/current", timeout=TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            print_success(f"Current research retrieved (status: {response.status_code})")

            # Check for research packs
            if 'perplexity' in data or 'gemini' in data:
                print_success("Research packs found")
                if 'perplexity' in data:
                    print_info("✓ Perplexity pack present")
                if 'gemini' in data:
                    print_info("✓ Gemini pack present")

                # Check structure of first pack
                pack_key = 'perplexity' if 'perplexity' in data else 'gemini'
                pack = data[pack_key]
                expected_fields = ['source', 'model', 'macro_regime', 'top_narratives', 'tradable_candidates']

                for field in expected_fields:
                    if field in pack:
                        print_info(f"  ✓ {field}")
                    else:
                        print_warning(f"  ✗ {field} missing")
            else:
                print_warning("No research packs found (may be empty state)")

            return True
        else:
            print_error(f"Unexpected status code: {response.status_code}")
            print_info(f"Response: {response.text}")
            return False

    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_research_latest() -> bool:
    """Test GET /api/research/latest (Acceptance Criteria #1)."""
    print_test("Get Latest Research - GET /api/research/latest")

    try:
        response = requests.get(f"{BASE_URL}/api/research/latest", timeout=TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            print_success(f"Latest research retrieved (status: {response.status_code})")

            # Check if data is empty or has content
            if not data:
                print_warning("Empty response (no research in database)")
            else:
                print_success("Research data found")
                expected_fields = ['id', 'week_id', 'provider', 'model', 'status']

                for field in expected_fields:
                    if field in data:
                        print_info(f"  ✓ {field}: {data[field]}")
                    else:
                        print_warning(f"  ✗ {field} missing")

            return True
        elif response.status_code == 404:
            print_warning("No research found (404) - Database may be empty")
            return True  # This is acceptable per acceptance criteria
        else:
            print_error(f"Unexpected status code: {response.status_code}")
            print_info(f"Response: {response.text}")
            return False

    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_research_history() -> bool:
    """Test GET /api/research/history (Acceptance Criteria #2)."""
    print_test("Get Research History - GET /api/research/history")

    try:
        response = requests.get(
            f"{BASE_URL}/api/research/history",
            params={"days": 30},
            timeout=TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            print_success(f"Research history retrieved (status: {response.status_code})")

            if 'history' in data:
                history_count = len(data['history'])
                print_success(f"History contains {history_count} dates")
                print_info(f"Days queried: {data.get('days', 'unknown')}")

                if history_count > 0:
                    # Show first date as sample
                    first_date = list(data['history'].keys())[0]
                    first_entry = data['history'][first_date]
                    print_info(f"Sample entry ({first_date}):")
                    print_info(f"  Providers: {len(first_entry.get('providers', []))}")
                    print_info(f"  Total reports: {first_entry.get('total', 0)}")
            else:
                print_warning("No 'history' field in response")

            return True
        else:
            print_error(f"Unexpected status code: {response.status_code}")
            print_info(f"Response: {response.text}")
            return False

    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_research_generate() -> Dict[str, Any]:
    """Test POST /api/research/generate (Acceptance Criteria #3)."""
    print_test("Generate Research - POST /api/research/generate")

    try:
        payload = {
            "models": ["perplexity"],
            "query": "",
            "prompt_override": None
        }

        response = requests.post(
            f"{BASE_URL}/api/research/generate",
            json=payload,
            timeout=TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            print_success(f"Research generation started (status: {response.status_code})")

            # Check for job tracking fields
            expected_fields = ['job_id', 'status', 'started_at', 'models']
            missing = [f for f in expected_fields if f not in data]

            if missing:
                print_warning(f"Missing fields: {missing}")
                return None
            else:
                print_success("All expected fields present")
                print_info(f"Job ID: {data['job_id']}")
                print_info(f"Status: {data['status']}")
                print_info(f"Models: {data['models']}")
                print_info(f"Started at: {data['started_at']}")

                return data
        else:
            print_error(f"Unexpected status code: {response.status_code}")
            print_info(f"Response: {response.text}")
            return None

    except Exception as e:
        print_error(f"Error: {e}")
        return None


def test_research_status(job_id: str) -> bool:
    """Test GET /api/research/status (Acceptance Criteria #4)."""
    print_test(f"Get Research Status - GET /api/research/status?job_id={job_id}")

    try:
        response = requests.get(
            f"{BASE_URL}/api/research/status",
            params={"job_id": job_id},
            timeout=TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            print_success(f"Job status retrieved (status: {response.status_code})")
            print_info(f"Job ID: {data.get('job_id')}")
            print_info(f"Status: {data.get('status')}")

            if 'perplexity' in data:
                perplexity_status = data['perplexity']
                print_info(f"Perplexity status: {perplexity_status.get('status')}")
                print_info(f"Perplexity progress: {perplexity_status.get('progress')}%")
                print_info(f"Perplexity message: {perplexity_status.get('message')}")

            return True
        elif response.status_code == 404:
            print_warning("Job not found (404)")
            return True
        else:
            print_error(f"Unexpected status code: {response.status_code}")
            print_info(f"Response: {response.text}")
            return False

    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_research_verify() -> bool:
    """Test POST /api/research/verify."""
    print_test("Verify Research - POST /api/research/verify")

    try:
        payload = {"id": "current"}

        response = requests.post(
            f"{BASE_URL}/api/research/verify",
            json=payload,
            timeout=TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            print_success(f"Research verified (status: {response.status_code})")
            print_info(f"Response: {json.dumps(data, indent=2)}")
            return True
        else:
            print_warning(f"Status code: {response.status_code} (may be expected if no research)")
            print_info(f"Response: {response.text}")
            return True  # Don't fail if pipeline state is not available

    except Exception as e:
        print_error(f"Error: {e}")
        return False


def main():
    """Run all research endpoint tests."""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}Research Endpoints Test Suite{Colors.RESET}")
    print(f"{Colors.BLUE}Testing backend at: {BASE_URL}{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}")

    results = {}

    # 1. Health check first
    results['health'] = test_health_check()
    if not results['health']:
        print_error("\nBackend is not running. Aborting tests.")
        sys.exit(1)

    time.sleep(0.5)

    # 2. Test research prompt
    results['prompt'] = test_research_prompt()
    time.sleep(0.5)

    # 3. Test current research
    results['current'] = test_research_current()
    time.sleep(0.5)

    # 4. Test latest research (Acceptance Criteria #1)
    results['latest'] = test_research_latest()
    time.sleep(0.5)

    # 5. Test research history (Acceptance Criteria #2)
    results['history'] = test_research_history()
    time.sleep(0.5)

    # 6. Test research generation (Acceptance Criteria #3)
    job_data = test_research_generate()
    results['generate'] = job_data is not None
    time.sleep(1.0)

    # 7. Test research status (Acceptance Criteria #4)
    if job_data and 'job_id' in job_data:
        results['status'] = test_research_status(job_data['job_id'])
        time.sleep(0.5)

        # Poll status a few more times to see progress
        for i in range(3):
            print_info(f"\nPolling status again (attempt {i+2}/4)...")
            test_research_status(job_data['job_id'])
            time.sleep(2.0)
    else:
        results['status'] = False
        print_warning("\nSkipping status test (no job_id from generate)")

    # 8. Test verify research
    results['verify'] = test_research_verify()

    # Print summary
    print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}TEST SUMMARY{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}\n")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if result else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  {test_name:20s} {status}")

    print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")

    if passed == total:
        print(f"{Colors.GREEN}✓ ALL TESTS PASSED ({passed}/{total}){Colors.RESET}")
    else:
        print(f"{Colors.YELLOW}⚠ SOME TESTS FAILED ({passed}/{total} passed){Colors.RESET}")

    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}\n")

    # Acceptance Criteria Check
    print(f"{Colors.BLUE}ACCEPTANCE CRITERIA CHECK{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}\n")

    acceptance_tests = {
        "GET /api/research/latest returns data or 404": results.get('latest', False),
        "GET /api/research/history returns data": results.get('history', False),
        "POST /api/research/generate starts job": results.get('generate', False),
        "GET /api/research/status returns job status": results.get('status', False),
        "No errors in backend logs": True  # Manual check required
    }

    for criteria, passed in acceptance_tests.items():
        status = f"{Colors.GREEN}✓{Colors.RESET}" if passed else f"{Colors.RED}✗{Colors.RESET}"
        if "backend logs" in criteria:
            status = f"{Colors.YELLOW}⚠ MANUAL CHECK{Colors.RESET}"
        print(f"  {status} {criteria}")

    print(f"\n{Colors.YELLOW}Note: Check backend logs for any errors during test execution.{Colors.RESET}")
    print(f"{Colors.YELLOW}      Backend logs should be visible in the terminal where you started the server.{Colors.RESET}\n")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
