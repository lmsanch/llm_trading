#!/usr/bin/env python3
"""Simple tests for query builder functionality.

This script tests the query builders without requiring a database connection.
It validates the generated SQL and parameter tuples.
"""

from backend.db.query_builders import (
    SelectQuery,
    build_upsert,
    build_batch_upsert,
    build_latest_by_date,
    build_date_range_query,
    build_count_query,
    validate_identifier,
)


def test_select_query_basic():
    """Test basic SELECT query building."""
    print("=" * 60)
    print("Test: Basic SELECT query")
    print("=" * 60)

    query, params = (SelectQuery("users")
        .columns("id", "name", "email")
        .where("active = $1", True)
        .where("role = $1", "admin")
        .order_by("created_at DESC")
        .limit(10)
        .build())

    print(f"Query: {query}")
    print(f"Params: {params}")

    expected = "SELECT id, name, email FROM users WHERE (active = $1) AND (role = $2) ORDER BY created_at DESC LIMIT 10"
    assert query == expected, f"Expected: {expected}\nGot: {query}"
    assert params == (True, "admin"), f"Expected: (True, 'admin')\nGot: {params}"
    print("✓ PASSED\n")


def test_select_query_simple():
    """Test simple SELECT with defaults."""
    print("=" * 60)
    print("Test: Simple SELECT query")
    print("=" * 60)

    query, params = SelectQuery("daily_bars").build()

    print(f"Query: {query}")
    print(f"Params: {params}")

    expected = "SELECT * FROM daily_bars"
    assert query == expected, f"Expected: {expected}\nGot: {query}"
    assert params == (), f"Expected: ()\nGot: {params}"
    print("✓ PASSED\n")


def test_select_query_distinct():
    """Test SELECT DISTINCT."""
    print("=" * 60)
    print("Test: SELECT DISTINCT")
    print("=" * 60)

    query, params = (SelectQuery("daily_bars")
        .columns("symbol")
        .distinct()
        .order_by("symbol ASC")
        .build())

    print(f"Query: {query}")
    print(f"Params: {params}")

    expected = "SELECT DISTINCT symbol FROM daily_bars ORDER BY symbol ASC"
    assert query == expected, f"Expected: {expected}\nGot: {query}"
    print("✓ PASSED\n")


def test_upsert():
    """Test UPSERT query building."""
    print("=" * 60)
    print("Test: UPSERT query")
    print("=" * 60)

    query, params = build_upsert(
        table="daily_bars",
        conflict_columns=["symbol", "date"],
        data={"symbol": "SPY", "date": "2025-01-20", "close": 550.25, "volume": 100000},
        update_columns=["close", "volume"]
    )

    print(f"Query: {query}")
    print(f"Params: {params}")

    assert "INSERT INTO daily_bars" in query
    assert "ON CONFLICT (symbol, date) DO UPDATE SET" in query
    assert "close = EXCLUDED.close" in query
    assert "volume = EXCLUDED.volume" in query
    assert params == ("SPY", "2025-01-20", 550.25, 100000)
    print("✓ PASSED\n")


def test_batch_upsert():
    """Test batch UPSERT query building."""
    print("=" * 60)
    print("Test: Batch UPSERT")
    print("=" * 60)

    query, args_list = build_batch_upsert(
        table="daily_bars",
        conflict_columns=["symbol", "date"],
        rows=[
            {"symbol": "SPY", "date": "2025-01-20", "close": 550.25, "volume": 100000},
            {"symbol": "QQQ", "date": "2025-01-20", "close": 450.10, "volume": 80000}
        ],
        update_columns=["close", "volume"]
    )

    print(f"Query: {query}")
    print(f"Args list:")
    for i, args in enumerate(args_list):
        print(f"  [{i}]: {args}")

    assert "INSERT INTO daily_bars" in query
    assert "ON CONFLICT (symbol, date) DO UPDATE SET" in query
    assert len(args_list) == 2
    assert args_list[0] == ("SPY", "2025-01-20", 550.25, 100000)
    assert args_list[1] == ("QQQ", "2025-01-20", 450.10, 80000)
    print("✓ PASSED\n")


def test_latest_by_date():
    """Test latest by date query."""
    print("=" * 60)
    print("Test: Latest by date")
    print("=" * 60)

    # With symbol filter
    query, params = build_latest_by_date("daily_bars", symbol_value="SPY")
    print(f"Query (with symbol): {query}")
    print(f"Params: {params}")
    assert query == "SELECT MAX(date) FROM daily_bars WHERE symbol = $1"
    assert params == ("SPY",)

    # Without symbol filter
    query, params = build_latest_by_date("daily_bars")
    print(f"Query (no symbol): {query}")
    print(f"Params: {params}")
    assert query == "SELECT MAX(date) FROM daily_bars"
    assert params == ()

    print("✓ PASSED\n")


def test_date_range_query():
    """Test date range query."""
    print("=" * 60)
    print("Test: Date range query")
    print("=" * 60)

    query, params = build_date_range_query(
        table="daily_bars",
        start_date="2025-01-01",
        end_date="2025-01-31",
        symbol="SPY"
    )

    print(f"Query: {query}")
    print(f"Params: {params}")

    assert "SELECT * FROM daily_bars WHERE date >= $1 AND date <= $2 AND symbol = $3" in query
    assert "ORDER BY date ASC" in query
    assert params == ("2025-01-01", "2025-01-31", "SPY")
    print("✓ PASSED\n")


def test_count_query():
    """Test count query."""
    print("=" * 60)
    print("Test: Count query")
    print("=" * 60)

    # Simple count
    query, params = build_count_query("daily_bars")
    print(f"Query (simple): {query}")
    print(f"Params: {params}")
    assert query == "SELECT COUNT(*) FROM daily_bars"
    assert params == ()

    # Count with WHERE
    query, params = build_count_query(
        "daily_bars",
        where_clause="symbol = $1",
        params=("SPY",)
    )
    print(f"Query (with WHERE): {query}")
    print(f"Params: {params}")
    assert query == "SELECT COUNT(*) FROM daily_bars WHERE symbol = $1"
    assert params == ("SPY",)

    print("✓ PASSED\n")


def test_validate_identifier():
    """Test identifier validation."""
    print("=" * 60)
    print("Test: Identifier validation")
    print("=" * 60)

    # Valid identifiers
    valid = ["users", "daily_bars", "my_table_123", "_private"]
    for identifier in valid:
        assert validate_identifier(identifier), f"Expected '{identifier}' to be valid"
        print(f"✓ Valid: {identifier}")

    # Invalid identifiers
    invalid = ["", "123invalid", "table-name", "table name", "a" * 64]
    for identifier in invalid:
        assert not validate_identifier(identifier), f"Expected '{identifier}' to be invalid"
        print(f"✗ Invalid: {identifier}")

    print("✓ PASSED\n")


def test_select_offset():
    """Test SELECT with OFFSET."""
    print("=" * 60)
    print("Test: SELECT with OFFSET")
    print("=" * 60)

    query, params = (SelectQuery("users")
        .columns("id", "name")
        .order_by("id ASC")
        .limit(10)
        .offset(20)
        .build())

    print(f"Query: {query}")
    print(f"Params: {params}")

    expected = "SELECT id, name FROM users ORDER BY id ASC LIMIT 10 OFFSET 20"
    assert query == expected, f"Expected: {expected}\nGot: {query}"
    print("✓ PASSED\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("QUERY BUILDER TESTS")
    print("=" * 60 + "\n")

    tests = [
        test_select_query_basic,
        test_select_query_simple,
        test_select_query_distinct,
        test_upsert,
        test_batch_upsert,
        test_latest_by_date,
        test_date_range_query,
        test_count_query,
        test_validate_identifier,
        test_select_offset,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ FAILED: {e}\n")
            failed += 1
        except Exception as e:
            print(f"✗ ERROR: {e}\n")
            failed += 1

    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())
