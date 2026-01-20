"""Serialization utilities for Redis caching.

This module provides utilities for serializing and deserializing Python objects
to/from Redis-compatible formats (JSON and msgpack). It handles special types
like datetime, Decimal, and UUID, and supports compression for large payloads.

Supported Formats:
    - JSON: Human-readable, good for debugging
    - msgpack: Binary format, more efficient for storage and network

Special Type Handling:
    - datetime/date/time: Converted to ISO format strings
    - Decimal: Converted to float
    - UUID: Converted to string
    - bytes: Base64 encoded (JSON) or passed through (msgpack)
    - set: Converted to list

Compression:
    - Automatic compression for payloads larger than threshold
    - Uses gzip compression (level 6 by default)
    - Adds 'compressed' flag to metadata

Usage:
    from backend.cache.serializer import serialize, deserialize

    # Serialize data to JSON
    data = {"timestamp": datetime.now(), "value": Decimal("123.45")}
    serialized = serialize(data, format="json")

    # Deserialize back
    original = deserialize(serialized, format="json")

    # Use msgpack for efficiency
    serialized = serialize(data, format="msgpack")
    original = deserialize(serialized, format="msgpack")

    # Automatic compression for large payloads
    large_data = {"bars": [...]}  # Large dataset
    serialized = serialize(large_data, format="msgpack", compress=True)
"""

import json
import logging
import gzip
import base64
from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID
from typing import Any, Optional, Union
from enum import Enum

logger = logging.getLogger(__name__)

# Try to import msgpack (optional dependency)
try:
    import msgpack
    HAS_MSGPACK = True
except ImportError:
    HAS_MSGPACK = False
    logger.warning("msgpack not available - using JSON serialization only")


# Serialization format enum
class SerializationFormat(str, Enum):
    """Supported serialization formats."""
    JSON = "json"
    MSGPACK = "msgpack"


# Compression configuration
DEFAULT_COMPRESSION_LEVEL = 6  # gzip compression level (0-9)
DEFAULT_COMPRESSION_THRESHOLD = 1024  # Compress if larger than 1KB


# ============================================================================
# JSON Serialization
# ============================================================================


def _json_default(obj: Any) -> Any:
    """
    Custom JSON encoder for special types.

    Handles datetime, Decimal, UUID, bytes, and set objects.

    Args:
        obj: Object to encode

    Returns:
        JSON-serializable representation

    Raises:
        TypeError: If object type is not supported
    """
    # Handle datetime objects
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()

    # Handle Decimal
    if isinstance(obj, Decimal):
        return float(obj)

    # Handle UUID
    if isinstance(obj, UUID):
        return str(obj)

    # Handle bytes
    if isinstance(obj, bytes):
        return base64.b64encode(obj).decode("utf-8")

    # Handle sets
    if isinstance(obj, set):
        return list(obj)

    # Unknown type
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def serialize_json(data: Any) -> str:
    """
    Serialize data to JSON string.

    Args:
        data: Python object to serialize

    Returns:
        JSON string

    Raises:
        ValueError: If serialization fails

    Example:
        >>> data = {"timestamp": datetime.now(), "value": Decimal("123.45")}
        >>> json_str = serialize_json(data)
        >>> isinstance(json_str, str)
        True
    """
    try:
        return json.dumps(data, default=_json_default, separators=(',', ':'))
    except Exception as e:
        logger.error(f"JSON serialization failed: {e}", exc_info=True)
        raise ValueError(f"Failed to serialize to JSON: {e}")


def deserialize_json(data: Union[str, bytes]) -> Any:
    """
    Deserialize data from JSON string.

    Args:
        data: JSON string or bytes

    Returns:
        Deserialized Python object

    Raises:
        ValueError: If deserialization fails

    Example:
        >>> json_str = '{"key":"value","count":42}'
        >>> obj = deserialize_json(json_str)
        >>> obj["key"]
        'value'
    """
    try:
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return json.loads(data)
    except Exception as e:
        logger.error(f"JSON deserialization failed: {e}", exc_info=True)
        raise ValueError(f"Failed to deserialize from JSON: {e}")


# ============================================================================
# msgpack Serialization
# ============================================================================


def _msgpack_default(obj: Any) -> Any:
    """
    Custom msgpack encoder for special types.

    Handles datetime, Decimal, UUID, and set objects.

    Args:
        obj: Object to encode

    Returns:
        msgpack-serializable representation

    Raises:
        TypeError: If object type is not supported
    """
    # Handle datetime objects
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()

    # Handle Decimal
    if isinstance(obj, Decimal):
        return float(obj)

    # Handle UUID
    if isinstance(obj, UUID):
        return str(obj)

    # Handle sets
    if isinstance(obj, set):
        return list(obj)

    # Unknown type
    raise TypeError(f"Object of type {type(obj).__name__} is not msgpack serializable")


def serialize_msgpack(data: Any) -> bytes:
    """
    Serialize data to msgpack binary format.

    Args:
        data: Python object to serialize

    Returns:
        msgpack bytes

    Raises:
        ValueError: If serialization fails or msgpack not available

    Example:
        >>> data = {"timestamp": datetime.now(), "value": Decimal("123.45")}
        >>> binary = serialize_msgpack(data)
        >>> isinstance(binary, bytes)
        True
    """
    if not HAS_MSGPACK:
        raise ValueError("msgpack is not available - install with 'pip install msgpack'")

    try:
        return msgpack.packb(data, default=_msgpack_default, use_bin_type=True)
    except Exception as e:
        logger.error(f"msgpack serialization failed: {e}", exc_info=True)
        raise ValueError(f"Failed to serialize to msgpack: {e}")


def deserialize_msgpack(data: bytes) -> Any:
    """
    Deserialize data from msgpack binary format.

    Args:
        data: msgpack bytes

    Returns:
        Deserialized Python object

    Raises:
        ValueError: If deserialization fails or msgpack not available

    Example:
        >>> binary = b'\x82\xa3key\xa5value\xa5count*'
        >>> obj = deserialize_msgpack(binary)
        >>> isinstance(obj, dict)
        True
    """
    if not HAS_MSGPACK:
        raise ValueError("msgpack is not available - install with 'pip install msgpack'")

    try:
        return msgpack.unpackb(data, raw=False)
    except Exception as e:
        logger.error(f"msgpack deserialization failed: {e}", exc_info=True)
        raise ValueError(f"Failed to deserialize from msgpack: {e}")


# ============================================================================
# Compression
# ============================================================================


def compress_data(data: bytes, level: int = DEFAULT_COMPRESSION_LEVEL) -> bytes:
    """
    Compress data using gzip.

    Args:
        data: Bytes to compress
        level: Compression level (0-9, higher = better compression but slower)

    Returns:
        Compressed bytes

    Raises:
        ValueError: If compression fails

    Example:
        >>> data = b"x" * 10000
        >>> compressed = compress_data(data)
        >>> len(compressed) < len(data)
        True
    """
    try:
        return gzip.compress(data, compresslevel=level)
    except Exception as e:
        logger.error(f"Compression failed: {e}", exc_info=True)
        raise ValueError(f"Failed to compress data: {e}")


def decompress_data(data: bytes) -> bytes:
    """
    Decompress gzip-compressed data.

    Args:
        data: Compressed bytes

    Returns:
        Decompressed bytes

    Raises:
        ValueError: If decompression fails

    Example:
        >>> compressed = gzip.compress(b"test data")
        >>> decompressed = decompress_data(compressed)
        >>> decompressed
        b'test data'
    """
    try:
        return gzip.decompress(data)
    except Exception as e:
        logger.error(f"Decompression failed: {e}", exc_info=True)
        raise ValueError(f"Failed to decompress data: {e}")


# ============================================================================
# High-Level Serialization API
# ============================================================================


def serialize(
    data: Any,
    format: str = "json",
    compress: bool = False,
    compression_threshold: int = DEFAULT_COMPRESSION_THRESHOLD,
    compression_level: int = DEFAULT_COMPRESSION_LEVEL,
) -> Union[str, bytes]:
    """
    Serialize data to Redis-compatible format.

    This is the main entry point for serialization. It handles:
    - Format selection (JSON or msgpack)
    - Special type conversion (datetime, Decimal, UUID)
    - Optional compression for large payloads

    Args:
        data: Python object to serialize
        format: Serialization format ("json" or "msgpack")
        compress: Whether to compress the data
        compression_threshold: Compress if size exceeds this (bytes)
        compression_level: gzip compression level (0-9)

    Returns:
        Serialized data (str for JSON, bytes for msgpack)
        If compressed, always returns bytes

    Raises:
        ValueError: If serialization fails or format is invalid

    Examples:
        >>> # Simple JSON serialization
        >>> data = {"key": "value", "count": 42}
        >>> serialize(data, format="json")
        '{"key":"value","count":42}'

        >>> # msgpack serialization
        >>> serialize(data, format="msgpack")
        b'\\x82\\xa3key\\xa5value\\xa5count*'

        >>> # Automatic compression
        >>> large_data = {"bars": [{"price": i} for i in range(1000)]}
        >>> serialized = serialize(large_data, format="msgpack", compress=True)
        >>> isinstance(serialized, bytes)
        True

        >>> # Handle special types
        >>> data = {"timestamp": datetime.now(), "price": Decimal("123.45")}
        >>> serialized = serialize(data, format="json")
        >>> "timestamp" in serialized
        True
    """
    # Validate format
    format = format.lower()
    if format not in [SerializationFormat.JSON, SerializationFormat.MSGPACK]:
        raise ValueError(f"Invalid format: {format}. Use 'json' or 'msgpack'")

    # Serialize based on format
    try:
        if format == SerializationFormat.JSON:
            serialized = serialize_json(data)
            serialized_bytes = serialized.encode("utf-8")
        else:
            serialized_bytes = serialize_msgpack(data)
            serialized = serialized_bytes

        # Check if compression is needed
        should_compress = compress and len(serialized_bytes) > compression_threshold

        if should_compress:
            logger.debug(
                f"Compressing data: {len(serialized_bytes)} bytes "
                f"(threshold={compression_threshold})"
            )
            compressed = compress_data(serialized_bytes, level=compression_level)
            logger.debug(
                f"Compressed: {len(serialized_bytes)} -> {len(compressed)} bytes "
                f"({100 * len(compressed) / len(serialized_bytes):.1f}%)"
            )
            return compressed

        return serialized

    except Exception as e:
        logger.error(f"Serialization failed: {e}", exc_info=True)
        raise ValueError(f"Failed to serialize data: {e}")


def deserialize(
    data: Union[str, bytes],
    format: str = "json",
    compressed: bool = False,
) -> Any:
    """
    Deserialize data from Redis-compatible format.

    This is the main entry point for deserialization. It handles:
    - Format detection and parsing (JSON or msgpack)
    - Optional decompression
    - Error handling and logging

    Args:
        data: Serialized data (str for JSON, bytes for msgpack)
        format: Serialization format ("json" or "msgpack")
        compressed: Whether the data is compressed

    Returns:
        Deserialized Python object

    Raises:
        ValueError: If deserialization fails or format is invalid

    Examples:
        >>> # Simple JSON deserialization
        >>> json_str = '{"key":"value","count":42}'
        >>> obj = deserialize(json_str, format="json")
        >>> obj["key"]
        'value'

        >>> # msgpack deserialization
        >>> binary = b'\\x82\\xa3key\\xa5value\\xa5count*'
        >>> obj = deserialize(binary, format="msgpack")
        >>> isinstance(obj, dict)
        True

        >>> # Automatic decompression
        >>> data = {"bars": [{"price": i} for i in range(1000)]}
        >>> serialized = serialize(data, format="msgpack", compress=True)
        >>> deserialized = deserialize(serialized, format="msgpack", compressed=True)
        >>> len(deserialized["bars"])
        1000
    """
    # Validate format
    format = format.lower()
    if format not in [SerializationFormat.JSON, SerializationFormat.MSGPACK]:
        raise ValueError(f"Invalid format: {format}. Use 'json' or 'msgpack'")

    try:
        # Decompress if needed
        if compressed:
            if isinstance(data, str):
                data = data.encode("utf-8")
            logger.debug(f"Decompressing data: {len(data)} bytes")
            data = decompress_data(data)
            logger.debug(f"Decompressed to: {len(data)} bytes")

        # Deserialize based on format
        if format == SerializationFormat.JSON:
            return deserialize_json(data)
        else:
            return deserialize_msgpack(data)

    except Exception as e:
        logger.error(f"Deserialization failed: {e}", exc_info=True)
        raise ValueError(f"Failed to deserialize data: {e}")


# ============================================================================
# Utility Functions
# ============================================================================


def estimate_size(data: Any, format: str = "json") -> int:
    """
    Estimate serialized size of data without actually serializing.

    This is useful for deciding whether to compress data before caching.

    Args:
        data: Python object
        format: Serialization format ("json" or "msgpack")

    Returns:
        Estimated size in bytes

    Example:
        >>> data = {"bars": [{"price": i} for i in range(1000)]}
        >>> size = estimate_size(data, format="json")
        >>> size > 1000
        True
    """
    try:
        serialized = serialize(data, format=format, compress=False)
        if isinstance(serialized, str):
            return len(serialized.encode("utf-8"))
        return len(serialized)
    except Exception as e:
        logger.warning(f"Failed to estimate size: {e}")
        return 0


def should_compress(
    data: Any,
    format: str = "json",
    threshold: int = DEFAULT_COMPRESSION_THRESHOLD,
) -> bool:
    """
    Determine if data should be compressed based on size threshold.

    Args:
        data: Python object
        format: Serialization format ("json" or "msgpack")
        threshold: Compression threshold in bytes

    Returns:
        True if data should be compressed, False otherwise

    Example:
        >>> small_data = {"key": "value"}
        >>> should_compress(small_data)
        False

        >>> large_data = {"bars": [{"price": i} for i in range(1000)]}
        >>> should_compress(large_data)
        True
    """
    size = estimate_size(data, format=format)
    return size > threshold


def get_compression_ratio(original: bytes, compressed: bytes) -> float:
    """
    Calculate compression ratio.

    Args:
        original: Original data bytes
        compressed: Compressed data bytes

    Returns:
        Compression ratio (e.g., 0.5 = 50% of original size)

    Example:
        >>> original = b"x" * 10000
        >>> compressed = compress_data(original)
        >>> ratio = get_compression_ratio(original, compressed)
        >>> ratio < 0.01  # gzip compresses repetitive data very well
        True
    """
    if len(original) == 0:
        return 0.0
    return len(compressed) / len(original)
