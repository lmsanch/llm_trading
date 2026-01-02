"""PostgreSQL event store schema for LLM Trading.

All state changes are stored as immutable events for replay capability.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from sqlalchemy import (
    create_engine,
    Column,
    String,
    DateTime,
    JSON,
    Text,
    Integer,
    Float,
    Index,
    Boolean,
    ForeignKey,
    select,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.types import TypeDecorator, VARCHAR

# ============================================================================
# Base and Database Connection
# ============================================================================

Base = declarative_base()


def get_database_url() -> str:
    """Get database URL from environment."""
    import os
    from dotenv import load_dotenv

    load_dotenv()
    return os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/llm_trading"
    )


def create_engine_with_url(url: Optional[str] = None):
    """Create SQLAlchemy engine with connection pooling."""
    if url is None:
        url = get_database_url()

    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=False,  # Set to True for SQL query logging
    )


def create_tables(engine):
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)


def get_sessionmaker(engine):
    """Return a session factory for the given engine."""
    return sessionmaker(bind=engine)


# ============================================================================
# Enums
# ============================================================================


class EventType(str, Enum):
    """Event types for the system."""

    WEEK_START = "week_start"
    RESEARCH_COMPLETED = "research_completed"
    PM_PITCH = "pm_pitch"
    PEER_REVIEW = "peer_review"
    CHAIRMAN_DECISION = "chairman_decision"
    MARKET_SNAPSHOT = "market_snapshot"
    CHECKPOINT_UPDATE = "checkpoint_update"
    ORDER_PLACED = "order_placed"
    FILL_RECEIVED = "fill_received"
    POSITION_CHANGED = "position_changed"
    WEEK_POSTMORTEM = "week_postmortem"


class Direction(str, Enum):
    """Trade direction."""

    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


# ============================================================================
# Event Tables
# ============================================================================


class Event(Base):
    """Base event table - all events inherit from this conceptually.

    This is the primary table for event sourcing. Each row represents
    an immutable event in the system.
    """

    __tablename__ = "events"

    # Primary key - composite of event_type + id
    id = Column(String, primary_key=True)  # Format: "{event_type}_{uuid}"

    # Event type for filtering
    event_type = Column(String(50), nullable=False, index=True)

    # Week identifier (Wednesday date)
    week_id = Column(String(10), nullable=False, index=True)  # Format: "YYYY-MM-DD"

    # Account identifier (for paper trading accounts)
    account_id = Column(String(50), nullable=True, index=True)

    # Timestamp (always UTC)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Event payload (JSON blob)
    payload = Column(JSON, nullable=False)

    # Optional: link to parent event (for causality)
    parent_event_id = Column(String, ForeignKey("events.id"), nullable=True)

    # Optional: human-readable summary
    summary = Column(Text, nullable=True)


class ResearchPackEvent(Base):
    """Research pack from Gemini or Perplexity deep research.

    One event per research pack per provider per week.
    """

    __tablename__ = "research_packs"

    id = Column(String, primary_key=True)  # Format: "research_{uuid}"

    week_id = Column(String(10), nullable=False, index=True)

    # Research provider name
    provider = Column(String(50), nullable=False)  # "gemini_deep" or "perplexity_deep"

    # Full research pack (from WEEKLY_RESEARCH.MD schema)
    research_data = Column(JSON, nullable=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Metadata
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)


class PMPitchEvent(Base):
    """PM pitch from one of the council models.

    One event per PM model per week.
    """

    __tablename__ = "pm_pitches"

    id = Column(String, primary_key=True)  # Format: "pitch_{uuid}"

    week_id = Column(String(10), nullable=False, index=True)

    # PM model identifier
    model = Column(String(100), nullable=False)

    # Pitch data (from PRD.md PM Pitch JSON schema)
    pitch_data = Column(JSON, nullable=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Validation status
    validation_status = Column(
        String(20), default="pending"
    )  # "pending", "valid", "invalid"
    validation_errors = Column(JSON, nullable=True)

    # Research pack IDs used (for traceability)
    research_pack_a_id = Column(String, nullable=True)
    research_pack_b_id = Column(String, nullable=True)


class PeerReviewEvent(Base):
    """Peer review of a PM pitch by another model.

    One event per reviewer-pitch pair.
    """

    __tablename__ = "peer_reviews"

    id = Column(String, primary_key=True)  # Format: "review_{uuid}"

    week_id = Column(String(10), nullable=False, index=True)

    # Reviewer model
    reviewer_model = Column(String(100), nullable=False)

    # Pitch being reviewed (anonymized label during review process)
    pitch_id = Column(String, nullable=False)
    anonymized_pitch_label = Column(
        String(20), nullable=True
    )  # "Pitch A", "Pitch B", etc.

    # Review data (from PRD.md Peer Review JSON schema)
    review_data = Column(JSON, nullable=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ChairmanDecisionEvent(Base):
    """Final chairman (CIO) decision for the week.

    One event per week (for council account).
    """

    __tablename__ = "chairman_decisions"

    id = Column(String, primary_key=True)  # Format: "decision_{uuid}"

    week_id = Column(String(10), nullable=False, unique=True, index=True)

    # Chairman model
    model = Column(String(100), nullable=False)

    # Decision data (from PRD.md Chairman Decision JSON schema)
    decision_data = Column(JSON, nullable=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class CheckpointUpdateEvent(Base):
    """Daily checkpoint conviction update.

    One event per account per checkpoint time per day.
    """

    __tablename__ = "checkpoint_updates"

    id = Column(String, primary_key=True)  # Format: "checkpoint_{uuid}"

    week_id = Column(String(10), nullable=False, index=True)

    account_id = Column(String(50), nullable=False, index=True)

    # Checkpoint time (e.g., "09:00", "12:00", etc.)
    checkpoint_time = Column(String(5), nullable=False)  # Format: "HH:MM"

    # Checkpoint data (from PRD.md Checkpoint JSON schema)
    checkpoint_data = Column(JSON, nullable=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class OrderEvent(Base):
    """Order placed event.

    One event per order attempt.
    """

    __tablename__ = "orders"

    id = Column(String, primary_key=True)  # Use Alpaca order ID if available

    week_id = Column(String(10), nullable=False, index=True)

    account_id = Column(String(50), nullable=False, index=True)

    # Order details
    order_id = Column(String(100), nullable=True)  # Alpaca order ID
    symbol = Column(String(10), nullable=False)  # e.g., "SPY"
    side = Column(String(10), nullable=False)  # "buy" or "sell"
    qty = Column(Float, nullable=False)
    order_type = Column(String(20), nullable=False)  # "market", "limit", etc.
    limit_price = Column(Float, nullable=True)

    # Order status
    status = Column(
        String(20), nullable=False
    )  # "pending", "filled", "cancelled", "rejected"

    # Links to decision (why this order was placed)
    decision_id = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class PositionEvent(Base):
    """Position change event.

    One event per position snapshot.
    """

    __tablename__ = "positions"

    id = Column(String, primary_key=True)  # Format: "pos_{account}_{symbol}_{week_id}"

    week_id = Column(String(10), nullable=False, index=True)

    account_id = Column(String(50), nullable=False, index=True)

    # Position details
    symbol = Column(String(10), nullable=False)  # e.g., "SPY"
    qty = Column(Float, nullable=False)
    avg_entry_price = Column(Float, nullable=True)
    current_price = Column(Float, nullable=True)

    # P/L calculations
    unrealized_pl = Column(Float, nullable=True)
    unrealized_pl_pct = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class WeeklyPostmortemEvent(Base):
    """End-of-week postmortem analysis.

    One event per week.
    """

    __tablename__ = "weekly_postmortems"

    id = Column(String, primary_key=True)  # Format: "postmortem_{week_id}"

    week_id = Column(String(10), nullable=False, unique=True, index=True)

    # Postmortem data
    postmortem_data = Column(JSON, nullable=False)

    # Summary metrics
    total_return_pct = Column(Float, nullable=True)
    max_drawdown_pct = Column(Float, nullable=True)
    turnover = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class WeekMetadata(Base):
    """Week-level metadata for quick lookups.

    This is a denormalized table for faster queries.
    """

    __tablename__ = "week_metadata"

    week_id = Column(String(10), primary_key=True)  # Format: "YYYY-MM-DD"

    # Week state
    state = Column(String(20), nullable=False)  # "started", "completed", "postmortem"

    # Timestamps
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    postmortem_at = Column(DateTime, nullable=True)

    # Account states
    council_account_status = Column(
        String(20), nullable=True
    )  # "long", "short", "flat"

    # Summary metrics
    total_orders = Column(Integer, default=0)
    total_checkpoints = Column(Integer, default=0)


# ============================================================================
# Indexes
# ============================================================================

# Note: Indexes are defined on columns above using index=True parameter
# Additional composite indexes can be added via __table_args__ if needed
