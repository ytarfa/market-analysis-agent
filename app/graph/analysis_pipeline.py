from typing import cast

from langchain.chat_models import init_chat_model
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

from app.config import settings
from app.graph.analysis_pipeline_prompts import GENERATE_BRIEF_PROMPT
from app.schemas.research import ResearchBrief


class PipelineState(BaseModel):
    query: str = Field(
        description="Raw user query (e.g. 'iPhone 16 Pro').",
    )

    brief: ResearchBrief | None = Field(
        default=None,
        description="Structured brief derived from the raw query.",
    )

    report: str = Field(
        default="",
        description="Final markdown report synthesised from all research.",
    )


brief_llm = init_chat_model(
    model=settings.model,
    api_key=settings.anthropic_api_key,
    max_tokens=settings.max_tokens,
).with_structured_output(ResearchBrief)


def generate_brief_node(state: PipelineState) -> dict[str, ResearchBrief]:
    brief = cast(
        ResearchBrief,
        brief_llm.invoke(
            [
                {"role": "system", "content": GENERATE_BRIEF_PROMPT},
                {"role": "user", "content": state.query},
            ]
        ),
    )
    return {"brief": brief}


def research_coordinator_node():
    pass


def final_report_node():
    pass


def build_analysis_pipeline_graph() -> CompiledStateGraph:
    graph = StateGraph(PipelineState)

    graph.add_node("generate_brief", generate_brief_node)
    graph.add_node("research_coordinator", research_coordinator_node)
    graph.add_node("final_report", final_report_node)

    graph.add_edge(START, "generate_brief")
    graph.add_edge("generate_brief", "research_coordinator")
    graph.add_edge("research_coordinator", "final_report")
    graph.add_edge("final_report", END)

    return graph.compile()


pipeline = build_analysis_pipeline_graph()
