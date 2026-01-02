"""Pipeline context for carrying state through stages."""

from typing import Any, Dict, Optional, TypeVar, Generic
from dataclasses import dataclass, field


@dataclass
class ContextKey:
    """Type-safe context key identifier."""

    name: str

    def __str__(self) -> str:
        return self.name


# Common context keys used across stages
USER_QUERY = ContextKey("user_query")
USER_QUERY_ORIGINAL = ContextKey("user_query_original")
STAGE1_RESULTS = ContextKey("stage1_results")
STAGE2_RESULTS = ContextKey("stage2_results")
STAGE3_RESULT = ContextKey("stage3_result")
LABEL_TO_MODEL = ContextKey("label_to_model")
AGGREGATE_RANKINGS = ContextKey("aggregate_rankings")
MARKET_SNAPSHOT = ContextKey("market_snapshot")
EXECUTION_CONSTRAINTS = ContextKey("execution_constraints")
RISK_ASSESSMENT = ContextKey("risk_assessment")
CONVERSATION_ID = ContextKey("conversation_id")
IS_FIRST_MESSAGE = ContextKey("is_first_message")


@dataclass
class PipelineContext:
    """
    Immutable context that flows through pipeline stages.

    Each stage receives a context and produces a new context with
    additional data. Context is never mutated in place.
    """

    _data: Dict[str, Any] = field(default_factory=dict)
    _metadata: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: ContextKey, default: Any = None) -> Any:
        """Get value from context."""
        return self._data.get(str(key), default)

    def set(self, key: ContextKey, value: Any) -> "PipelineContext":
        """
        Return a new context with the key set.
        Context is immutable - this returns a new instance.
        """
        new_data = self._data.copy()
        new_data[str(key)] = value
        return PipelineContext(_data=new_data, _metadata=self._metadata.copy())

    def update(self, **kwargs: Any) -> "PipelineContext":
        """Return a new context with multiple keys set."""
        new_data = self._data.copy()
        for key, value in kwargs.items():
            new_data[key] = value
        return PipelineContext(_data=new_data, _metadata=self._metadata.copy())

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value (for internal pipeline use)."""
        return self._metadata.get(key, default)

    def set_metadata(self, key: str, value: Any) -> "PipelineContext":
        """Return a new context with metadata set."""
        new_metadata = self._metadata.copy()
        new_metadata[key] = value
        return PipelineContext(_data=self._data.copy(), _metadata=new_metadata)

    def has(self, key: ContextKey) -> bool:
        """Check if key exists in context."""
        return str(key) in self._data

    def keys(self) -> list[str]:
        """Get all data keys."""
        return list(self._data.keys())

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dict (for serialization)."""
        return {
            "data": self._data.copy(),
            "metadata": self._metadata.copy(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PipelineContext":
        """Create context from dict."""
        return cls(
            _data=data.get("data", {}),
            _metadata=data.get("metadata", {}),
        )

    def with_conversation_id(self, conversation_id: str) -> "PipelineContext":
        """Set conversation id in context."""
        return self.set(CONVERSATION_ID, conversation_id)

    def with_user_query(self, query: str) -> "PipelineContext":
        """Set user query in context."""
        return self.set(USER_QUERY, query).set(USER_QUERY_ORIGINAL, query)
