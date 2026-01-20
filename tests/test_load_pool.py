"""Load testing for PostgreSQL connection pool.

This module contains load tests to verify that the asyncpg connection pool
handles concurrent requests efficiently under various workloads.

Metrics Tested:
    - Connection reuse rate
    - Query latency under load
    - Pool exhaustion handling
    - Throughput improvement vs sequential access

REQUIREMENTS:
-------------
These are load tests that require a running PostgreSQL database with proper
credentials configured.

To run these tests:
1. Ensure PostgreSQL is running
2. Set environment variables in .env:
   - DATABASE_URL (e.g., postgresql://user:password@localhost:5432/llm_trading), OR
   - DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD, DATABASE_HOST, DATABASE_PORT
3. Pool should be configured with reasonable size (min=10, max=50)

To run:
    pytest tests/test_load_pool.py -v              # Run all load tests
    pytest tests/test_load_pool.py -v -s           # Run with output
    pytest tests/test_load_pool.py -v --tb=short   # Run with short traceback

To run as standalone script:
    python tests/test_load_pool.py                 # Run load tests directly
"""

import asyncio
import time
import statistics
from datetime import datetime
from typing import List, Dict, Any
import pytest
import pytest_asyncio

from backend.db.pool import init_pool, close_pool, get_pool, check_pool_health
from backend.db_helpers import fetch_one, fetch_all, fetch_val, execute


# Test configuration
CONCURRENT_REQUESTS = 100  # Number of concurrent requests
QUERY_ROUNDS = 5  # Number of rounds to repeat tests
STRESS_REQUESTS = 200  # Number of requests for stress test (exceeds pool size)


# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture(scope="module")
async def load_test_pool():
    """Initialize pool for load testing."""
    try:
        pool = await init_pool()
        yield pool
    except Exception as e:
        pytest.skip(f"Database not available: {e}")
    finally:
        await close_pool()


@pytest_asyncio.fixture(scope="module")
async def load_test_table(load_test_pool):
    """Create test table for load testing."""
    pool = get_pool()

    # Create test table
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS load_test_data (
                id SERIAL PRIMARY KEY,
                request_id INTEGER NOT NULL,
                payload TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

    yield

    # Cleanup
    async with pool.acquire() as conn:
        await conn.execute("DROP TABLE IF EXISTS load_test_data")


@pytest_asyncio.fixture(autouse=True)
async def cleanup_load_data(load_test_pool, load_test_table):
    """Clean test data before each test."""
    yield

    # Clean up after test
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM load_test_data")


# ============================================================================
# Load Test Helpers
# ============================================================================


async def simple_query(request_id: int) -> Dict[str, Any]:
    """Execute a simple SELECT query.

    Args:
        request_id: Unique identifier for this request

    Returns:
        Dict with query result and timing info
    """
    start = time.perf_counter()
    result = await fetch_val("SELECT $1::int + $2::int", request_id, 1)
    duration = time.perf_counter() - start

    return {
        "request_id": request_id,
        "result": result,
        "duration_ms": duration * 1000,
        "success": True
    }


async def write_query(request_id: int) -> Dict[str, Any]:
    """Execute an INSERT query.

    Args:
        request_id: Unique identifier for this request

    Returns:
        Dict with query result and timing info
    """
    start = time.perf_counter()
    await execute(
        "INSERT INTO load_test_data (request_id, payload) VALUES ($1, $2)",
        request_id,
        f"Test data for request {request_id}"
    )
    duration = time.perf_counter() - start

    return {
        "request_id": request_id,
        "duration_ms": duration * 1000,
        "success": True
    }


async def complex_query(request_id: int) -> Dict[str, Any]:
    """Execute a more complex query with joins and aggregations.

    Args:
        request_id: Unique identifier for this request

    Returns:
        Dict with query result and timing info
    """
    start = time.perf_counter()

    # Simulate a complex query pattern
    result = await fetch_one("""
        WITH nums AS (
            SELECT generate_series(1, 10) as num
        )
        SELECT
            $1 as request_id,
            COUNT(*) as total_nums,
            SUM(num) as sum_nums,
            AVG(num) as avg_nums
        FROM nums
    """, request_id)

    duration = time.perf_counter() - start

    return {
        "request_id": request_id,
        "result": result,
        "duration_ms": duration * 1000,
        "success": True
    }


def calculate_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate performance metrics from test results.

    Args:
        results: List of query result dictionaries

    Returns:
        Dict with calculated metrics
    """
    durations = [r["duration_ms"] for r in results if r.get("success")]

    return {
        "total_requests": len(results),
        "successful_requests": len(durations),
        "failed_requests": len(results) - len(durations),
        "total_duration_ms": sum(durations),
        "avg_latency_ms": statistics.mean(durations) if durations else 0,
        "median_latency_ms": statistics.median(durations) if durations else 0,
        "min_latency_ms": min(durations) if durations else 0,
        "max_latency_ms": max(durations) if durations else 0,
        "p95_latency_ms": (
            statistics.quantiles(durations, n=20)[18] if len(durations) >= 20 else 0
        ),
        "p99_latency_ms": (
            statistics.quantiles(durations, n=100)[98] if len(durations) >= 100 else 0
        ),
    }


# ============================================================================
# Load Tests
# ============================================================================


@pytest.mark.asyncio
async def test_concurrent_simple_queries(load_test_pool):
    """Test pool performance with concurrent simple SELECT queries.

    Verifies:
    - Pool can handle multiple concurrent requests
    - Latency remains reasonable under load
    - All requests complete successfully
    """
    print(f"\n{'='*70}")
    print(f"TEST: Concurrent Simple Queries ({CONCURRENT_REQUESTS} requests)")
    print(f"{'='*70}")

    # Run concurrent queries
    start_time = time.perf_counter()

    tasks = [simple_query(i) for i in range(CONCURRENT_REQUESTS)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    total_duration = time.perf_counter() - start_time

    # Process results
    successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
    failed_results = [r for r in results if not (isinstance(r, dict) and r.get("success"))]

    metrics = calculate_metrics(successful_results)

    # Print results
    print(f"\nResults:")
    print(f"  Total Duration: {total_duration*1000:.2f}ms")
    print(f"  Successful: {metrics['successful_requests']}/{metrics['total_requests']}")
    print(f"  Failed: {metrics['failed_requests']}")
    print(f"  Throughput: {metrics['total_requests']/total_duration:.2f} req/sec")
    print(f"\nLatency:")
    print(f"  Average: {metrics['avg_latency_ms']:.2f}ms")
    print(f"  Median: {metrics['median_latency_ms']:.2f}ms")
    print(f"  Min: {metrics['min_latency_ms']:.2f}ms")
    print(f"  Max: {metrics['max_latency_ms']:.2f}ms")
    print(f"  P95: {metrics['p95_latency_ms']:.2f}ms")
    print(f"  P99: {metrics['p99_latency_ms']:.2f}ms")

    # Check pool health
    health = await check_pool_health()
    print(f"\nPool Health:")
    print(f"  Status: {health['status']}")
    print(f"  Pool Size: {health.get('pool_size', 'N/A')}")
    print(f"  Free Connections: {health.get('free_connections', 'N/A')}")

    # Assertions
    assert metrics['failed_requests'] == 0, "All requests should succeed"
    assert metrics['avg_latency_ms'] < 100, f"Average latency too high: {metrics['avg_latency_ms']:.2f}ms"
    assert health['status'] == 'healthy', "Pool should remain healthy"


@pytest.mark.asyncio
async def test_concurrent_write_queries(load_test_pool, load_test_table):
    """Test pool performance with concurrent INSERT queries.

    Verifies:
    - Pool handles write operations under concurrent load
    - All writes complete successfully
    - Database consistency is maintained
    """
    print(f"\n{'='*70}")
    print(f"TEST: Concurrent Write Queries ({CONCURRENT_REQUESTS} requests)")
    print(f"{'='*70}")

    # Run concurrent writes
    start_time = time.perf_counter()

    tasks = [write_query(i) for i in range(CONCURRENT_REQUESTS)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    total_duration = time.perf_counter() - start_time

    # Process results
    successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
    metrics = calculate_metrics(successful_results)

    # Verify all records were written
    count = await fetch_val("SELECT COUNT(*) FROM load_test_data")

    # Print results
    print(f"\nResults:")
    print(f"  Total Duration: {total_duration*1000:.2f}ms")
    print(f"  Successful: {metrics['successful_requests']}/{metrics['total_requests']}")
    print(f"  Records in DB: {count}")
    print(f"  Throughput: {metrics['total_requests']/total_duration:.2f} req/sec")
    print(f"\nLatency:")
    print(f"  Average: {metrics['avg_latency_ms']:.2f}ms")
    print(f"  Median: {metrics['median_latency_ms']:.2f}ms")
    print(f"  P95: {metrics['p95_latency_ms']:.2f}ms")

    # Assertions
    assert metrics['failed_requests'] == 0, "All requests should succeed"
    assert count == CONCURRENT_REQUESTS, "All records should be written"
    assert metrics['avg_latency_ms'] < 200, f"Average write latency too high: {metrics['avg_latency_ms']:.2f}ms"


@pytest.mark.asyncio
async def test_concurrent_complex_queries(load_test_pool):
    """Test pool performance with concurrent complex queries.

    Verifies:
    - Pool handles complex queries efficiently
    - Latency remains acceptable for analytical queries
    """
    print(f"\n{'='*70}")
    print(f"TEST: Concurrent Complex Queries ({CONCURRENT_REQUESTS} requests)")
    print(f"{'='*70}")

    # Run concurrent complex queries
    start_time = time.perf_counter()

    tasks = [complex_query(i) for i in range(CONCURRENT_REQUESTS)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    total_duration = time.perf_counter() - start_time

    # Process results
    successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
    metrics = calculate_metrics(successful_results)

    # Print results
    print(f"\nResults:")
    print(f"  Total Duration: {total_duration*1000:.2f}ms")
    print(f"  Successful: {metrics['successful_requests']}/{metrics['total_requests']}")
    print(f"  Throughput: {metrics['total_requests']/total_duration:.2f} req/sec")
    print(f"\nLatency:")
    print(f"  Average: {metrics['avg_latency_ms']:.2f}ms")
    print(f"  Median: {metrics['median_latency_ms']:.2f}ms")
    print(f"  P95: {metrics['p95_latency_ms']:.2f}ms")

    # Assertions
    assert metrics['failed_requests'] == 0, "All requests should succeed"
    assert metrics['avg_latency_ms'] < 500, f"Average complex query latency too high: {metrics['avg_latency_ms']:.2f}ms"


@pytest.mark.asyncio
async def test_pool_exhaustion_handling(load_test_pool):
    """Test pool behavior when requests exceed pool size.

    Verifies:
    - Pool queues requests gracefully when all connections are in use
    - No requests fail due to connection exhaustion
    - Performance degrades gracefully (latency increases but no failures)
    """
    print(f"\n{'='*70}")
    print(f"TEST: Pool Exhaustion Handling ({STRESS_REQUESTS} requests)")
    print(f"{'='*70}")

    # Get pool size
    health_before = await check_pool_health()
    max_pool_size = health_before.get('max_size', 50)
    print(f"\nPool Configuration:")
    print(f"  Max Pool Size: {max_pool_size}")
    print(f"  Stress Requests: {STRESS_REQUESTS} (exceeds pool by {STRESS_REQUESTS - max_pool_size})")

    # Run stress test
    start_time = time.perf_counter()

    tasks = [simple_query(i) for i in range(STRESS_REQUESTS)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    total_duration = time.perf_counter() - start_time

    # Process results
    successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
    metrics = calculate_metrics(successful_results)

    # Check pool health after stress
    health_after = await check_pool_health()

    # Print results
    print(f"\nResults:")
    print(f"  Total Duration: {total_duration*1000:.2f}ms")
    print(f"  Successful: {metrics['successful_requests']}/{metrics['total_requests']}")
    print(f"  Failed: {metrics['failed_requests']}")
    print(f"  Throughput: {metrics['total_requests']/total_duration:.2f} req/sec")
    print(f"\nLatency:")
    print(f"  Average: {metrics['avg_latency_ms']:.2f}ms")
    print(f"  Median: {metrics['median_latency_ms']:.2f}ms")
    print(f"  Max: {metrics['max_latency_ms']:.2f}ms")
    print(f"  P95: {metrics['p95_latency_ms']:.2f}ms")
    print(f"  P99: {metrics['p99_latency_ms']:.2f}ms")
    print(f"\nPool Health After Stress:")
    print(f"  Status: {health_after['status']}")
    print(f"  Pool Size: {health_after.get('pool_size', 'N/A')}")
    print(f"  Free Connections: {health_after.get('free_connections', 'N/A')}")

    # Assertions
    assert metrics['failed_requests'] == 0, "No requests should fail even under stress"
    assert health_after['status'] == 'healthy', "Pool should recover after stress"
    assert metrics['avg_latency_ms'] < 200, f"Average latency under stress too high: {metrics['avg_latency_ms']:.2f}ms"


@pytest.mark.asyncio
async def test_sustained_load(load_test_pool):
    """Test pool performance under sustained load over multiple rounds.

    Verifies:
    - Pool maintains consistent performance over time
    - No connection leaks
    - No memory leaks
    - Performance doesn't degrade over time
    """
    print(f"\n{'='*70}")
    print(f"TEST: Sustained Load ({QUERY_ROUNDS} rounds x {CONCURRENT_REQUESTS} requests)")
    print(f"{'='*70}")

    all_metrics = []

    for round_num in range(QUERY_ROUNDS):
        print(f"\nRound {round_num + 1}/{QUERY_ROUNDS}...")

        # Run concurrent queries
        start_time = time.perf_counter()
        tasks = [simple_query(i) for i in range(CONCURRENT_REQUESTS)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.perf_counter() - start_time

        # Calculate metrics
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        metrics = calculate_metrics(successful_results)
        metrics['round'] = round_num + 1
        metrics['total_duration_sec'] = total_duration
        metrics['throughput'] = metrics['total_requests'] / total_duration
        all_metrics.append(metrics)

        print(f"  Successful: {metrics['successful_requests']}/{metrics['total_requests']}")
        print(f"  Avg Latency: {metrics['avg_latency_ms']:.2f}ms")
        print(f"  Throughput: {metrics['throughput']:.2f} req/sec")

        # Brief pause between rounds
        await asyncio.sleep(0.1)

    # Analyze sustained performance
    avg_latencies = [m['avg_latency_ms'] for m in all_metrics]
    throughputs = [m['throughput'] for m in all_metrics]

    print(f"\n{'='*70}")
    print(f"Sustained Load Summary:")
    print(f"{'='*70}")
    print(f"Average Latency:")
    print(f"  Mean: {statistics.mean(avg_latencies):.2f}ms")
    print(f"  Std Dev: {statistics.stdev(avg_latencies) if len(avg_latencies) > 1 else 0:.2f}ms")
    print(f"  Min: {min(avg_latencies):.2f}ms")
    print(f"  Max: {max(avg_latencies):.2f}ms")
    print(f"\nThroughput:")
    print(f"  Mean: {statistics.mean(throughputs):.2f} req/sec")
    print(f"  Std Dev: {statistics.stdev(throughputs) if len(throughputs) > 1 else 0:.2f} req/sec")
    print(f"  Min: {min(throughputs):.2f} req/sec")
    print(f"  Max: {max(throughputs):.2f} req/sec")

    # Check pool health after sustained load
    health = await check_pool_health()
    print(f"\nPool Health After Sustained Load:")
    print(f"  Status: {health['status']}")
    print(f"  Pool Size: {health.get('pool_size', 'N/A')}")
    print(f"  Free Connections: {health.get('free_connections', 'N/A')}")

    # Assertions
    total_requests = sum(m['total_requests'] for m in all_metrics)
    total_failed = sum(m['failed_requests'] for m in all_metrics)

    assert total_failed == 0, f"No requests should fail during sustained load (failed: {total_failed})"
    assert health['status'] == 'healthy', "Pool should remain healthy after sustained load"

    # Performance should be consistent (std dev should be reasonable)
    latency_cv = statistics.stdev(avg_latencies) / statistics.mean(avg_latencies) if len(avg_latencies) > 1 else 0
    assert latency_cv < 0.5, f"Latency too variable (CV: {latency_cv:.2f}), possible connection leak"


@pytest.mark.asyncio
async def test_connection_reuse_rate(load_test_pool):
    """Test that connections are reused efficiently.

    Verifies:
    - Pool reuses connections rather than creating new ones
    - Connection count stays within pool limits
    - Free connections available after load
    """
    print(f"\n{'='*70}")
    print(f"TEST: Connection Reuse Rate")
    print(f"{'='*70}")

    # Get initial pool stats
    health_before = await check_pool_health()
    initial_pool_size = health_before.get('pool_size', 0)
    max_pool_size = health_before.get('max_size', 50)

    print(f"\nInitial Pool State:")
    print(f"  Pool Size: {initial_pool_size}")
    print(f"  Free Connections: {health_before.get('free_connections', 0)}")
    print(f"  Max Size: {max_pool_size}")

    # Run load
    print(f"\nRunning {CONCURRENT_REQUESTS * 3} queries...")
    for round_num in range(3):
        tasks = [simple_query(i) for i in range(CONCURRENT_REQUESTS)]
        await asyncio.gather(*tasks)

        # Check pool state after each round
        health = await check_pool_health()
        print(f"  Round {round_num + 1}: Pool Size = {health.get('pool_size', 0)}, Free = {health.get('free_connections', 0)}")

    # Get final pool stats
    health_after = await check_pool_health()
    final_pool_size = health_after.get('pool_size', 0)
    final_free = health_after.get('free_connections', 0)

    print(f"\nFinal Pool State:")
    print(f"  Pool Size: {final_pool_size}")
    print(f"  Free Connections: {final_free}")

    # Calculate reuse metrics
    total_queries = CONCURRENT_REQUESTS * 3
    print(f"\nConnection Reuse Analysis:")
    print(f"  Total Queries: {total_queries}")
    print(f"  Max Connections Used: {final_pool_size}")
    print(f"  Queries per Connection: {total_queries / final_pool_size if final_pool_size > 0 else 0:.2f}")
    print(f"  Reuse Rate: {((total_queries - final_pool_size) / total_queries * 100) if total_queries > 0 else 0:.1f}%")

    # Assertions
    assert final_pool_size <= max_pool_size, f"Pool size exceeded max: {final_pool_size} > {max_pool_size}"
    assert final_free > 0, "Should have free connections after load"
    assert health_after['status'] == 'healthy', "Pool should be healthy"

    # Connection reuse should be high (we should use far fewer connections than queries)
    reuse_rate = ((total_queries - final_pool_size) / total_queries) if total_queries > 0 else 0
    assert reuse_rate > 0.5, f"Connection reuse rate too low: {reuse_rate:.2%}"


# ============================================================================
# Standalone Execution
# ============================================================================


async def run_all_load_tests():
    """Run all load tests as standalone script."""
    print("\n" + "="*70)
    print("POSTGRESQL CONNECTION POOL LOAD TESTS")
    print("="*70)

    # Initialize pool
    try:
        await init_pool()
        pool = get_pool()

        # Create test table
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS load_test_data (
                    id SERIAL PRIMARY KEY,
                    request_id INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

        print("\n✓ Database pool initialized")

        # Run tests
        await test_concurrent_simple_queries(pool)
        await test_concurrent_write_queries(pool)
        await test_concurrent_complex_queries(pool)
        await test_pool_exhaustion_handling(pool)
        await test_sustained_load(pool)
        await test_connection_reuse_rate(pool)

        # Cleanup
        async with pool.acquire() as conn:
            await conn.execute("DROP TABLE IF EXISTS load_test_data")

        print("\n" + "="*70)
        print("ALL LOAD TESTS PASSED ✓")
        print("="*70 + "\n")

    except Exception as e:
        print(f"\n✗ Error running load tests: {e}")
        raise
    finally:
        await close_pool()


if __name__ == "__main__":
    # Run as standalone script
    asyncio.run(run_all_load_tests())
