"""Pipeline-first architecture for composable LLM stages.

This module provides a pipeline abstraction where:
- Each Stage is independent with well-defined input/output contracts
- Stages can be chained together flexibly
- PipelineContext carries state between stages
- Async execution is supported throughout
"""

from .base import Stage, Pipeline, PipelineContext
from .context import PipelineContext, ContextKey

__all__ = [
    "Stage",
    "Pipeline",
    "PipelineContext",
    "ContextKey",
]
