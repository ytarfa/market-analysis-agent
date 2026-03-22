from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.coordinator import (
    evaluate_sufficiency_node,
    plan_research_node,
    spawn_researchers_node,
)
from app.schemas.research import (
    CompressedResearch,
    ResearchBrief,
    ResearchComplete,
    ResearchPlan,
    ResearchTopic,
    ToolHint,
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
    confidence: float = 0.7,
) -> CompressedResearch:
    return CompressedResearch(
        topic_title=topic_title,
        summary=summary,
        key_data_points=[],
        confidence=confidence,
    )


def _make_plan(
    topics: list[ResearchTopic] | None = None,
) -> ResearchPlan:
    return ResearchPlan(
        topics=topics
        or [
            ResearchTopic(
                title="Pricing",
                description="Investigate pricing",
                tool_hints=[ToolHint.WEB_SEARCH],
            ),
        ],
    )


def _make_state(
    *,
    brief: ResearchBrief | None = None,
    plan: ResearchPlan | None = None,
    research_results: list[CompressedResearch] | None = None,
    sufficiency: ResearchComplete | None = None,
    iteration: int = 0,
    max_iterations: int = 2,
) -> MagicMock:
    state = MagicMock()
    state.brief = brief or _make_brief()
    state.plan = plan
    state.research_results = research_results or []
    state.sufficiency = sufficiency
    state.iteration = iteration
    state.max_iterations = max_iterations
    return state


@patch("app.agent.coordinator._plan_llm")
def test_plan_research_node_returns_plan_and_increments_iteration(
    mock_llm: MagicMock,
) -> None:
    expected_plan = _make_plan()
    mock_llm.invoke.return_value = expected_plan

    state = _make_state(iteration=0)

    result = plan_research_node(state)

    assert result["plan"] is expected_plan
    assert result["iteration"] == 1


@patch("app.agent.coordinator._plan_llm")
def test_plan_research_node_includes_brief_in_prompt(
    mock_llm: MagicMock,
) -> None:
    mock_llm.invoke.return_value = _make_plan()

    brief = _make_brief(product_name="Widget Pro")
    state = _make_state(brief=brief)

    plan_research_node(state)

    call_messages = mock_llm.invoke.call_args[0][0]
    user_content: str = call_messages[1]["content"]
    assert "Widget Pro" in user_content


@patch("app.agent.coordinator._plan_llm")
def test_plan_research_node_includes_sufficiency_feedback_when_present(
    mock_llm: MagicMock,
) -> None:
    mock_llm.invoke.return_value = _make_plan()

    sufficiency = ResearchComplete(
        sufficient=False,
        feedback="Missing pricing data",
    )
    state = _make_state(sufficiency=sufficiency)

    plan_research_node(state)

    call_messages = mock_llm.invoke.call_args[0][0]
    user_content: str = call_messages[1]["content"]
    assert "Missing pricing data" in user_content


@patch("app.agent.coordinator._plan_llm")
def test_plan_research_node_includes_covered_topics_when_results_exist(
    mock_llm: MagicMock,
) -> None:
    mock_llm.invoke.return_value = _make_plan()

    results = [
        _make_compressed(topic_title="Pricing"),
        _make_compressed(topic_title="Sentiment"),
    ]
    state = _make_state(research_results=results)

    plan_research_node(state)

    call_messages = mock_llm.invoke.call_args[0][0]
    user_content: str = call_messages[1]["content"]
    assert "Pricing" in user_content
    assert "Sentiment" in user_content
    assert "already covered" in user_content.lower()


@pytest.mark.asyncio
@patch("app.agent.coordinator._researcher_graph")
async def test_spawn_researchers_node_invokes_subgraph_for_each_topic(
    mock_graph: MagicMock,
) -> None:
    compressed = _make_compressed(topic_title="Pricing")
    mock_graph.ainvoke = AsyncMock(return_value={"compressed": compressed})

    topics = [
        ResearchTopic(title="Pricing", description="Check prices"),
        ResearchTopic(title="Reviews", description="Check reviews"),
    ]
    plan = _make_plan(topics=topics)
    state = _make_state(plan=plan)

    result = await spawn_researchers_node(state)

    assert mock_graph.ainvoke.await_count == 2
    assert len(result["research_results"]) == 2


@pytest.mark.asyncio
@patch("app.agent.coordinator._researcher_graph")
async def test_spawn_researchers_node_appends_to_existing_results(
    mock_graph: MagicMock,
) -> None:
    new_compressed = _make_compressed(topic_title="New")
    mock_graph.ainvoke = AsyncMock(return_value={"compressed": new_compressed})

    existing = [_make_compressed(topic_title="Existing")]
    plan = _make_plan()
    state = _make_state(plan=plan, research_results=existing)

    result = await spawn_researchers_node(state)

    assert len(result["research_results"]) == 2
    assert result["research_results"][0].topic_title == "Existing"
    assert result["research_results"][1].topic_title == "New"


@pytest.mark.asyncio
@patch("app.agent.coordinator._researcher_graph")
async def test_spawn_researchers_node_creates_fallback_on_empty_output(
    mock_graph: MagicMock,
) -> None:
    mock_graph.ainvoke = AsyncMock(return_value={"compressed": None})

    topic = ResearchTopic(title="Empty Topic", description="Nothing here")
    plan = _make_plan(topics=[topic])
    state = _make_state(plan=plan)

    result = await spawn_researchers_node(state)

    assert len(result["research_results"]) == 1
    fallback = result["research_results"][0]
    assert fallback.topic_title == "Empty Topic"
    assert fallback.confidence == 0.0
    assert "did not produce results" in fallback.summary


@pytest.mark.asyncio
async def test_spawn_researchers_node_returns_existing_results_when_no_plan() -> None:
    existing = [_make_compressed(topic_title="Prior")]
    state = _make_state(plan=None, research_results=existing)

    result = await spawn_researchers_node(state)

    assert result["research_results"] is existing


@patch("app.agent.coordinator._sufficiency_llm")
def test_evaluate_sufficiency_node_returns_research_complete(
    mock_llm: MagicMock,
) -> None:
    expected = ResearchComplete(sufficient=True, feedback="")
    mock_llm.invoke.return_value = expected

    state = _make_state(research_results=[_make_compressed()])

    result = evaluate_sufficiency_node(state)

    assert result["sufficiency"] is expected


@patch("app.agent.coordinator._sufficiency_llm")
def test_evaluate_sufficiency_node_formats_results_in_prompt(
    mock_llm: MagicMock,
) -> None:
    mock_llm.invoke.return_value = ResearchComplete(sufficient=True)

    results = [
        _make_compressed(topic_title="Pricing", summary="Avg $30", confidence=0.8),
    ]
    state = _make_state(research_results=results)

    evaluate_sufficiency_node(state)

    call_messages = mock_llm.invoke.call_args[0][0]
    user_content: str = call_messages[1]["content"]
    assert "Pricing" in user_content
    assert "Avg $30" in user_content
    assert "80%" in user_content
