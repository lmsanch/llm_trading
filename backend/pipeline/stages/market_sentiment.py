"""Market sentiment stage for news search and sentiment analysis."""

from typing import List, Dict, Any
from ..base import Stage
from ..context import PipelineContext, ContextKey
from ...search.manager import SearchManager
from ...openrouter import query_model


SENTIMENT_PACK = ContextKey("sentiment_pack")
MARKET_SNAPSHOT = ContextKey("market_snapshot")


class MarketSentimentStage(Stage):
    """
    Market sentiment stage that gathers recent news and analyzes sentiment.

    This stage:
    1. Gets tradable instruments from market snapshot
    2. Searches for recent news on each instrument
    3. Extracts full article content via Jina Reader
    4. Generates sentiment summary
    5. Returns structured sentiment pack
    """

    def __init__(
        self,
        search_provider: str | None = None,
        search_terms: List[str] | None = None,
        temperature: float | None = None,
    ):
        super().__init__()
        from ..utils.temperature_manager import TemperatureManager

        self.search_provider = search_provider
        self.search_terms = search_terms or [
            "latest news",
            "market outlook",
            "analysis",
        ]
        self.temperature = temperature or TemperatureManager().get_temperature(
            "market_sentiment"
        )

    @property
    def name(self) -> str:
        return "MarketSentimentStage"

    async def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Execute market sentiment analysis.

        Args:
            context: Pipeline context with market snapshot

        Returns:
            New context with sentiment pack added
        """
        print("\n" + "=" * 60)
        print("📰 MARKET SENTIMENT STAGE")
        print("=" * 60)

        market_snapshot = context.get(MARKET_SNAPSHOT)
        if not market_snapshot:
            print("⚠️  No market snapshot found, skipping sentiment analysis")
            return context

        instruments = list(market_snapshot.get("instruments", {}).keys())
        print(
            f"📊 Analyzing sentiment for {len(instruments)} instruments: {instruments}"
        )

        search_manager = SearchManager()

        ticker_results = await search_manager.search_for_tickers(
            tickers=instruments,
            search_terms=self.search_terms,
            provider_id=self.search_provider or None,
        )

        sentiment_pack = {
            "asof_et": self._get_timestamp(),
            "search_provider": search_manager.get_default_provider(),
            "search_terms_used": self.search_terms,
            "instrument_sentiments": {},
            "overall_market_sentiment": "neutral",
            "key_headlines": [],
            "sentiment_summary": "",
        }

        for ticker, results in ticker_results.items():
            if results:
                print(f"  ✅ {ticker}: {len(results)} articles found")
                sentiment_pack["instrument_sentiments"][ticker] = {
                    "article_count": len(results),
                    "articles": [
                        {
                            "title": r.title,
                            "url": r.url,
                            "snippet": r.snippet,
                            "published_date": r.published_date,
                            "source": r.source,
                        }
                        for r in results[:5]
                    ],
                    "sentiment": "neutral",
                }
                sentiment_pack["key_headlines"].extend([r.title for r in results[:3]])
            else:
                print(f"  ⚠️  {ticker}: No articles found")
                sentiment_pack["instrument_sentiments"][ticker] = {
                    "article_count": 0,
                    "articles": [],
                    "sentiment": "neutral",
                }

        sentiment_pack["key_headlines"] = sentiment_pack["key_headlines"][:10]

        sentiment_summary = await self._generate_sentiment_summary(sentiment_pack)
        sentiment_pack["sentiment_summary"] = sentiment_summary

        print(f"📝 Sentiment Summary: {sentiment_summary}")

        return context.set(SENTIMENT_PACK, sentiment_pack)

    async def _generate_sentiment_summary(self, sentiment_pack: Dict[str, Any]) -> str:
        """Generate sentiment summary using an LLM."""
        try:
            from ...openrouter import query_model

            prompt = f"""You are a market sentiment analyst. Analyze the following news headlines and provide a brief sentiment summary.

Headlines:
{chr(10).join([f"- {h}" for h in sentiment_pack.get("key_headlines", [])])}

Provide:
1. Overall market sentiment (BULLISH/BEARISH/NEUTRAL)
2. Key themes driving the market
3. Any notable risks or opportunities

Keep it concise (3-4 sentences)."""

            messages = [{"role": "user", "content": prompt}]
            response = await query_model(
                model="google/gemini-2.5-flash",
                messages=messages,
                temperature=self.temperature,
                timeout=30.0,
            )

            if response is None:
                return "Neutral - sentiment analysis unavailable"

            return response.get("content", "Neutral sentiment analysis unavailable")

        except Exception as e:
            print(f"⚠️  Failed to generate sentiment summary: {e}")
            return "Neutral - sentiment analysis unavailable"

    def _get_timestamp(self) -> str:
        from datetime import datetime

        return datetime.utcnow().isoformat()
