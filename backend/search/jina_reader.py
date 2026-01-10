"""Jina Reader integration for full article content extraction."""

import httpx
from typing import Optional
from .base import SearchResult


async def fetch_article_content(url: str, timeout: float = 30.0) -> Optional[str]:
    """
    Fetch full article content using Jina Reader.

    Jina Reader extracts clean, readable content from any URL.

    Args:
        url: Article URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Full article text or None if failed
    """
    jina_url = f"https://r.jina.ai/http://{url}"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(jina_url)
            response.raise_for_status()

            return response.text

    except httpx.HTTPStatusError as e:
        print(f"⚠️  Jina Reader HTTP error for {url}: {e.response.status_code}")
        return None
    except Exception as e:
        print(f"⚠️  Jina Reader failed for {url}: {e}")
        return None


async def enrich_search_results(results: list, max_articles: int = 10) -> list:
    """
    Enrich search results with full article content.

    Args:
        results: List of SearchResult objects
        max_articles: Maximum number of articles to fetch full content for

    Returns:
        Enriched SearchResult list with content field populated
    """
    enriched = []

    for i, result in enumerate(results):
        if i >= max_articles:
            enriched.append(result)
            continue

        content = await fetch_article_content(result.url)
        if content:
            enriched.append(
                SearchResult(
                    title=result.title,
                    url=result.url,
                    snippet=result.snippet,
                    content=content,
                    source=result.source,
                    published_date=result.published_date,
                    relevance_score=result.relevance_score,
                )
            )
        else:
            enriched.append(result)

    return enriched
