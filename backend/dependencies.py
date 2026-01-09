"""FastAPI dependency injection utilities.

This module provides dependency functions for FastAPI route handlers.
These dependencies handle resource management and provide access to
global state and database connections.
"""

import logging
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
import psycopg2

logger = logging.getLogger(__name__)


def get_pipeline_state():
    """
    FastAPI dependency for accessing the global pipeline state.

    This dependency provides access to the shared pipeline state object
    that tracks the current status of research, pitches, council decisions,
    and trade execution across the application.

    Returns:
        PipelineState object from backend.main

    Raises:
        HTTPException: 503 Service Unavailable if pipeline state cannot be accessed

    Example:
        @router.get("/api/research/current")
        async def get_research(state = Depends(get_pipeline_state)):
            return state.research_packs

    Notes:
        - This dependency imports from backend.main to access the global pipeline_state
        - The pipeline state is a singleton shared across all requests
        - No cleanup or context management is needed since it's a global object
    """
    try:
        from backend.main import pipeline_state

        if pipeline_state is None:
            logger.error("Pipeline state is None")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Pipeline state not initialized",
            )

        return pipeline_state

    except ImportError as e:
        logger.error(f"Could not import pipeline_state from backend.main: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pipeline state not available",
        )


def get_db_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    FastAPI dependency for database connections with automatic cleanup.

    This dependency provides a PostgreSQL database connection that is
    automatically committed on success, rolled back on error, and closed
    when the request completes.

    Yields:
        psycopg2 connection object

    Raises:
        HTTPException: 503 Service Unavailable if database connection fails

    Example:
        @router.get("/api/data")
        async def get_data(conn = Depends(get_db_connection)):
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM table")
                return cur.fetchall()

    Notes:
        - Connection is automatically committed if no exception occurs
        - Connection is automatically rolled back if an exception occurs
        - Connection is always closed when the request completes
        - Uses environment variables DATABASE_NAME and DATABASE_USER
        - This is an alternative to using DatabaseConnection context manager directly
    """
    from backend.db.database import get_connection

    conn = None
    try:
        # Create database connection
        conn = get_connection()
        yield conn

        # Commit on success
        conn.commit()

    except psycopg2.Error as e:
        logger.error(f"Database error: {e}", exc_info=True)
        if conn is not None:
            conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed",
        )

    except Exception as e:
        logger.error(f"Unexpected error in database connection: {e}", exc_info=True)
        if conn is not None:
            conn.rollback()
        raise

    finally:
        # Always close connection
        if conn is not None:
            conn.close()


# Optional dependencies for specific use cases

def get_pipeline_state_optional():
    """
    FastAPI dependency for optional pipeline state access.

    This is similar to get_pipeline_state() but returns None instead of
    raising an exception if the pipeline state is not available. Useful
    for endpoints that can function with mock data or degraded functionality.

    Returns:
        PipelineState object or None if not available

    Example:
        @router.get("/api/research/current")
        async def get_research(state = Depends(get_pipeline_state_optional)):
            if state and state.research_packs:
                return state.research_packs
            return MOCK_RESEARCH_PACKS  # fallback to mock data

    Notes:
        - Does not raise exceptions, returns None on failure
        - Logs warnings but doesn't break the request
        - Useful for endpoints that have fallback data sources
    """
    try:
        from backend.main import pipeline_state

        return pipeline_state

    except ImportError:
        logger.warning("Could not import pipeline_state from backend.main")
        return None
