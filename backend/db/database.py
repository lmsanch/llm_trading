"""Database connection utilities for PostgreSQL."""

import os
import psycopg2
from typing import Optional


def get_connection():
    """
    Create a PostgreSQL database connection.

    Returns:
        psycopg2 connection object

    Raises:
        psycopg2.Error: If connection fails

    Environment Variables:
        DATABASE_NAME: Name of the database (default: llm_trading)
        DATABASE_USER: Database user (default: luis)
    """
    db_name = os.getenv("DATABASE_NAME", "llm_trading")
    db_user = os.getenv("DATABASE_USER", "luis")

    return psycopg2.connect(dbname=db_name, user=db_user)


class DatabaseConnection:
    """
    Context manager for safe database connection handling.

    Automatically commits on success and rolls back on error.
    Always closes the connection when done.

    Usage:
        with DatabaseConnection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM table")
                results = cur.fetchall()

    Environment Variables:
        DATABASE_NAME: Name of the database (default: llm_trading)
        DATABASE_USER: Database user (default: luis)
    """

    def __init__(self):
        """Initialize the context manager."""
        self.conn: Optional[psycopg2.extensions.connection] = None

    def __enter__(self):
        """
        Enter the context and create database connection.

        Returns:
            psycopg2 connection object
        """
        db_name = os.getenv("DATABASE_NAME", "llm_trading")
        db_user = os.getenv("DATABASE_USER", "luis")

        self.conn = psycopg2.connect(dbname=db_name, user=db_user)
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context and clean up connection.

        Commits transaction on success, rolls back on error.
        Always closes the connection.

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred

        Returns:
            False to propagate exceptions
        """
        if self.conn is not None:
            try:
                if exc_type is None:
                    # No exception, commit the transaction
                    self.conn.commit()
                else:
                    # Exception occurred, rollback
                    self.conn.rollback()
            finally:
                # Always close the connection
                self.conn.close()

        # Return False to propagate exceptions
        return False
