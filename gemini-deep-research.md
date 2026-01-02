# Google Gemini Deep Research API Guide

This guide explains how to properly use Google's Gemini Deep Research API (Interactions API) based on working implementations.

## Overview

Google's Deep Research uses the **Interactions API** (v1beta), which is different from the standard `generateContent` API. It's designed for complex research tasks that require:
- Web search and information gathering
- Multi-step reasoning
- 5-30 minute processing time
- Asynchronous background execution

## API Model

**Model ID:** `deep-research-pro-preview-12-2025`

**API Endpoint:** `https://generativelanguage.googleapis.com/v1beta/interactions`

**Rate Limit:** ~1 request per minute (may vary by quota)

## Authentication

The API uses API key authentication via query parameter:

```python
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
```

## Request Flow

### 1. Create Interaction (Start Research)

**Endpoint:** `POST https://generativelanguage.googleapis.com/v1beta/interactions?key={API_KEY}`

**Request Body:**
```json
{
  "agent": "deep-research-pro-preview-12-2025",
  "input": "Your research question here",
  "background": true
}
```

**Important Notes:**
- `background: true` is **required** for deep research
- The request returns immediately with an interaction ID
- No `config` or `generation_config` parameters are supported

**Response Structure:**
```json
{
  "id": "interaction_id_here",
  "name": "interactions/interaction_id_here",
  "status": "CREATED"
}
```

**ID Extraction:**
The API may return the ID in different formats:
- `"id": "abc123"`
- `"name": "interactions/abc123"`
- `"interactionId": "abc123"`

Extract the actual ID (not the full "interactions/..." path):
```python
interaction_id = data.get("id", "") or data.get("name", "") or data.get("interactionId", "")

# If format is "interactions/ID", extract just the ID
if "/" in interaction_id:
    parts = interaction_id.split("/")
    if "interactions" in parts:
        idx = parts.index("interactions")
        if idx + 1 < len(parts):
            interaction_id = parts[idx + 1]
```

### 2. Poll for Completion

**Endpoint:** `GET https://generativelanguage.googleapis.com/v1beta/interactions/{interaction_id}?key={API_KEY}`

**Polling Strategy:**
- Poll every 10-30 seconds
- Maximum wait time: 30 minutes (1800 seconds)
- Check status/state field for completion

**Response Status Values:**

The API uses inconsistent field names. Check both `status` and `state`:

```python
state = data.get("state") or data.get("status") or ""
state = state.upper()
```

**Status Values:**
- **In Progress:** `CREATED`, `IN_PROGRESS`, `RUNNING`, `PENDING`, `ACTIVE`
- **Success:** `COMPLETED`, `COMPLETE`, `DONE`, `SUCCEEDED`
- **Failure:** `FAILED`, `ERROR`, `CANCELED`, `CANCELLED`

### 3. Extract Results

When status is `COMPLETED`, extract the output from the response.

**Response Structure:**
```json
{
  "id": "interaction_id",
  "status": "COMPLETED",
  "outputs": [
    {
      "text": "Full research report here..."
    }
  ]
}
```

**Alternative Structure:**
```json
{
  "id": "interaction_id",
  "status": "COMPLETED",
  "output": {
    "text": "Full research report here..."
  }
}
```

**Extraction Code:**
```python
# Try outputs array first (most common)
outputs = data.get("outputs", [])
if outputs and len(outputs) > 0:
    last_output = outputs[-1]
    if isinstance(last_output, dict):
        content = last_output.get("text", "").strip()
    else:
        content = str(last_output).strip()

# Fallback to output object
if not content:
    content = data.get("output", {}).get("text", "").strip()
```

## Complete Working Example

```python
import httpx
import time
import json
from typing import Dict, Any

GOOGLE_API_KEY = "your_api_key_here"
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

async def run_deep_research(prompt: str) -> str:
    """
    Run Google Deep Research and return the result.

    Args:
        prompt: Research question or prompt

    Returns:
        Research report as string
    """
    # Step 1: Create interaction
    create_url = f"{BASE_URL}/interactions?key={GOOGLE_API_KEY}"

    payload = {
        "agent": "deep-research-pro-preview-12-2025",
        "input": prompt,
        "background": True
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(create_url, json=payload)
        response.raise_for_status()
        data = response.json()

    # Extract interaction ID
    interaction_id = data.get("id", "") or data.get("name", "")
    if "/" in interaction_id:
        interaction_id = interaction_id.split("/")[-1]

    print(f"✅ Created interaction: {interaction_id}")

    # Step 2: Poll for completion
    poll_url = f"{BASE_URL}/interactions/{interaction_id}?key={GOOGLE_API_KEY}"

    max_wait = 1800  # 30 minutes
    poll_interval = 10  # 10 seconds
    start_time = time.time()

    while time.time() - start_time < max_wait:
        await asyncio.sleep(poll_interval)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(poll_url)
            response.raise_for_status()
            data = response.json()

        # Check status
        status = (data.get("status") or data.get("state") or "").upper()

        if status in ["COMPLETED", "COMPLETE", "DONE", "SUCCEEDED"]:
            # Extract content
            outputs = data.get("outputs", [])
            if outputs:
                content = outputs[-1].get("text", "") if isinstance(outputs[-1], dict) else str(outputs[-1])
            else:
                content = data.get("output", {}).get("text", "")

            print(f"✅ Research completed!")
            return content.strip()

        elif status in ["FAILED", "ERROR", "CANCELED", "CANCELLED"]:
            error = data.get("error", "Unknown error")
            raise Exception(f"Research failed: {error}")

        else:
            elapsed = int(time.time() - start_time)
            print(f"⏳ Polling... ({elapsed}s, status: {status})")

    raise TimeoutError(f"Research timed out after {max_wait}s")
```

## Parsing JSON from Response

Deep Research often returns markdown-formatted responses with JSON code blocks:

```python
def extract_json_from_response(content: str) -> dict:
    """Extract JSON from markdown code blocks or raw text."""

    # Try markdown code block first
    json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try to find raw JSON object
        json_start = content.find('{')
        if json_start >= 0:
            # Find matching closing brace
            brace_count = 0
            for i, char in enumerate(content[json_start:], json_start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_str = content[json_start:i+1]
                        break
        else:
            return {}

    # Parse JSON
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        return {}
```

## Common Issues & Fixes

### Issue 1: "Empty interaction ID"
**Cause:** Not properly extracting ID from response
**Fix:** Check all possible field names (`id`, `name`, `interactionId`)

### Issue 2: Polling never completes
**Cause:** Incorrect status checking or wrong URL format
**Fix:**
- Ensure URL doesn't have trailing slash before `?key=`
- Check both `status` and `state` fields
- Use case-insensitive comparison

### Issue 3: Empty response content
**Cause:** Looking for wrong field in completed response
**Fix:** Check both `outputs` array and `output` object

### Issue 4: JSON parsing fails
**Cause:** Response may include markdown or extra text
**Fix:** Extract JSON using regex, handle code blocks properly

### Issue 5: Rate limit errors
**Cause:** Too many requests
**Fix:** Wait 60+ seconds between requests, implement exponential backoff

## Best Practices

1. **Always use `background: true`** - Required for deep research
2. **Implement generous timeouts** - Research can take 5-30 minutes
3. **Handle all status variations** - API uses inconsistent field names
4. **Extract IDs carefully** - May come in different formats
5. **Poll conservatively** - 10-30 second intervals to avoid rate limits
6. **Validate outputs** - Check both `outputs` and `output` fields
7. **Parse JSON defensively** - Handle markdown, code blocks, extra text
8. **Add retry logic** - Network issues can occur during long polls

## Differences from Standard Gemini API

| Feature | Standard API | Deep Research API |
|---------|-------------|-------------------|
| Endpoint | `/v1beta/models/.../generateContent` | `/v1beta/interactions` |
| Response | Synchronous | Asynchronous (polling) |
| Duration | Seconds | 5-30 minutes |
| Config | Supports `generation_config` | Does not support config |
| Background | Optional | Required (`background: true`) |
| Web Search | No | Yes (built-in) |

## Cost Considerations

Based on observed usage:
- **Base cost per request:** ~$0.40-$0.80 USD
- **Variable by complexity:** Higher for more complex research
- **No token-based pricing:** Fixed per interaction
- **Compare with alternatives:** Perplexity sonar-pro is token-based and may be cheaper for simple queries

## Testing

Test with a simple query first:

```python
prompt = "What are the top 3 technology trends in 2026?"

result = await run_deep_research(prompt)
print(result)
```

Expected behavior:
1. Returns interaction ID immediately (< 1 second)
2. Polls show "IN_PROGRESS" status for several minutes
3. Eventually returns "COMPLETED" with comprehensive research

## Your Current Implementation Issues

Looking at your code in `backend/research/gemini_client.py`, you have the right structure but a few issues:

1. ✅ **Correct:** Using Interactions API endpoint
2. ✅ **Correct:** Setting `background: True`
3. ⚠️ **Issue:** In `_poll_research()` line 151, you use `asyncio.sleep()` but don't import it at the top
4. ⚠️ **Issue:** Not checking `outputs` array in response (line 57 only checks `output.text`)
5. ⚠️ **Issue:** Status checking is good but could normalize to uppercase for consistency

## Recommended Fixes

### Fix 1: Move asyncio import to top
```python
# At top of file
import asyncio
import os
import json
import re
import time
from typing import Dict, Any
```

### Fix 2: Improve output extraction
```python
# In _poll_research after state == "completed"
# Extract content from outputs array (primary) or output object (fallback)
outputs = data.get("outputs", [])
if outputs and len(outputs) > 0:
    last_output = outputs[-1]
    content = last_output.get("text", "") if isinstance(last_output, dict) else str(last_output)
else:
    content = data.get("output", {}).get("text", "")

if not content:
    return {"state": "completed", "output": {"text": ""}}

data["output"] = {"text": content}
return data
```

### Fix 3: Normalize status checking
```python
state = (data.get("state") or data.get("status") or "").upper()

if state in ["COMPLETED", "COMPLETE", "DONE", "SUCCEEDED"]:
    # ... handle completion
```

## References

- Working implementation: `/research/granite-todo/corpus_generator/model_clients.py`
- Interactions API docs: https://ai.google.dev/api/interactions
- Your current code: `/research/llm_trading/backend/research/gemini_client.py`

---

**Last Updated:** 2026-01-01
**Status:** Production-tested with granite-todo project
