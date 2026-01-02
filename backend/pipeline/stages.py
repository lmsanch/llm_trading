from typing import Dict, List, Any

from .base import Stage
from .context import PipelineContext
from .context_keys import (
    USER_QUERY,
    STAGE1_RESULTS,
    STAGE2_RESULTS,
    STAGE3_RESULT,
    LABEL_TO_MODEL,
    AGGREGATE_RANKINGS,
)
import backend.council as council


class CollectResponsesStage(Stage):
    @property
    def name(self) -> str:
        return "CollectResponses"

    async def execute(self, context: PipelineContext) -> PipelineContext:
        user_query = context.get(USER_QUERY)

        if not user_query:
            raise ValueError("USER_QUERY must be set in context")

        stage1_results = await council.stage1_collect_responses(user_query)

        return context.set(STAGE1_RESULTS, stage1_results)


class CollectRankingsStage(Stage):
    @property
    def name(self) -> str:
        return "CollectRankings"

    async def execute(self, context: PipelineContext) -> PipelineContext:
        user_query = context.get(USER_QUERY)
        stage1_results = context.get(STAGE1_RESULTS)

        if not user_query or not stage1_results:
            raise ValueError("USER_QUERY and STAGE1_RESULTS must be set in context")

        stage2_results, label_to_model = await council.stage2_collect_rankings(
            user_query, stage1_results
        )

        aggregate_rankings = council.calculate_aggregate_rankings(
            stage2_results, label_to_model
        )

        return (
            context.set(STAGE2_RESULTS, stage2_results)
            .set(LABEL_TO_MODEL, label_to_model)
            .set(AGGREGATE_RANKINGS, aggregate_rankings)
        )


class SynthesizeFinalStage(Stage):
    @property
    def name(self) -> str:
        return "SynthesizeFinal"

    async def execute(self, context: PipelineContext) -> PipelineContext:
        user_query = context.get(USER_QUERY)
        stage1_results = context.get(STAGE1_RESULTS)
        stage2_results = context.get(STAGE2_RESULTS)

        if not user_query or not stage1_results or not stage2_results:
            raise ValueError(
                "USER_QUERY, STAGE1_RESULTS, and STAGE2_RESULTS must be set in context"
            )

        stage3_result = await council.stage3_synthesize_final(
            user_query, stage1_results, stage2_results
        )

        return context.set(STAGE3_RESULT, stage3_result)
