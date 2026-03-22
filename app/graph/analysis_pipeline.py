from __future__ import annotations

from typing import Any, cast

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

from app.config import settings
from app.graph.analysis_pipeline_prompts import (
    FINAL_REPORT_PROMPT,
    GENERATE_BRIEF_PROMPT,
)
from app.graph.coordinator import build_research_coordinator
from app.schemas.research import CompressedResearch, ResearchBrief


class PipelineState(BaseModel):
    query: str = Field(
        description="Raw user query (e.g. 'iPhone 16 Pro').",
    )
    brief: ResearchBrief | None = Field(
        default=None,
        description="Structured brief derived from the raw query.",
    )
    research_results: list[CompressedResearch] = Field(
        default_factory=list,
        description="Compressed findings from every researcher agent.",
    )
    report: str = Field(
        default="",
        description="Final markdown report synthesised from all research.",
    )


_base_llm: BaseChatModel = init_chat_model(
    model=settings.model,
    api_key=settings.anthropic_api_key,
    max_tokens=settings.max_tokens,
)

_brief_llm = _base_llm.with_structured_output(ResearchBrief)

_coordinator_graph: CompiledStateGraph = build_research_coordinator()


def generate_brief_node(state: PipelineState) -> dict[str, ResearchBrief]:
    brief: ResearchBrief = cast(
        ResearchBrief,
        _brief_llm.invoke(
            [
                {"role": "system", "content": GENERATE_BRIEF_PROMPT},
                {"role": "user", "content": state.query},
            ]
        ),
    )
    return {"brief": brief}


async def research_coordinator_node(
    state: PipelineState,
) -> dict[str, list[CompressedResearch]]:
    brief: ResearchBrief | None = state.brief
    if brief is None:
        raise ValueError(
            "research_coordinator_node called without a brief. "
            "generate_brief must run first."
        )

    coordinator_input: dict[str, Any] = {
        "brief": brief.model_dump(),
    }

    coordinator_output: dict[str, Any] = await _coordinator_graph.ainvoke(
        coordinator_input
    )

    raw_results: list[Any] = coordinator_output.get("research_results", [])
    research_results: list[CompressedResearch] = [
        r if isinstance(r, CompressedResearch) else CompressedResearch.model_validate(r)
        for r in raw_results
    ]

    return {"research_results": research_results}


def final_report_node(state: PipelineState) -> dict[str, str]:
    brief: ResearchBrief | None = state.brief
    if brief is None:
        raise ValueError(
            "final_report_node called without a brief. generate_brief must run first."
        )

    research_context: str = "\n\n".join(
        f"## {r.topic_title}\n"
        f"{r.summary}\n\n"
        f"Key data points:\n"
        + "\n".join(f"- {dp}" for dp in r.key_data_points)
        + f"\n\nConfidence: {r.confidence:.0%}"
        for r in state.research_results
    )

    report: str = cast(
        str,
        _base_llm.invoke(
            [
                {"role": "system", "content": FINAL_REPORT_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"<brief>\n"
                        f"Product: {brief.product_name}\n"
                        f"Category: {brief.market_category}\n"
                        f"Audience: {brief.target_audience}\n"
                        f"Research questions:\n"
                        + "\n".join(f"- {q}" for q in brief.research_questions)
                        + f"\n</brief>\n\n"
                        f"<research>\n{research_context}\n</research>"
                    ),
                },
            ]
        ).content,
    )

    return {"report": report}


def build_analysis_pipeline() -> CompiledStateGraph:
    graph = StateGraph(PipelineState)

    graph.add_node("generate_brief", generate_brief_node)
    graph.add_node("research_coordinator", research_coordinator_node)
    graph.add_node("final_report", final_report_node)

    graph.add_edge(START, "generate_brief")
    graph.add_edge("generate_brief", "research_coordinator")
    graph.add_edge("research_coordinator", "final_report")
    graph.add_edge("final_report", END)

    return graph.compile()
