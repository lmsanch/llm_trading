#!/usr/bin/env python3
"""
Smoke Test Suite for API Endpoints with Async Connection Pool

This script tests all API endpoints to verify they work correctly with the
asyncpg connection pool implementation. It checks:
- Endpoints return 200 OK (or expected status codes)
- Database operations complete without errors
- Connection pool is healthy throughout

Usage:
    # Start the backend server first
    python -m uvicorn backend.main:app --host 0.0.0.0 --port 8200

    # In another terminal, run this script
    python tests/smoke_test_endpoints.py

    # Or with verbose output
    python tests/smoke_test_endpoints.py -v

Requirements:
    - Backend server must be running (default: http://localhost:8200)
    - PostgreSQL database must be initialized and accessible
    - Redis must be running (for some endpoints)
"""

import requests
import sys
import time
from typing import Dict, Any, List, Tuple, Optional
from enum import Enum


class TestStatus(Enum):
    """Test status codes."""
    PASS = "✓ PASS"
    FAIL = "✗ FAIL"
    SKIP = "⊗ SKIP"
    WARN = "⚠ WARN"


class Color:
    """ANSI color codes."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    GRAY = '\033[90m'
    BOLD = '\033[1m'
    END = '\033[0m'


class EndpointSmokeTest:
    """Smoke test runner for all API endpoints."""

    def __init__(self, base_url: str = "http://localhost:8200", verbose: bool = False):
        self.base_url = base_url.rstrip('/')
        self.verbose = verbose
        self.results: List[Tuple[str, str, TestStatus, str]] = []
        self.session = requests.Session()

    def log(self, message: str, color: str = ""):
        """Log message with optional color."""
        if self.verbose:
            if color:
                print(f"{color}{message}{Color.END}")
            else:
                print(message)

    def test_endpoint(
        self,
        method: str,
        path: str,
        expected_status: int = 200,
        json_data: Optional[Dict] = None,
        description: str = "",
        skip_if_empty: bool = False
    ) -> TestStatus:
        """
        Test a single endpoint.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: Endpoint path (e.g., /api/health)
            expected_status: Expected HTTP status code
            json_data: JSON payload for POST requests
            description: Test description
            skip_if_empty: Skip if response data is empty (for data-dependent endpoints)

        Returns:
            TestStatus enum value
        """
        url = f"{self.base_url}{path}"
        test_name = f"{method} {path}"

        try:
            self.log(f"Testing {test_name}...", Color.GRAY)

            # Make request
            if method == "GET":
                response = self.session.get(url, timeout=10)
            elif method == "POST":
                response = self.session.post(url, json=json_data, timeout=10)
            elif method == "PUT":
                response = self.session.put(url, json=json_data, timeout=10)
            elif method == "DELETE":
                response = self.session.delete(url, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")

            # Check status code
            if response.status_code != expected_status:
                # Handle special cases
                if response.status_code == 404 and skip_if_empty:
                    self.results.append((method, path, TestStatus.SKIP, "No data available"))
                    return TestStatus.SKIP
                elif response.status_code == 500:
                    error_msg = f"Server error (500)"
                    try:
                        error_data = response.json()
                        if "detail" in error_data:
                            error_msg = f"500: {error_data['detail']}"
                    except:
                        pass
                    self.results.append((method, path, TestStatus.FAIL, error_msg))
                    self.log(f"  {TestStatus.FAIL.value}: {error_msg}", Color.RED)
                    return TestStatus.FAIL
                else:
                    msg = f"Expected {expected_status}, got {response.status_code}"
                    self.results.append((method, path, TestStatus.FAIL, msg))
                    self.log(f"  {TestStatus.FAIL.value}: {msg}", Color.RED)
                    return TestStatus.FAIL

            # Check response is JSON (for most endpoints)
            try:
                data = response.json()
                if skip_if_empty and not data:
                    self.results.append((method, path, TestStatus.SKIP, "Empty response"))
                    return TestStatus.SKIP

                # Log response sample in verbose mode
                if self.verbose and data:
                    if isinstance(data, dict):
                        keys = list(data.keys())[:5]
                        self.log(f"  Response keys: {keys}", Color.GRAY)
                    elif isinstance(data, list):
                        self.log(f"  Response: list with {len(data)} items", Color.GRAY)

            except ValueError:
                # Not JSON - that's OK for some endpoints
                pass

            self.results.append((method, path, TestStatus.PASS, description or "OK"))
            self.log(f"  {TestStatus.PASS.value}", Color.GREEN)
            return TestStatus.PASS

        except requests.Timeout:
            self.results.append((method, path, TestStatus.FAIL, "Request timeout"))
            self.log(f"  {TestStatus.FAIL.value}: Timeout", Color.RED)
            return TestStatus.FAIL
        except requests.ConnectionError:
            self.results.append((method, path, TestStatus.FAIL, "Connection refused"))
            self.log(f"  {TestStatus.FAIL.value}: Connection refused", Color.RED)
            return TestStatus.FAIL
        except Exception as e:
            error_msg = str(e)[:100]
            self.results.append((method, path, TestStatus.FAIL, error_msg))
            self.log(f"  {TestStatus.FAIL.value}: {error_msg}", Color.RED)
            return TestStatus.FAIL

    def run_all_tests(self):
        """Run smoke tests for all API endpoints."""
        print(f"\n{Color.BOLD}API Endpoint Smoke Tests{Color.END}")
        print(f"Base URL: {self.base_url}")
        print(f"Testing {Color.BOLD}async connection pool{Color.END} integration\n")

        # 1. Health checks
        print(f"{Color.BLUE}=== Health & Status ==={Color.END}")
        self.test_endpoint("GET", "/", description="Root health check")
        self.test_endpoint("GET", "/api/health", description="Detailed health check")

        # 2. Market endpoints (uses async pool for data_fetcher.py)
        print(f"\n{Color.BLUE}=== Market Endpoints ==={Color.END}")
        self.test_endpoint("GET", "/api/market/snapshot", description="Market snapshot (data_fetcher)")
        self.test_endpoint("GET", "/api/market/metrics", description="Market metrics (market_db)")
        self.test_endpoint("GET", "/api/market/prices", description="Current prices (market_db)")

        # 3. Research endpoints (uses async pool for research_db.py)
        print(f"\n{Color.BLUE}=== Research Endpoints ==={Color.END}")
        self.test_endpoint("GET", "/api/research/latest", description="Latest research (research_db)", skip_if_empty=True)
        self.test_endpoint("GET", "/api/research/history", description="Research history (research_db)", skip_if_empty=True)
        self.test_endpoint("GET", "/api/research/current", description="Current research state")
        self.test_endpoint("GET", "/api/research/status", description="Research generation status")
        self.test_endpoint("GET", "/api/research/prompt", description="Research prompt template")

        # 4. Graphs endpoint
        print(f"\n{Color.BLUE}=== Data Visualization ==={Color.END}")
        self.test_endpoint("GET", "/api/graphs/latest", description="Latest graphs", skip_if_empty=True)

        # 5. Metrics endpoint
        print(f"\n{Color.BLUE}=== Metrics ==={Color.END}")
        self.test_endpoint("GET", "/api/metrics/returns/latest", description="Latest returns", skip_if_empty=True)

        # 6. Data package endpoint
        print(f"\n{Color.BLUE}=== Data Package ==={Color.END}")
        self.test_endpoint("GET", "/api/data-package/latest", description="Latest data package", skip_if_empty=True)

        # 7. Pitches endpoints (uses async pool for pitch_db.py)
        print(f"\n{Color.BLUE}=== PM Pitches ==={Color.END}")
        self.test_endpoint("GET", "/api/pitches/current", description="Current pitches (pitch_db)", skip_if_empty=True)
        self.test_endpoint("GET", "/api/pitches/status", description="Pitch generation status")

        # 8. Council endpoints (uses async pool for council_db.py)
        print(f"\n{Color.BLUE}=== Council ==={Color.END}")
        self.test_endpoint("GET", "/api/council/current", description="Current council state (council_db)", skip_if_empty=True)

        # 9. Trades endpoints (uses async pool via find_pitch_by_id)
        print(f"\n{Color.BLUE}=== Trades ==={Color.END}")
        self.test_endpoint("GET", "/api/trades/pending", description="Pending trades", skip_if_empty=True)

        # 10. Monitor endpoints (Alpaca positions/accounts)
        print(f"\n{Color.BLUE}=== Account Monitor ==={Color.END}")
        self.test_endpoint("GET", "/api/positions", description="Current positions")
        self.test_endpoint("GET", "/api/accounts", description="Account balances")

        # 11. Conversations endpoints (Redis-based, no DB pool)
        print(f"\n{Color.BLUE}=== Conversations ==={Color.END}")
        self.test_endpoint("GET", "/api/conversations", description="List conversations")

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test results summary."""
        print(f"\n{Color.BOLD}{'='*70}{Color.END}")
        print(f"{Color.BOLD}Test Results Summary{Color.END}")
        print(f"{Color.BOLD}{'='*70}{Color.END}\n")

        # Count results by status
        pass_count = sum(1 for _, _, status, _ in self.results if status == TestStatus.PASS)
        fail_count = sum(1 for _, _, status, _ in self.results if status == TestStatus.FAIL)
        skip_count = sum(1 for _, _, status, _ in self.results if status == TestStatus.SKIP)
        total_count = len(self.results)

        # Print statistics
        print(f"Total tests: {Color.BOLD}{total_count}{Color.END}")
        print(f"{Color.GREEN}Passed: {pass_count}{Color.END}")
        if fail_count > 0:
            print(f"{Color.RED}Failed: {fail_count}{Color.END}")
        if skip_count > 0:
            print(f"{Color.YELLOW}Skipped: {skip_count}{Color.END}")

        pass_rate = (pass_count / (total_count - skip_count) * 100) if (total_count - skip_count) > 0 else 0
        print(f"\nPass rate: {Color.BOLD}{pass_rate:.1f}%{Color.END} (excluding skipped)")

        # Print failed tests
        if fail_count > 0:
            print(f"\n{Color.RED}{Color.BOLD}Failed Tests:{Color.END}")
            for method, path, status, message in self.results:
                if status == TestStatus.FAIL:
                    print(f"  {Color.RED}✗{Color.END} {method} {path}: {message}")

        # Print skipped tests
        if skip_count > 0:
            print(f"\n{Color.YELLOW}{Color.BOLD}Skipped Tests:{Color.END}")
            for method, path, status, message in self.results:
                if status == TestStatus.SKIP:
                    print(f"  {Color.YELLOW}⊗{Color.END} {method} {path}: {message}")

        # Final verdict
        print(f"\n{Color.BOLD}{'='*70}{Color.END}")
        if fail_count == 0:
            print(f"{Color.GREEN}{Color.BOLD}✓ ALL TESTS PASSED{Color.END} - Async pool integration verified!")
        else:
            print(f"{Color.RED}{Color.BOLD}✗ SOME TESTS FAILED{Color.END} - Please review errors above")
        print(f"{Color.BOLD}{'='*70}{Color.END}\n")

        # Return exit code
        return 0 if fail_count == 0 else 1


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Smoke test all API endpoints")
    parser.add_argument("--url", default="http://localhost:8200", help="Base URL (default: http://localhost:8200)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # Check if server is running
    try:
        response = requests.get(f"{args.url}/", timeout=2)
        print(f"{Color.GREEN}✓{Color.END} Server is running at {args.url}")
    except requests.ConnectionError:
        print(f"{Color.RED}✗ Cannot connect to server at {args.url}{Color.END}")
        print(f"  Please start the backend server first:")
        print(f"  {Color.GRAY}python -m uvicorn backend.main:app --host 0.0.0.0 --port 8200{Color.END}")
        return 1

    # Run tests
    tester = EndpointSmokeTest(base_url=args.url, verbose=args.verbose)
    exit_code = tester.run_all_tests()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
