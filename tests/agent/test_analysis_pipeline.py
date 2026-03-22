from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.analysis_pipeline import (
    final_report_node,
    research_coordinator_node,
)
from app.schemas.research import (
    CompressedResearch,
    DataSeries,
    ResearchBrief,
)


def _make_brief(
    *,
    product_name: str = "Test Product",
    market_category: str = "Electronics",
    research_questions: list[str] | None = None,
) -> ResearchBrief:
    return ResearchBrief(
        product_name=product_name,
        market_category=market_category,
        research_questions=research_questions or ["Q1?", "Q2?", "Q3?"],
    )


def _make_compressed(
    *,
    topic_title: str = "Topic A",
    summary: str = "Some findings",
    key_data_points: list[str] | None = None,
    numeric_datasets: list[DataSeries] | None = None,
    confidence: float = 0.7,
) -> CompressedResearch:
    return CompressedResearch(
        topic_title=topic_title,
        summary=summary,
        key_data_points=key_data_points or ["point 1"],
        numeric_datasets=numeric_datasets or [],
        confidence=confidence,
    )


def _make_state(
    *,
    query: str = "test query",
    brief: ResearchBrief | None = None,
    research_results: list[CompressedResearch] | None = None,
    report: str = "",
) -> MagicMock:
    state = MagicMock()
    state.query = query
    state.brief = brief
    state.research_results = research_results or []
    state.report = report
    return state


@pytest.mark.asyncio
@patch("app.agent.analysis_pipeline._coordinator_graph")
async def test_research_coordinator_node_invokes_coordinator_graph(
    mock_graph: MagicMock,
) -> None:
    compressed = _make_compressed()
    mock_graph.ainvoke = AsyncMock(
        return_value={"research_results": [compressed]},
    )

    brief = _make_brief()
    state = _make_state(brief=brief)

    result = await research_coordinator_node(state)

    mock_graph.ainvoke.assert_awaited_once()
    call_input = mock_graph.ainvoke.call_args[0][0]
    assert "brief" in call_input
    assert len(result["research_results"]) == 1


def test_final_report_node_raises_when_brief_is_none() -> None:
    state = _make_state(brief=None)

    with pytest.raises(ValueError, match="without a brief"):
        final_report_node(state)


@patch("app.agent.analysis_pipeline._report_llm")
def test_final_report_node_formats_research_in_prompt(
    mock_llm: MagicMock,
) -> None:
    mock_response = MagicMock()
    mock_response.content = "# Final Report"
    mock_llm.invoke.return_value = mock_response

    brief = _make_brief(product_name="Widget Pro")
    results = [
        _make_compressed(
            topic_title="Pricing",
            summary="Avg price $30",
            key_data_points=["$30 average", "$10 minimum"],
            confidence=0.85,
        ),
    ]
    state = _make_state(brief=brief, research_results=results)

    result = final_report_node(state)

    call_messages = mock_llm.invoke.call_args[0][0]
    user_content: str = call_messages[1]["content"]
    assert "Widget Pro" in user_content
    assert "Pricing" in user_content
    assert "Avg price $30" in user_content
    assert "$30 average" in user_content
    assert "<datasets>" in user_content
    assert "</datasets>" in user_content
    assert result["report"] == "# Final Report"


@patch("app.agent.analysis_pipeline._report_llm")
def test_final_report_node_includes_numeric_datasets_in_prompt(
    mock_llm: MagicMock,
) -> None:
    mock_response = MagicMock()
    mock_response.content = "# Report with Charts"
    mock_llm.invoke.return_value = mock_response

    brief = _make_brief(product_name="Widget Pro")
    results = [
        _make_compressed(
            topic_title="Pricing",
            summary="Avg price $30",
            key_data_points=["$30 average"],
            confidence=0.85,
            numeric_datasets=[
                DataSeries(
                    label="Price by Retailer",
                    entries={"Amazon": 29.99, "Best Buy": 34.99, "Walmart": 27.99},
                ),
            ],
        ),
        _make_compressed(
            topic_title="Trends",
            summary="Upward trend",
            key_data_points=["Growing demand"],
            confidence=0.6,
            numeric_datasets=[
                DataSeries(
                    label="Monthly Search Interest",
                    entries={"Jan": 72, "Feb": 65, "Mar": 80},
                ),
            ],
        ),
    ]
    state = _make_state(brief=brief, research_results=results)

    result = final_report_node(state)

    call_messages = mock_llm.invoke.call_args[0][0]
    user_content: str = call_messages[1]["content"]
    assert "<datasets>" in user_content
    assert "Price by Retailer" in user_content
    assert "Amazon: 29.99" in user_content
    assert "Best Buy: 34.99" in user_content
    assert "Monthly Search Interest" in user_content
    assert "Jan: 72" in user_content
    assert result["report"] == "# Report with Charts"
