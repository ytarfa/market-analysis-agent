from typing import Any, Generator
from unittest.mock import AsyncMock, patch

import pytest

from app.tools.web_search import web_search


@pytest.fixture
def mock_tavily() -> Generator[AsyncMock, None, None]:
    mock_client = AsyncMock()
    with patch("app.tools.web_search.AsyncTavilyClient", return_value=mock_client):
        yield mock_client


def tavily_response(
    results: list[dict[str, Any]] = [],
    answer: str | None = None,
) -> dict[str, Any]:
    return {"answer": answer, "results": results}


@pytest.mark.asyncio
async def test_returns_formatted_string_with_results(mock_tavily: AsyncMock) -> None:
    answer = "answer"
    results = [
        {
            "title": "iphone",
            "url": "example.com/review",
            "content": "The iphone is a phone",
            "score": 0.95,
        }
    ]
    mock_tavily.search.return_value = tavily_response(results=results, answer=answer)

    result: str = await web_search.ainvoke({"query": "iPhone 16 Pro price"})

    assert "[1]" in result
    assert "iphone" in result
    assert "example.com/review" in result
    assert "The iphone is a phone" in result


@pytest.mark.asyncio
async def test_empty_results_returns_no_results_message(mock_tavily: AsyncMock) -> None:
    mock_tavily.search.return_value = tavily_response()

    result: str = await web_search.ainvoke({"query": "some query"})

    assert "No results found" in result
    assert "some query" in result


@pytest.mark.asyncio
async def test_raises_runtime_error_on_tavily_failure(mock_tavily: AsyncMock) -> None:
    mock_tavily.search.side_effect = Exception("Network timeout")

    with pytest.raises(RuntimeError, match="Tavily search failed: Network timeout"):
        await web_search.ainvoke({"query": "test"})
