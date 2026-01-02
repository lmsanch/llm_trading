# Pipeline-First Architecture

This document describes the pipeline-first architecture for LLM Trading, extending Karpathy's `llm-council` pattern into a composable, headless system.

---

## Design Principles

### 1. Composable Stages

Each stage is an independent component with:
- **Clear input/output contract** - typed input → typed output
- **Async execution** - all stages are async by default
- **Isolation** - stages don't depend on each other's internals
- **Reusability** - stages can be rearranged, added, or removed

### 2. Immutable Context

- `PipelineContext` carries state through stages
- Context is **never mutated** - each stage returns a new context
- Type-safe keys via `ContextKey` class

### 3. Event Sourcing

- All state changes are immutable events
- Stored in SQLite with per-week sharding
- Full replay capability for debugging and analysis

---

## Core Classes

### PipelineContext

```python
@dataclass
class PipelineContext:
    """Immutable context flowing through pipeline stages."""
    _data: Dict[str, Any]
    _metadata: Dict[str, Any]

    def get(self, key: ContextKey, default: Any = None) -> Any
    def set(self, key: ContextKey, value: Any) -> "PipelineContext"
    def update(self, **kwargs: Any) -> "PipelineContext"
    def has(self, key: ContextKey) -> bool
```

### ContextKey

```python
@dataclass
class ContextKey:
    """Type-safe context key identifier."""
    name: str
```

### Stage

```python
class Stage(ABC):
    """Base class for all pipeline stages."""

    @abstractmethod
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute stage logic, return new context."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Stage name for logging."""
        pass
```

### Pipeline

```python
class Pipeline:
    """Chain of stages with async execution."""

    def __init__(self, stages: List[Stage]):
        self.stages = stages

    async def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute all stages sequentially."""
        for stage in self.stages:
            context = await stage.execute(context)
        return context

    def with_stage(self, stage: Stage) -> "Pipeline":
        """Return new pipeline with stage appended."""
        return Pipeline(self.stages + [stage])
```

---

## Standard Context Keys

```python
# Input keys
USER_QUERY = ContextKey("user_query")
USER_QUERY_ORIGINAL = ContextKey("user_query_original")
CONVERSATION_ID = ContextKey("conversation_id")
IS_FIRST_MESSAGE = ContextKey("is_first_message")

# Stage outputs
STAGE1_RESULTS = ContextKey("stage1_results")
STAGE2_RESULTS = ContextKey("stage2_results")
STAGE3_RESULT = ContextKey("stage3_result")

# Trading-specific keys
MARKET_SNAPSHOT = ContextKey("market_snapshot")
EXECUTION_CONSTRAINTS = ContextKey("execution_constraints")
RISK_ASSESSMENT = ContextKey("risk_assessment")
RESEARCH_PACK_A = ContextKey("research_pack_a")
RESEARCH_PACK_B = ContextKey("research_pack_b")
PM_PITCHES = ContextKey("pm_pitches")
PEER_REVIEWS = ContextKey("peer_reviews")
CHAIRMAN_DECISION = ContextKey("chairman_decision")

# Derived data
LABEL_TO_MODEL = ContextKey("label_to_model")
AGGREGATE_RANKINGS = ContextKey("aggregate_rankings")
```

---

## Stage Catalog

### Research Layer

| Stage | Input | Output | Description |
|-------|-------|--------|-------------|
| `GeminiResearchStage` | `USER_QUERY` | `RESEARCH_PACK_A` | Query Gemini Deep Research |
| `PerplexityResearchStage` | `USER_QUERY` | `RESEARCH_PACK_B` | Query Perplexity Deep Research |

### PM Layer

| Stage | Input | Output | Description |
|-------|-------|--------|-------------|
| `PMPitchStage` | `RESEARCH_PACK_A`, `RESEARCH_PACK_B` | `PM_PITCHES` | Generate pitches from all PM models |
| `CollectResponsesStage` | `USER_QUERY` | `STAGE1_RESULTS` | Ported from llm-council stage1 |

### Peer Review Layer

| Stage | Input | Output | Description |
|-------|-------|--------|-------------|
| `PeerReviewStage` | `PM_PITCHES` | `PEER_REVIEWS`, `LABEL_TO_MODEL` | Anonymized cross-evaluation |
| `CollectRankingsStage` | `USER_QUERY`, `STAGE1_RESULTS` | `STAGE2_RESULTS` | Ported from llm-council stage2 |

### Chairman Layer

| Stage | Input | Output | Description |
|-------|-------|--------|-------------|
| `ChairmanStage` | `PM_PITCHES`, `PEER_REVIEWS` | `CHAIRMAN_DECISION` | Synthesize final decision |
| `SynthesizeFinalStage` | `USER_QUERY`, `STAGE1_RESULTS`, `STAGE2_RESULTS` | `STAGE3_RESULT` | Ported from llm-council stage3 |

### Market Layer

| Stage | Input | Output | Description |
|-------|-------|--------|-------------|
| `MarketSnapshotStage` | - | `MARKET_SNAPSHOT` | Frozen indicator inputs + execution constraints |
| `RiskManagementStage` | `CHAIRMAN_DECISION`, `MARKET_SNAPSHOT` | `RISK_ASSESSMENT` | Risk assessment + position sizing |

### Execution Layer

| Stage | Input | Output | Description |
|-------|-------|--------|-------------|
| `ExecutionStage` | `CHAIRMAN_DECISION`, `RISK_ASSESSMENT` | `EXECUTION_RESULT` | Place paper trades via Alpaca MCP |

---

## Pipeline Definitions

### Weekly Pipeline

```python
weekly_pipeline = Pipeline([
    # Research layer
    GeminiResearchStage(),
    PerplexityResearchStage(),

    # PM layer
    PMPitchStage(),

    # Peer review layer
    PeerReviewStage(),

    # Chairman layer
    ChairmanStage(),

    # Market layer
    MarketSnapshotStage(),
    RiskManagementStage(),

    # Execution layer
    ExecutionStage(),
])
```

### Checkpoint Pipeline

```python
checkpoint_pipeline = Pipeline([
    MarketSnapshotStage(),
    ConvictionUpdateStage(),
    RiskManagementStage(),
    ExecutionStage(),  # Only if action != STAY
])
```

---

## Example: Creating a Custom Stage

```python
from council.pipeline import Stage, PipelineContext, ContextKey

MY_OUTPUT = ContextKey("my_output")

class MyCustomStage(Stage):
    """Example custom stage."""

    @property
    def name(self) -> str:
        return "MyCustomStage"

    async def execute(self, context: PipelineContext) -> PipelineContext:
        # Get input from context
        user_query = context.get(USER_QUERY)
        if user_query is None:
            raise ValueError("USER_QUERY required")

        # Do some work
        result = f"Processed: {user_query}"

        # Return new context with output
        return context.set(MY_OUTPUT, result)
```

---

## Error Handling

### Stage-Level Error Handling

Each stage should:
1. Catch and log its own errors
2. Return a context with error information
3. Allow pipeline to continue (graceful degradation) OR fail fast (critical stages)

```python
async def execute(self, context: PipelineContext) -> PipelineContext:
    try:
        result = await self._do_work(context)
        return context.set(self.output_key, result)
    except Exception as e:
        logger.error(f"{self.name} failed: {e}")
        return context.set_metadata(f"{self.name}_error", str(e))
```

### Pipeline-Level Error Handling

```python
class Pipeline:
    async def execute(self, context: PipelineContext) -> PipelineContext:
        for stage in self.stages:
            try:
                context = await stage.execute(context)
            except Exception as e:
                logger.error(f"Pipeline failed at {stage.name}: {e}")
                context = context.set_metadata("failed_stage", stage.name)
                context = context.set_metadata("error", str(e))
                raise  # Or continue for graceful degradation
        return context
```

---

## Streaming and Progress

For long-running pipelines, stages can emit progress events:

```python
class ProgressCallback(ABC):
    @abstractmethod
    async def on_stage_start(self, stage_name: str):
        pass

    @abstractmethod
    async def on_stage_complete(self, stage_name: str, result: Any):
        pass

    @abstractmethod
    async def on_stage_error(self, stage_name: str, error: str):
        pass

class StreamingPipeline(Pipeline):
    def __init__(self, stages: List[Stage], callback: ProgressCallback):
        super().__init__(stages)
        self.callback = callback

    async def execute(self, context: PipelineContext) -> PipelineContext:
        for stage in self.stages:
            await self.callback.on_stage_start(stage.name)
            try:
                context = await stage.execute(context)
                await self.callback.on_stage_complete(stage.name, context)
            except Exception as e:
                await self.callback.on_stage_error(stage.name, str(e))
                raise
        return context
```

---

## JSON Schema Validation

All stage outputs should validate against schemas:

```python
from jsonschema import validate, ValidationError

class ValidatedStage(Stage):
    @property
    @abstractmethod
    def output_schema(self) -> dict:
        """JSON schema for output validation."""
        pass

    async def execute(self, context: PipelineContext) -> PipelineContext:
        result = await self._execute_impl(context)
        try:
            validate(instance=result, schema=self.output_schema)
        except ValidationError as e:
            raise ValueError(f"Output validation failed: {e}")
        return context.set(self.output_key, result)
```

---

## Testing Stages

```python
import pytest

@pytest.mark.asyncio
async def test_my_custom_stage():
    # Setup context
    context = PipelineContext().set(USER_QUERY, "test query")

    # Execute stage
    stage = MyCustomStage()
    result_context = await stage.execute(context)

    # Assert output
    assert result_context.has(MY_OUTPUT)
    assert result_context.get(MY_OUTPUT) == "Processed: test query"
```

---

## Migration from llm-council

| Original | New Pipeline Stage | Notes |
|----------|-------------------|-------|
| `stage1_collect_responses()` | `CollectResponsesStage` | Direct port |
| `stage2_collect_rankings()` | `CollectRankingsStage` | Direct port |
| `stage3_synthesize_final()` | `SynthesizeFinalStage` | Direct port |
| `run_full_council()` | `LLMCouncilPipeline` | Compose the 3 stages |
| `generate_conversation_title()` | `TitleGenerationStage` | Optional stage |

---

## References

- Original: `/tmp/llm-council/backend/council.py`
- Implementation: `/research/llm_trading/backend/council/pipeline/`
