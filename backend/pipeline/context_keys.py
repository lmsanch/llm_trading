from backend.pipeline.context import ContextKey


USER_QUERY = ContextKey("user_query")
STAGE1_RESULTS = ContextKey("stage1_results")
STAGE2_RESULTS = ContextKey("stage2_results")
STAGE3_RESULT = ContextKey("stage3_result")
LABEL_TO_MODEL = ContextKey("label_to_model")
AGGREGATE_RANKINGS = ContextKey("aggregate_rankings")
