from __future__ import annotations

from typing import Annotated, Any, Literal, cast

from langchain.chat_models import init_chat_model
from langchain.tools import BaseTool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

from app.agent.researcher_prompts import (
    COMPRESS_RESEARCH_PROMPT,
    RESEARCHER_SYSTEM_PROMPT,
)
from app.config import settings
from app.schemas.research import CompressedResearch, ResearchTopic
from app.tools.fetch_reviews import fetch_reviews
from app.tools.google_trends import google_trends
from app.tools.web_search import web_search


class ResearcherState(BaseModel):
    topic: ResearchTopic = Field(
        description="The research topic this agent is investigating.",
    )
    messages: Annotated[list[BaseMessage], add_messages] = Field(
        default_factory=list,
    )
    compressed: CompressedResearch | None = Field(
        default=None,
        description="Structured summary produced after the ReAct loop completes.",
    )


_base_llm: BaseChatModel = init_chat_model(
    model=settings.model,
    api_key=settings.anthropic_api_key,
    max_tokens=settings.max_tokens,
)

_tools: list[BaseTool] = [web_search, fetch_reviews, google_trends]
_tools_by_name: dict[str, BaseTool] = {t.name: t for t in _tools}
_researcher_llm = _base_llm.bind_tools(_tools)

_compress_llm = _base_llm.with_structured_output(CompressedResearch)


def researcher_node(state: ResearcherState) -> dict[str, list[BaseMessage]]:
    if not state.messages:
        tool_hint_str: str = (
            ", ".join(h.value for h in state.topic.tool_hints)
            if state.topic.tool_hints
            else "any available tool"
        )
        system_prompt: str = RESEARCHER_SYSTEM_PROMPT.format(
            topic_title=state.topic.title,
            topic_description=state.topic.description,
            tool_hints=tool_hint_str,
        )
        messages: list[Any] = [
            {"role": "system", "content": system_prompt},
            HumanMessage(
                content=(
                    f"Research the following topic: {state.topic.title}\n\n"
                    f"{state.topic.description}"
                )
            ),
        ]
    else:
        system_prompt = RESEARCHER_SYSTEM_PROMPT.format(
            topic_title=state.topic.title,
            topic_description=state.topic.description,
            tool_hints=(
                ", ".join(h.value for h in state.topic.tool_hints)
                if state.topic.tool_hints
                else "any available tool"
            ),
        )
        messages = [
            {"role": "system", "content": system_prompt},
            *state.messages,
        ]

    response: BaseMessage = _researcher_llm.invoke(messages)
    return {"messages": [response]}


async def researcher_tools_node(
    state: ResearcherState,
) -> dict[str, list[ToolMessage]]:
    last_message: AIMessage = cast(AIMessage, state.messages[-1])
    results: list[ToolMessage] = []

    for tool_call in last_message.tool_calls:
        tool: BaseTool = _tools_by_name[tool_call["name"]]
        observation: str = await tool.ainvoke(tool_call["args"])
        results.append(
            ToolMessage(content=str(observation), tool_call_id=tool_call["id"])
        )

    return {"messages": results}


def compress_research_node(
    state: ResearcherState,
) -> dict[str, CompressedResearch]:
    conversation: str = "\n\n".join(
        f"[{m.type}] {m.content}"
        for m in state.messages
        if isinstance(m.content, str) and m.content
    )

    compressed: CompressedResearch = cast(
        CompressedResearch,
        _compress_llm.invoke(
            [
                {"role": "system", "content": COMPRESS_RESEARCH_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Topic: {state.topic.title}\n\n"
                        f"Full research conversation:\n{conversation}"
                    ),
                },
            ]
        ),
    )
    return {"compressed": compressed}


def should_continue(
    state: ResearcherState,
) -> Literal["researcher_tools", "compress_research"]:
    last_message: AIMessage = cast(AIMessage, state.messages[-1])
    if last_message.tool_calls:
        return "researcher_tools"
    return "compress_research"


def build_researcher_subgraph() -> CompiledStateGraph:
    graph: StateGraph[ResearcherState] = StateGraph(ResearcherState)

    graph.add_node("researcher", researcher_node)
    graph.add_node("researcher_tools", researcher_tools_node)
    graph.add_node("compress_research", compress_research_node)

    graph.add_edge(START, "researcher")
    graph.add_conditional_edges("researcher", should_continue)
    graph.add_edge("researcher_tools", "researcher")
    graph.add_edge("compress_research", END)

    return graph.compile()
