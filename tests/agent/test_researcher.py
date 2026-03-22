from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agent.researcher import (
    compress_research_node,
    researcher_node,
    researcher_tools_node,
    should_continue,
)
from app.schemas.research import CompressedResearch, ResearchTopic, ToolHint


def _make_topic(
    *,
    title: str = "Test Topic",
    description: str = "Investigate test things",
    tool_hints: list[ToolHint] | None = None,
) -> ResearchTopic:
    return ResearchTopic(
        title=title,
        description=description,
        tool_hints=tool_hints or [],
    )


def _make_state(
    *,
    topic: ResearchTopic | None = None,
    messages: list | None = None,
    compressed: CompressedResearch | None = None,
) -> MagicMock:
    state = MagicMock()
    state.topic = topic or _make_topic()
    state.messages = messages or []
    state.compressed = compressed
    return state


@patch("app.agent.researcher._researcher_llm")
def test_researcher_node_formats_tool_hints_in_system_prompt(
    mock_llm: MagicMock,
) -> None:
    mock_llm.invoke.return_value = AIMessage(content="ok")

    topic = _make_topic(
        tool_hints=[ToolHint.WEB_SEARCH, ToolHint.FETCH_REVIEWS],
    )
    state = _make_state(topic=topic)

    researcher_node(state)

    messages = mock_llm.invoke.call_args[0][0]
    system_content: str = messages[0]["content"]
    assert "web_search, fetch_reviews" in system_content


@patch("app.agent.researcher._researcher_llm")
def test_researcher_node_uses_fallback_tool_hint_when_empty(
    mock_llm: MagicMock,
) -> None:
    mock_llm.invoke.return_value = AIMessage(content="ok")

    topic = _make_topic(tool_hints=[])
    state = _make_state(topic=topic)

    researcher_node(state)

    messages = mock_llm.invoke.call_args[0][0]
    system_content: str = messages[0]["content"]
    assert "any available tool" in system_content


@pytest.mark.asyncio
@patch("app.agent.researcher._tools_by_name")
async def test_researcher_tools_node_invokes_correct_tool_by_name(
    mock_tools_by_name: MagicMock,
) -> None:
    mock_tool = AsyncMock()
    mock_tool.ainvoke.return_value = "search result"
    mock_tools_by_name.__getitem__ = MagicMock(return_value=mock_tool)

    ai_msg = AIMessage(
        content="",
        tool_calls=[
            {"name": "web_search", "args": {"query": "test"}, "id": "call_1"},
        ],
    )
    state = _make_state(messages=[ai_msg])

    result = await researcher_tools_node(state)

    mock_tools_by_name.__getitem__.assert_called_once_with("web_search")
    mock_tool.ainvoke.assert_awaited_once_with({"query": "test"})
    assert len(result["messages"]) == 1
    assert result["messages"][0].content == "search result"


@pytest.mark.asyncio
@patch("app.agent.researcher._tools_by_name")
async def test_researcher_tools_node_handles_multiple_tool_calls(
    mock_tools_by_name: MagicMock,
) -> None:
    mock_tool_a = AsyncMock()
    mock_tool_a.ainvoke.return_value = "result_a"
    mock_tool_b = AsyncMock()
    mock_tool_b.ainvoke.return_value = "result_b"

    def _lookup(name: str) -> AsyncMock:
        return {"web_search": mock_tool_a, "fetch_reviews": mock_tool_b}[name]

    mock_tools_by_name.__getitem__ = MagicMock(side_effect=_lookup)

    ai_msg = AIMessage(
        content="",
        tool_calls=[
            {"name": "web_search", "args": {"query": "a"}, "id": "call_1"},
            {"name": "fetch_reviews", "args": {"product": "b"}, "id": "call_2"},
        ],
    )
    state = _make_state(messages=[ai_msg])

    result = await researcher_tools_node(state)

    assert len(result["messages"]) == 2
    assert result["messages"][0].content == "result_a"
    assert result["messages"][1].content == "result_b"


@patch("app.agent.researcher._compress_llm")
def test_compress_research_node_concatenates_message_contents(
    mock_llm: MagicMock,
) -> None:
    mock_llm.invoke.return_value = CompressedResearch(
        topic_title="T",
        summary="S",
    )

    messages = [
        HumanMessage(content="hello"),
        AIMessage(content="world"),
    ]
    state = _make_state(messages=messages)

    compress_research_node(state)

    call_messages = mock_llm.invoke.call_args[0][0]
    user_content: str = call_messages[1]["content"]
    assert "[human] hello" in user_content
    assert "[ai] world" in user_content


@patch("app.agent.researcher._compress_llm")
def test_compress_research_node_skips_empty_content_messages(
    mock_llm: MagicMock,
) -> None:
    mock_llm.invoke.return_value = CompressedResearch(
        topic_title="T",
        summary="S",
    )

    messages = [
        HumanMessage(content="hello"),
        AIMessage(content=""),
        ToolMessage(content="data", tool_call_id="c1"),
    ]
    state = _make_state(messages=messages)

    compress_research_node(state)

    call_messages = mock_llm.invoke.call_args[0][0]
    user_content: str = call_messages[1]["content"]
    assert "[human] hello" in user_content
    assert "[ai]" not in user_content
    assert "[tool] data" in user_content


@patch("app.agent.researcher._compress_llm")
def test_compress_research_node_returns_compressed_research(
    mock_llm: MagicMock,
) -> None:
    expected = CompressedResearch(
        topic_title="Pricing",
        summary="Prices range from $10-$50",
        key_data_points=["avg $30"],
        confidence=0.8,
    )
    mock_llm.invoke.return_value = expected

    state = _make_state(messages=[HumanMessage(content="hi")])

    result = compress_research_node(state)

    assert result["compressed"] is expected


def test_should_continue_returns_tools_when_tool_calls_present() -> None:
    ai_msg = AIMessage(
        content="",
        tool_calls=[
            {"name": "web_search", "args": {"query": "test"}, "id": "call_1"},
        ],
    )
    state = _make_state(messages=[ai_msg])

    assert should_continue(state) == "researcher_tools"


def test_should_continue_returns_compress_when_no_tool_calls() -> None:
    ai_msg = AIMessage(content="I have enough data now.")
    state = _make_state(messages=[ai_msg])

    assert should_continue(state) == "compress_research"
