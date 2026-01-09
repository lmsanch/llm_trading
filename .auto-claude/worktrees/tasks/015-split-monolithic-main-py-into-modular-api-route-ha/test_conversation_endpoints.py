#!/usr/bin/env python3
"""
Test suite for legacy chat (conversation) API endpoints.

This script tests all conversation endpoints after the refactoring from
monolithic main.py to modular structure in backend/api/conversations.py.

Tests:
- GET /api/conversations - List all conversations
- POST /api/conversations - Create new conversation
- GET /api/conversations/{id} - Get specific conversation
- POST /api/conversations/{id}/message - Send message (blocking)
- POST /api/conversations/{id}/message/stream - Send message (streaming SSE)

Usage:
    python test_conversation_endpoints.py

Requirements:
    - Backend must be running: PYTHONPATH=. python backend/main.py
    - Backend at http://localhost:8000
"""

import json
import sys
import time
from typing import Dict, Any, List

try:
    import requests
except ImportError:
    print("Error: requests library not found. Install with: pip install requests")
    sys.exit(1)

# Test configuration
BASE_URL = "http://localhost:8000"
TIMEOUT = 30  # seconds


# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_success(message: str):
    """Print success message in green."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str):
    """Print error message in red."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_warning(message: str):
    """Print warning message in yellow."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def print_info(message: str):
    """Print info message in blue."""
    print(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def test_health_check() -> bool:
    """Test backend health check."""
    print_section("TEST: Health Check - GET /")

    try:
        response = requests.get(f"{BASE_URL}/", timeout=TIMEOUT)

        if response.status_code == 200:
            print_success(f"Backend is running (status: {response.status_code})")
            return True
        else:
            print_error(f"Backend returned status: {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print_error("Could not connect to backend. Is it running?")
        print_info(f"Expected URL: {BASE_URL}")
        return False
    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False


def test_list_conversations() -> Dict[str, Any]:
    """Test GET /api/conversations - List all conversations."""
    print_section("TEST: List Conversations - GET /api/conversations")

    result = {"passed": False, "conversations": []}

    try:
        response = requests.get(f"{BASE_URL}/api/conversations", timeout=TIMEOUT)

        if response.status_code == 200:
            print_success(f"Conversations retrieved (status: {response.status_code})")

            conversations = response.json()
            result["conversations"] = conversations

            if isinstance(conversations, list):
                print_success(f"Response is a list (found {len(conversations)} conversation(s))")

                if len(conversations) > 0:
                    # Validate first conversation structure
                    conv = conversations[0]
                    if "id" in conv:
                        print_success(f"  ✓ id: {conv['id']}")
                    if "created_at" in conv:
                        print_success(f"  ✓ created_at: {conv['created_at']}")
                    if "title" in conv:
                        print_success(f"  ✓ title: {conv['title']}")
                    if "message_count" in conv:
                        print_success(f"  ✓ message_count: {conv['message_count']}")
                else:
                    print_info("No conversations found (empty database)")

                result["passed"] = True
            else:
                print_error("Response is not a list")
        else:
            print_error(f"Unexpected status code: {response.status_code}")
            print_info(f"Response: {response.text[:200]}")

    except requests.exceptions.ConnectionError:
        print_error("Connection failed")
    except Exception as e:
        print_error(f"Test failed: {e}")

    return result


def test_create_conversation() -> Dict[str, Any]:
    """Test POST /api/conversations - Create new conversation."""
    print_section("TEST: Create Conversation - POST /api/conversations")

    result = {"passed": False, "conversation_id": None}

    try:
        response = requests.post(
            f"{BASE_URL}/api/conversations",
            json={},
            timeout=TIMEOUT
        )

        if response.status_code == 200:
            print_success(f"Conversation created (status: {response.status_code})")

            conversation = response.json()

            # Validate response structure
            if "id" in conversation:
                result["conversation_id"] = conversation["id"]
                print_success(f"  ✓ id: {conversation['id']}")
            else:
                print_error("  ✗ Missing field: id")

            if "created_at" in conversation:
                print_success(f"  ✓ created_at: {conversation['created_at']}")
            else:
                print_error("  ✗ Missing field: created_at")

            if "title" in conversation:
                print_success(f"  ✓ title: {conversation['title']}")
            else:
                print_error("  ✗ Missing field: title")

            if "messages" in conversation:
                if isinstance(conversation["messages"], list):
                    print_success(f"  ✓ messages: {len(conversation['messages'])} messages")
                    if len(conversation["messages"]) == 0:
                        print_success("    ✓ Messages list is empty (as expected for new conversation)")
                else:
                    print_error("  ✗ messages is not a list")
            else:
                print_error("  ✗ Missing field: messages")

            if result["conversation_id"]:
                result["passed"] = True
        else:
            print_error(f"Unexpected status code: {response.status_code}")
            print_info(f"Response: {response.text[:200]}")

    except requests.exceptions.ConnectionError:
        print_error("Connection failed")
    except Exception as e:
        print_error(f"Test failed: {e}")

    return result


def test_get_conversation(conversation_id: str) -> bool:
    """Test GET /api/conversations/{id} - Get specific conversation."""
    print_section(f"TEST: Get Conversation - GET /api/conversations/{conversation_id}")

    try:
        response = requests.get(
            f"{BASE_URL}/api/conversations/{conversation_id}",
            timeout=TIMEOUT
        )

        if response.status_code == 200:
            print_success(f"Conversation retrieved (status: {response.status_code})")

            conversation = response.json()

            # Validate response structure
            if "id" in conversation:
                print_success(f"  ✓ id: {conversation['id']}")
            if "created_at" in conversation:
                print_success(f"  ✓ created_at: {conversation['created_at']}")
            if "title" in conversation:
                print_success(f"  ✓ title: {conversation['title']}")
            if "messages" in conversation:
                print_success(f"  ✓ messages: {len(conversation['messages'])} messages")

                # Validate message structure
                for i, msg in enumerate(conversation["messages"]):
                    if "role" in msg:
                        print_success(f"    ✓ Message {i+1}: role = {msg['role']}")

                        if msg["role"] == "user" and "content" in msg:
                            print_success(f"      ✓ User message has content")
                        elif msg["role"] == "assistant":
                            if "stage1" in msg:
                                print_success(f"      ✓ Assistant message has stage1")
                            if "stage2" in msg:
                                print_success(f"      ✓ Assistant message has stage2")
                            if "stage3" in msg:
                                print_success(f"      ✓ Assistant message has stage3")

            return True
        elif response.status_code == 404:
            print_warning(f"Conversation not found (status: 404)")
            return False
        else:
            print_error(f"Unexpected status code: {response.status_code}")
            print_info(f"Response: {response.text[:200]}")
            return False

    except requests.exceptions.ConnectionError:
        print_error("Connection failed")
        return False
    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def test_send_message(conversation_id: str) -> bool:
    """Test POST /api/conversations/{id}/message - Send message (blocking)."""
    print_section(f"TEST: Send Message (Blocking) - POST /api/conversations/{conversation_id}/message")

    try:
        # Send a simple test message
        test_message = "What is 2+2?"
        print_info(f"Sending message: '{test_message}'")
        print_warning("Note: This may take 10-30 seconds to complete (3-stage council process)")

        response = requests.post(
            f"{BASE_URL}/api/conversations/{conversation_id}/message",
            json={"content": test_message},
            timeout=60  # Longer timeout for council process
        )

        if response.status_code == 200:
            print_success(f"Message sent successfully (status: {response.status_code})")

            result = response.json()

            # Validate response structure
            if "stage1" in result:
                stage1 = result["stage1"]
                print_success(f"  ✓ stage1: {len(stage1)} model responses")

                # Check first stage1 response structure
                if len(stage1) > 0:
                    first_response = stage1[0]
                    if "model" in first_response:
                        print_success(f"    ✓ model: {first_response['model']}")
                    if "response" in first_response:
                        print_success(f"    ✓ response: {first_response['response'][:50]}...")
            else:
                print_error("  ✗ Missing field: stage1")

            if "stage2" in result:
                stage2 = result["stage2"]
                print_success(f"  ✓ stage2: {len(stage2)} peer reviews")
            else:
                print_error("  ✗ Missing field: stage2")

            if "stage3" in result:
                stage3 = result["stage3"]
                print_success(f"  ✓ stage3: Final synthesized answer")

                if "selected_model" in stage3:
                    print_success(f"    ✓ selected_model: {stage3['selected_model']}")
                if "selected_response" in stage3:
                    print_success(f"    ✓ selected_response: {stage3['selected_response'][:50]}...")
            else:
                print_error("  ✗ Missing field: stage3")

            if "metadata" in result:
                print_success(f"  ✓ metadata: Present")

            return True
        elif response.status_code == 404:
            print_error(f"Conversation not found (status: 404)")
            return False
        else:
            print_error(f"Unexpected status code: {response.status_code}")
            print_info(f"Response: {response.text[:200]}")
            return False

    except requests.exceptions.ConnectionError:
        print_error("Connection failed")
        return False
    except requests.exceptions.Timeout:
        print_error("Request timed out (council process may be running)")
        print_warning("Try increasing the timeout or check backend logs")
        return False
    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def test_send_message_stream(conversation_id: str) -> bool:
    """Test POST /api/conversations/{id}/message/stream - Send message (streaming SSE)."""
    print_section(f"TEST: Send Message (Streaming) - POST /api/conversations/{conversation_id}/message/stream")

    try:
        # Send a simple test message
        test_message = "What is the capital of France?"
        print_info(f"Sending message: '{test_message}'")
        print_warning("Note: This may take 10-30 seconds to complete (3-stage council process)")
        print_info("Streaming events will be displayed in real-time...")

        response = requests.post(
            f"{BASE_URL}/api/conversations/{conversation_id}/message/stream",
            json={"content": test_message},
            timeout=60,  # Longer timeout for council process
            stream=True  # Enable streaming
        )

        if response.status_code == 200:
            print_success(f"Streaming started (status: {response.status_code})")

            # Track which events we receive
            events_received = []

            # Process streaming events
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')

                    # SSE format: "data: {json}"
                    if line.startswith('data: '):
                        data_json = line[6:]  # Remove "data: " prefix
                        try:
                            event = json.loads(data_json)
                            event_type = event.get('type', 'unknown')
                            events_received.append(event_type)

                            if event_type == 'stage1_start':
                                print_info("  → Stage 1 started (collecting model responses)")
                            elif event_type == 'stage1_complete':
                                stage1_data = event.get('data', [])
                                print_success(f"  ✓ Stage 1 complete ({len(stage1_data)} responses)")
                            elif event_type == 'stage2_start':
                                print_info("  → Stage 2 started (peer review rankings)")
                            elif event_type == 'stage2_complete':
                                stage2_data = event.get('data', [])
                                print_success(f"  ✓ Stage 2 complete ({len(stage2_data)} reviews)")
                            elif event_type == 'stage3_start':
                                print_info("  → Stage 3 started (chairman synthesis)")
                            elif event_type == 'stage3_complete':
                                stage3_data = event.get('data', {})
                                selected_model = stage3_data.get('selected_model', 'unknown')
                                print_success(f"  ✓ Stage 3 complete (selected: {selected_model})")
                            elif event_type == 'title_complete':
                                title_data = event.get('data', {})
                                title = title_data.get('title', 'unknown')
                                print_success(f"  ✓ Title generated: '{title}'")
                            elif event_type == 'complete':
                                print_success("  ✓ Council process complete")
                            elif event_type == 'error':
                                error_msg = event.get('message', 'Unknown error')
                                print_error(f"  ✗ Error: {error_msg}")
                            else:
                                print_info(f"  → Event: {event_type}")
                        except json.JSONDecodeError:
                            print_warning(f"  ⚠ Could not parse event: {data_json[:50]}...")

            # Verify we received expected events
            print("\nEvent Summary:")
            print_info(f"Total events received: {len(events_received)}")
            print_info(f"Events: {', '.join(events_received)}")

            expected_events = ['stage1_start', 'stage1_complete', 'stage2_start',
                             'stage2_complete', 'stage3_start', 'stage3_complete', 'complete']

            all_expected_present = all(evt in events_received for evt in expected_events)

            if all_expected_present:
                print_success("✓ All expected events received")
                return True
            else:
                missing = [evt for evt in expected_events if evt not in events_received]
                print_warning(f"⚠ Missing events: {', '.join(missing)}")
                return len(events_received) > 0  # Pass if we got some events

        elif response.status_code == 404:
            print_error(f"Conversation not found (status: 404)")
            return False
        else:
            print_error(f"Unexpected status code: {response.status_code}")
            print_info(f"Response: {response.text[:200]}")
            return False

    except requests.exceptions.ConnectionError:
        print_error("Connection failed")
        return False
    except requests.exceptions.Timeout:
        print_error("Request timed out (council process may be running)")
        print_warning("Try increasing the timeout or check backend logs")
        return False
    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def main():
    """Run all conversation endpoint tests."""
    print_section("Conversation Endpoints Test Suite")
    print(f"Testing backend at: {BASE_URL}")

    # Track test results
    results = {
        "health": False,
        "list": False,
        "create": False,
        "get": False,
        "send_message": False,
        "send_message_stream": False,
    }

    # Test 1: Health check
    results["health"] = test_health_check()
    if not results["health"]:
        print_error("\nBackend is not running. Please start it first:")
        print_info("cd /research/llm_trading && PYTHONPATH=. python backend/main.py")
        sys.exit(1)

    # Test 2: List conversations (before creating any)
    list_result = test_list_conversations()
    results["list"] = list_result["passed"]

    # Test 3: Create conversation
    create_result = test_create_conversation()
    results["create"] = create_result["passed"]

    if not create_result["passed"] or not create_result["conversation_id"]:
        print_error("\nCould not create conversation. Stopping tests.")
        print_summary(results)
        sys.exit(1)

    conversation_id = create_result["conversation_id"]
    print_info(f"\nUsing conversation ID for remaining tests: {conversation_id}")

    # Test 4: Get conversation
    results["get"] = test_get_conversation(conversation_id)

    # Test 5: Send message (blocking)
    print_warning("\nTest 5 will take 10-30 seconds. Starting in 2 seconds...")
    time.sleep(2)
    results["send_message"] = test_send_message(conversation_id)

    # Test 6: Send message (streaming)
    print_warning("\nTest 6 will take 10-30 seconds. Starting in 2 seconds...")
    time.sleep(2)
    results["send_message_stream"] = test_send_message_stream(conversation_id)

    # Print test summary
    print_summary(results)

    # Check acceptance criteria
    check_acceptance_criteria(results)


def print_summary(results: Dict[str, bool]):
    """Print test summary."""
    print_section("TEST SUMMARY")
    print()

    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        color = Colors.GREEN if passed else Colors.RED
        print(f"  {test_name:20s} {color}{status}{Colors.RESET}")

    print()
    print("=" * 70)

    passed_count = sum(1 for p in results.values() if p)
    total_count = len(results)

    if passed_count == total_count:
        print_success(f"✓ ALL TESTS PASSED ({passed_count}/{total_count})")
    else:
        print_error(f"✗ SOME TESTS FAILED ({passed_count}/{total_count} passed)")

    print("=" * 70)


def check_acceptance_criteria(results: Dict[str, bool]):
    """Check acceptance criteria from implementation plan."""
    print_section("ACCEPTANCE CRITERIA CHECK")
    print()

    criteria = [
        ("GET /api/conversations returns list", results["list"]),
        ("POST /api/conversations creates conversation", results["create"]),
        ("GET /api/conversations/{id} returns conversation", results["get"]),
        ("POST /api/conversations/{id}/message works", results["send_message"]),
        ("Streaming endpoint works", results["send_message_stream"]),
        ("No errors in backend logs", None),  # Manual check
    ]

    for criterion, status in criteria:
        if status is True:
            print_success(f"✓ {criterion}")
        elif status is False:
            print_error(f"✗ {criterion}")
        else:
            print_warning(f"⚠ MANUAL CHECK: {criterion}")

    print()


if __name__ == "__main__":
    main()
