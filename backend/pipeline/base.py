from abc import ABC, abstractmethod
from typing import List

from .context import PipelineContext


class Stage(ABC):
    """Base class for all pipeline stages. Must be async and return a new PipelineContext (never mutate input)."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Execute stage logic and return a new context.

        NEVER mutate the input context. Always return a new context.
        """
        pass


class Pipeline:
    """Chain of stages with sequential async execution. Immutable - with_stage() returns new pipeline."""

    def __init__(self, stages: List[Stage] | None = None):
        self.stages = stages or []

    async def execute(self, context: PipelineContext) -> PipelineContext:
        current_context = context
        for stage in self.stages:
            current_context = await stage.execute(current_context)
        return current_context

    def with_stage(self, stage: Stage) -> "Pipeline":
        """
        Return new pipeline with stage appended.

        Creates a new pipeline, leaves the original unchanged.
        """
        return Pipeline(self.stages + [stage])

    def __len__(self) -> int:
        return len(self.stages)

    def __repr__(self) -> str:
        stage_names = [s.name for s in self.stages]
        return f"Pipeline(stages={stage_names})"
