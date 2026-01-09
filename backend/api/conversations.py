"""Legacy chat API endpoints for conversation management."""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

# Create router for conversation endpoints
router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# Import storage and council functions
# These are legacy modules that exist at the backend root level
def get_storage():
    """
    Get the conversation storage module.

    Returns:
        conversation_storage module
    """
    try:
        # Import from parent backend directory
        import sys
        from pathlib import Path
        backend_root = Path(__file__).parent.parent.parent / "backend"
        if str(backend_root) not in sys.path:
            sys.path.insert(0, str(backend_root))
        import conversation_storage as storage
        return storage
    except ImportError as e:
        logger.error(f"Could not import conversation_storage: {e}", exc_info=True)
        raise


def get_council_functions():
    """
    Get the council functions for multi-stage council process.

    Returns:
        Tuple of (run_full_council, generate_conversation_title,
                  stage1_collect_responses, stage2_collect_rankings,
                  stage3_synthesize_final, calculate_aggregate_rankings)
    """
    try:
        from backend.council import (
            run_full_council,
            generate_conversation_title,
            stage1_collect_responses,
            stage2_collect_rankings,
            stage3_synthesize_final,
            calculate_aggregate_rankings,
        )
        return (
            run_full_council,
            generate_conversation_title,
            stage1_collect_responses,
            stage2_collect_rankings,
            stage3_synthesize_final,
            calculate_aggregate_rankings,
        )
    except ImportError as e:
        logger.error(f"Could not import council functions: {e}", exc_info=True)
        raise


# Initialize storage and council functions
try:
    storage = get_storage()
    (
        run_full_council,
        generate_conversation_title,
        stage1_collect_responses,
        stage2_collect_rankings,
        stage3_synthesize_final,
        calculate_aggregate_rankings,
    ) = get_council_functions()
except Exception as e:
    logger.error(f"Failed to initialize conversations module: {e}", exc_info=True)
    storage = None
    run_full_council = None
    generate_conversation_title = None
    stage1_collect_responses = None
    stage2_collect_rankings = None
    stage3_synthesize_final = None
    calculate_aggregate_rankings = None


@router.get("", response_model=List[Dict])
async def list_conversations() -> List[Dict[str, Any]]:
    """
    List all conversations (metadata only).

    Retrieves metadata for all stored conversations including ID, creation time,
    title, and message count. Does not include full message history.

    Returns:
        List of conversation metadata dictionaries. Each dict contains:
            - id: Unique conversation identifier (UUID)
            - created_at: ISO timestamp of conversation creation
            - title: Conversation title (auto-generated or default)
            - message_count: Number of messages in the conversation

        Sorted by creation time, newest first.

    Example Response:
        [
            {
                "id": "abc123-def456",
                "created_at": "2024-01-09T12:30:00.000Z",
                "title": "Discussion about market trends",
                "message_count": 6
            },
            {
                "id": "xyz789-uvw012",
                "created_at": "2024-01-08T15:45:00.000Z",
                "title": "New Conversation",
                "message_count": 2
            }
        ]

    Notes:
        - Uses conversation_storage module for JSON-based persistence
        - Returns empty list if no conversations exist
        - Errors are logged and re-raised as HTTPException
    """
    try:
        if storage is None:
            logger.error("Storage module not initialized")
            raise HTTPException(
                status_code=500, detail="Storage module not available"
            )

        conversations = storage.list_conversations()
        logger.info(f"Retrieved {len(conversations)} conversation(s)")
        return conversations

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing conversations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=Dict)
async def create_conversation(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new conversation.

    Initializes a new conversation with a unique ID and default metadata.
    The conversation starts empty with no messages and a default title.

    Args:
        request: Request body (currently unused, reserved for future extensions)

    Returns:
        New conversation dictionary containing:
            - id: Unique conversation identifier (UUID)
            - created_at: ISO timestamp of conversation creation
            - title: Default title ("New Conversation")
            - messages: Empty list of messages

    Example Request:
        {}

    Example Response:
        {
            "id": "abc123-def456",
            "created_at": "2024-01-09T12:30:00.000Z",
            "title": "New Conversation",
            "messages": []
        }

    Notes:
        - Generates a UUID v4 for the conversation ID
        - Conversation is persisted to disk immediately
        - Uses conversation_storage module for JSON-based persistence
    """
    try:
        if storage is None:
            logger.error("Storage module not initialized")
            raise HTTPException(
                status_code=500, detail="Storage module not available"
            )

        conversation_id = str(uuid.uuid4())
        conversation = storage.create_conversation(conversation_id)

        logger.info(f"Created new conversation: {conversation_id}")
        return conversation

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{conversation_id}", response_model=Dict)
async def get_conversation(conversation_id: str) -> Dict[str, Any]:
    """
    Get a specific conversation with all its messages.

    Retrieves the full conversation history including all user and assistant
    messages with complete multi-stage council responses.

    Args:
        conversation_id: Unique conversation identifier (UUID)

    Returns:
        Conversation dictionary containing:
            - id: Unique conversation identifier (UUID)
            - created_at: ISO timestamp of conversation creation
            - title: Conversation title
            - messages: List of all messages in chronological order
                User messages have: {role: "user", content: str}
                Assistant messages have: {role: "assistant", stage1: [...], stage2: [...], stage3: {...}}

    Raises:
        HTTPException: 404 if conversation not found
        HTTPException: 500 for other errors

    Example Response:
        {
            "id": "abc123-def456",
            "created_at": "2024-01-09T12:30:00.000Z",
            "title": "Discussion about market trends",
            "messages": [
                {
                    "role": "user",
                    "content": "What's the market outlook?"
                },
                {
                    "role": "assistant",
                    "stage1": [...],
                    "stage2": [...],
                    "stage3": {...}
                }
            ]
        }

    Notes:
        - Uses conversation_storage module for JSON-based persistence
        - Returns complete message history with all council stages
    """
    try:
        if storage is None:
            logger.error("Storage module not initialized")
            raise HTTPException(
                status_code=500, detail="Storage module not available"
            )

        conversation = storage.get_conversation(conversation_id)

        if conversation is None:
            logger.warning(f"Conversation not found: {conversation_id}")
            raise HTTPException(status_code=404, detail="Conversation not found")

        logger.info(f"Retrieved conversation: {conversation_id}")
        return conversation

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{conversation_id}/message")
async def send_message(
    conversation_id: str, request: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Send a message and run the 3-stage council process.

    Processes a user message through the complete multi-stage council:
    1. Stage 1: Multiple models generate independent responses
    2. Stage 2: Models peer-review and rank each other's responses
    3. Stage 3: Chairman synthesizes final answer based on rankings

    Returns the complete response with all stages once processing is complete.
    For streaming version, use POST /{conversation_id}/message/stream.

    Args:
        conversation_id: Unique conversation identifier (UUID)
        request: Request body containing:
            - content: User message text (required)

    Returns:
        Dict containing all council stages:
            - stage1: List of individual model responses with metadata
            - stage2: List of peer review rankings from each model
            - stage3: Final synthesized answer from chairman
            - metadata: Additional processing metadata (timings, rankings, etc.)

    Raises:
        HTTPException: 404 if conversation not found
        HTTPException: 500 for other errors

    Example Request:
        {
            "content": "What's the current market outlook?"
        }

    Example Response:
        {
            "stage1": [
                {
                    "model": "chatgpt",
                    "response": "The market shows...",
                    "reasoning": "...",
                    "timing": 1.23
                },
                ...
            ],
            "stage2": [
                {
                    "model": "chatgpt",
                    "rankings": {"A": 1, "B": 2, ...},
                    "reasoning": "...",
                    "timing": 0.87
                },
                ...
            ],
            "stage3": {
                "selected_model": "chatgpt",
                "selected_response": "The market shows...",
                "reasoning": "...",
                "timing": 0.95
            },
            "metadata": {
                "total_time": 3.05,
                "aggregate_rankings": {...},
                "label_to_model": {...}
            }
        }

    Notes:
        - First message triggers automatic title generation
        - All messages are persisted to storage immediately
        - Uses backend.council functions for multi-stage processing
        - This is a blocking call - use streaming endpoint for real-time updates
    """
    try:
        if storage is None or run_full_council is None:
            logger.error("Storage or council module not initialized")
            raise HTTPException(
                status_code=500, detail="Required modules not available"
            )

        # Check if conversation exists
        conversation = storage.get_conversation(conversation_id)
        if conversation is None:
            logger.warning(f"Conversation not found: {conversation_id}")
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Check if this is the first message
        is_first_message = len(conversation["messages"]) == 0
        user_content = request.get("content", "")

        # Add user message
        storage.add_user_message(conversation_id, user_content)
        logger.info(f"Added user message to conversation: {conversation_id}")

        # If this is the first message, generate a title
        if is_first_message and generate_conversation_title is not None:
            title = await generate_conversation_title(user_content)
            storage.update_conversation_title(conversation_id, title)
            logger.info(f"Generated title for conversation {conversation_id}: {title}")

        # Run the 3-stage council process
        logger.info(f"Starting council process for conversation: {conversation_id}")
        stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
            user_content
        )

        # Add assistant message with all stages
        storage.add_assistant_message(
            conversation_id, stage1_results, stage2_results, stage3_result
        )
        logger.info(f"Added assistant message to conversation: {conversation_id}")

        # Return the complete response with metadata
        return {
            "stage1": stage1_results,
            "stage2": stage2_results,
            "stage3": stage3_result,
            "metadata": metadata,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{conversation_id}/message/stream")
async def send_message_stream(
    conversation_id: str, request: Dict[str, Any]
) -> StreamingResponse:
    """
    Send a message and stream the 3-stage council process.

    Processes a user message through the complete multi-stage council with
    real-time Server-Sent Events (SSE) as each stage completes. This provides
    a better user experience by showing progress as it happens.

    Streams events for:
    - Stage 1 start/complete (individual model responses)
    - Stage 2 start/complete (peer review rankings)
    - Stage 3 start/complete (chairman synthesis)
    - Title generation complete (if first message)
    - Final completion or error

    Args:
        conversation_id: Unique conversation identifier (UUID)
        request: Request body containing:
            - content: User message text (required)

    Returns:
        StreamingResponse with Server-Sent Events. Each event has format:
            data: {"type": "<event_type>", "data": {...}, "metadata": {...}}

        Event types:
            - stage1_start: Stage 1 processing started
            - stage1_complete: Stage 1 done, data contains model responses
            - stage2_start: Stage 2 processing started
            - stage2_complete: Stage 2 done, data contains rankings
            - stage3_start: Stage 3 processing started
            - stage3_complete: Stage 3 done, data contains final answer
            - title_complete: Title generated, data contains {title: str}
            - complete: All processing complete
            - error: Processing failed, includes error message

    Raises:
        HTTPException: 404 if conversation not found (before streaming starts)

    Example Request:
        {
            "content": "What's the current market outlook?"
        }

    Example Event Stream:
        data: {"type": "stage1_start"}

        data: {"type": "stage1_complete", "data": [...]}

        data: {"type": "stage2_start"}

        data: {"type": "stage2_complete", "data": [...], "metadata": {...}}

        data: {"type": "stage3_start"}

        data: {"type": "stage3_complete", "data": {...}}

        data: {"type": "title_complete", "data": {"title": "..."}}

        data: {"type": "complete"}

    Notes:
        - Uses Server-Sent Events (text/event-stream)
        - Title generation runs in parallel with council stages
        - All messages are persisted to storage after completion
        - Errors are sent as SSE events rather than exceptions
        - Connection uses Cache-Control: no-cache and Connection: keep-alive
        - Uses backend.council functions for multi-stage processing
    """
    try:
        if (
            storage is None
            or stage1_collect_responses is None
            or stage2_collect_rankings is None
            or stage3_synthesize_final is None
            or calculate_aggregate_rankings is None
        ):
            logger.error("Storage or council module not initialized")
            raise HTTPException(
                status_code=500, detail="Required modules not available"
            )

        # Check if conversation exists
        conversation = storage.get_conversation(conversation_id)
        if conversation is None:
            logger.warning(f"Conversation not found: {conversation_id}")
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Check if this is the first message
        is_first_message = len(conversation["messages"]) == 0
        user_content = request.get("content", "")

        async def event_generator():
            try:
                # Add user message
                storage.add_user_message(conversation_id, user_content)
                logger.info(f"Added user message to conversation: {conversation_id}")

                # Start title generation in parallel (don't await yet)
                title_task = None
                if is_first_message and generate_conversation_title is not None:
                    title_task = asyncio.create_task(
                        generate_conversation_title(user_content)
                    )

                # Stage 1: Collect responses
                logger.info(f"Stage 1 started for conversation: {conversation_id}")
                yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"

                stage1_results = await stage1_collect_responses(user_content)
                yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"
                logger.info(f"Stage 1 complete for conversation: {conversation_id}")

                # Stage 2: Collect rankings
                logger.info(f"Stage 2 started for conversation: {conversation_id}")
                yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"

                stage2_results, label_to_model = await stage2_collect_rankings(
                    user_content, stage1_results
                )
                aggregate_rankings = calculate_aggregate_rankings(
                    stage2_results, label_to_model
                )
                yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"
                logger.info(f"Stage 2 complete for conversation: {conversation_id}")

                # Stage 3: Synthesize final answer
                logger.info(f"Stage 3 started for conversation: {conversation_id}")
                yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"

                stage3_result = await stage3_synthesize_final(
                    user_content, stage1_results, stage2_results
                )
                yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"
                logger.info(f"Stage 3 complete for conversation: {conversation_id}")

                # Wait for title generation if it was started
                if title_task:
                    title = await title_task
                    storage.update_conversation_title(conversation_id, title)
                    yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"
                    logger.info(f"Title generated for conversation {conversation_id}: {title}")

                # Save complete assistant message
                storage.add_assistant_message(
                    conversation_id, stage1_results, stage2_results, stage3_result
                )
                logger.info(f"Added assistant message to conversation: {conversation_id}")

                # Send completion event
                yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                logger.info(f"Council process complete for conversation: {conversation_id}")

            except Exception as e:
                logger.error(f"Error in streaming message: {e}", exc_info=True)
                # Send error event
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initializing streaming message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
