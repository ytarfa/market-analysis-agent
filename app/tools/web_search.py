from typing import Any

from langchain.tools import tool
from pydantic import BaseModel, Field
from tavily import AsyncTavilyClient

from app.config import settings


class WebSearchResult(BaseModel):
    title: str
    url: str
    content: str
    score: float


class WebSearchResponse(BaseModel):
    query: str
    results: list[WebSearchResult]
    answer: str | None = Field(default=None)


@tool
async def web_search(query: str, max_results: int = 5) -> str:
    """Search the web for current information about a product or market.
    Use this tool to find pricing, competitor data, trends, and customer sentiment.

    Args:
        query: Specific search query e.g. "iPhone 16 Pro price comparison 2026"
        max_results: Number of results to return (1-10). Default is 5.
    """
    client = AsyncTavilyClient(api_key=settings.tavily_api_key)

    try:
        raw: dict[str, Any] = await client.search(
            query=query,
            max_results=max_results,
            include_answer=True,
        )
    except Exception as e:
        raise RuntimeError(f"Tavily search failed: {e}") from e

    response = WebSearchResponse(
        query=query,
        answer=raw.get("answer"),
        results=[
            WebSearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content", ""),
                score=r.get("score", 0.0),
            )
            for r in raw.get("results", [])
        ],
    )

    parts: list[str] = []

    if response.answer:
        parts.append(f"Quick answer: {response.answer}\n")

    for i, result in enumerate(response.results, start=1):
        parts.append(
            f"[{i}] {result.title}\n    URL: {result.url}\n    {result.content}\n"
        )

    return "\n".join(parts) if parts else f"No results found for: {query}"
