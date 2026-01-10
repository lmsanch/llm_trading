"""Requesty API client using OpenAI SDK for LLM queries."""

import os
import asyncio
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# REQUESTY API CONFIGURATION
# ============================================================================

REQUESTY_API_URL = "https://router.requesty.ai/v1"
REQUESTY_API_KEY = os.getenv("REQUESTY_API_KEY")

# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

REQUESTY_MODELS = {
    # PM Layer (Portfolio Managers)
    "chatgpt": {
        "model_id": "openai/gpt-5.1",
        "account": "CHATGPT",
        "alpaca_id": "PA3IUYCYRWGK",
        "role": "portfolio_manager",
    },
    "gemini": {
        "model_id": "google/gemini-3-pro-preview",
        "account": "GEMINI",
        "alpaca_id": "PA3M2HMSLN00",
        "role": "portfolio_manager",
    },
    "groq": {
        "model_id": "xai/grok-4-fast",
        "account": "GROQ",
        "alpaca_id": "PA33MEQA4WT7",
        "role": "portfolio_manager",
    },
    "claude": {
        "model_id": "anthropic/claude-sonnet-4-5",
        "account": "CLAUDE",
        "alpaca_id": "PA38PAHFRFYC",
        "role": "portfolio_manager",
    },
    "deepseek": {
        "model_id": "deepinfra/deepseek-ai/DeepSeek-V3",
        "account": "DEEPSEEK",
        "alpaca_id": "PA3KKW3TN54V",
        "role": "portfolio_manager",
    },
    # Chairman Layer
    "chairman": {
        "model_id": "anthropic/claude-opus-4-5",
        "account": "COUNCIL",
        "alpaca_id": "PA3MQLPXBSO1",
        "role": "chairman",
    },
}

# PM models list for parallel queries
PM_MODELS = ["chatgpt", "gemini", "groq", "claude", "deepseek"]

# ============================================================================
# CLIENT INITIALIZATION
# ============================================================================


def get_requesty_client() -> AsyncOpenAI:
    """Get Requesty API client instance."""
    if not REQUESTY_API_KEY:
        raise ValueError("REQUESTY_API_KEY environment variable not set")

    # Debug: Log first 20 chars of API key
    key_preview = REQUESTY_API_KEY[:20] if REQUESTY_API_KEY else "None"
    print(f"🔑 Requesty API Key (first 20 chars): {key_preview}...")
    print(f"🔗 Requesty API URL: {REQUESTY_API_URL}")

    return AsyncOpenAI(api_key=REQUESTY_API_KEY, base_url=REQUESTY_API_URL)


# ============================================================================
# QUERY FUNCTIONS
# ============================================================================


async def query_model(
    model_key: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 2000,
    temperature: float = 0.7,
    timeout: float = 120.0,
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via Requesty API.

    Args:
        model_key: Key from REQUESTY_MODELS (e.g., 'chatgpt', 'gemini')
        messages: List of message dicts with 'role' and 'content'
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature (0.0-1.0)
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'content', 'tokens', 'model_id', or None if failed
    """
    if model_key not in REQUESTY_MODELS:
        raise ValueError(f"Unknown model key: {model_key}")

    model_config = REQUESTY_MODELS[model_key]
    model_id = model_config["model_id"]

    try:
        client = get_requesty_client()

        from typing import cast

        response = await client.chat.completions.create(
            model=model_id,
            messages=cast(List[ChatCompletionMessageParam], messages),
            max_tokens=max_tokens,
            temperature=temperature,
        )

        content = (
            response.choices[0].message.content
            if response.choices and response.choices[0].message
            else ""
        )
        usage = response.usage
        tokens = {}
        if usage:
            tokens = {
                "input": getattr(usage, "prompt_tokens", 0),
                "output": getattr(usage, "completion_tokens", 0),
                "total": getattr(usage, "total_tokens", 0),
            }

        return {
            "content": content,
            "model": model_key,
            "model_id": model_id,
            "tokens": tokens,
            "account": model_config["account"],
            "alpaca_id": model_config["alpaca_id"],
            "role": model_config["role"],
        }

    except Exception as e:
        print(f"Error querying model {model_key} ({model_id}): {e}")
        return None


async def query_models_parallel(
    model_keys: List[str],
    messages: List[Dict[str, str]],
    max_tokens: int = 2000,
    temperature: float = 0.7,
    timeout: float = 120.0,
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel.

    Args:
        model_keys: List of model keys from REQUESTY_MODELS
        messages: List of message dicts to send to each model
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature
        timeout: Request timeout in seconds

    Returns:
        Dict mapping model key to response dict (or None if failed)
    """
    # Create tasks for all models
    tasks = [
        query_model(model_key, messages, max_tokens, temperature, timeout)
        for model_key in model_keys
    ]

    # Execute all in parallel
    responses = await asyncio.gather(*tasks)

    # Map model keys to their responses
    return {model_key: response for model_key, response in zip(model_keys, responses)}


async def query_pm_models(
    messages: List[Dict[str, str]],
    max_tokens: int = 4000,
    temperature: float = 0.7,
    model_keys: Optional[List[str]] = None,
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query PM models in parallel.

    Args:
        messages: List of message dicts
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature
        model_keys: Optional list of model keys to query (default: all PM models)

    Returns:
        Dict mapping PM model key to response dict
    """
    target_models = model_keys if model_keys else PM_MODELS
    return await query_models_parallel(target_models, messages, max_tokens, temperature)


async def query_chairman(
    messages: List[Dict[str, str]], max_tokens: int = 3000, temperature: float = 0.5
) -> Optional[Dict[str, Any]]:
    """
    Query chairman model (Claude Opus 4.5) for synthesis.

    Args:
        messages: List of message dicts
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature (lower for synthesis)

    Returns:
        Response dict or None if failed
    """
    return await query_model("chairman", messages, max_tokens, temperature)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def get_model_info(model_key: str) -> Dict[str, Any]:
    """Get model configuration by key."""
    if model_key not in REQUESTY_MODELS:
        raise ValueError(f"Unknown model key: {model_key}")
    return REQUESTY_MODELS[model_key].copy()


def get_pm_model_keys() -> List[str]:
    """Get list of PM model keys."""
    return PM_MODELS.copy()


def get_chairman_model_key() -> str:
    """Get chairman model key."""
    return "chairman"


def estimate_cost(tokens: int, model_key: str) -> float:
    """
    Estimate cost based on model (using 2025 pricing).

    Approximate pricing (input/output per 1M tokens):
    - GPT-5.2: $2.50 / $10.00
    - Gemini 3 Pro: $1.50 / $6.00
    - Grok 4.1: $4.00 / $8.00
    - Claude Sonnet 4.5: $3.00 / $15.00
    - Claude Opus 4.5: $15.00 / $75.00
    - DeepSeek V3: $0.50 / $2.00
    """
    pricing = {
        "chatgpt": {"input": 0.0000025, "output": 0.00001},
        "gemini": {"input": 0.0000015, "output": 0.000006},
        "groq": {"input": 0.000004, "output": 0.000008},
        "claude": {"input": 0.000003, "output": 0.000015},
        "chairman": {"input": 0.000015, "output": 0.000075},
        "deepseek": {"input": 0.0000005, "output": 0.000002},
    }

    if model_key not in pricing:
        return 0.0

    return tokens * pricing[model_key]["output"]


# ============================================================================
# MAIN (for testing)
# ============================================================================


async def main():
    """Test Requesty client with all models."""

    # Verify API key
    if not REQUESTY_API_KEY:
        print("❌ ERROR: REQUESTY_API_KEY environment variable not set!")
        print("   Set it with: export REQUESTY_API_KEY='your-key-here'")
        return

    print("🚀 Testing Requesty API with all models...\n")

    # Test message
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is 2+2? Keep it brief."},
    ]

    # Query all PM models in parallel
    print("Querying PM models...")
    pm_results = await query_pm_models(messages)

    for model_key, response in pm_results.items():
        if response:
            model_info = REQUESTY_MODELS[model_key]
            print(f"\n✅ {model_info['account']} ({model_key.upper()})")
            print(f"   Model ID: {response['model_id']}")
            print(f"   Response: {response['content'][:100]}...")
            print(f"   Tokens: {response['tokens']['total']}")
        else:
            print(f"\n❌ {model_key.upper()} - Failed")

    # Query chairman
    print("\n\nQuerying Chairman...")
    chairman_result = await query_chairman(messages)

    if chairman_result:
        print(f"\n✅ CHAIRMAN")
        print(f"   Model ID: {chairman_result['model_id']}")
        print(f"   Response: {chairman_result['content'][:100]}...")
        print(f"   Tokens: {chairman_result['tokens']['total']}")
    else:
        print("\n❌ CHAIRMAN - Failed")


if __name__ == "__main__":
    asyncio.run(main())
