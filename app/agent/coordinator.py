import asyncio
from typing import Literal, cast

from langchain.chat_models import init_chat_model
from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

from app.agent.coordinator_prompts import (
    EVALUATE_SUFFICIENCY_PROMPT,
    PLAN_RESEARCH_PROMPT,
)
from app.agent.researcher import build_researcher_subgraph
from app.config import settings
from app.schemas.research import (
    CompressedResearch,
    ResearchBrief,
    ResearchComplete,
    ResearchPlan,
    ResearchTopic,
)


class CoordinatorState(BaseModel):
    brief: ResearchBrief = Field(
        description="The research brief to decompose into topics.",
    )
    plan: ResearchPlan | None = Field(
        default=None,
        description="Current research plan (topics to investigate).",
    )
    research_results: list[CompressedResearch] = Field(
        default_factory=list,
        description="Accumulated compressed findings from all researchers.",
    )
    sufficiency: ResearchComplete | None = Field(
        default=None,
        description="Latest sufficiency judgment from the evaluator.",
    )
    iteration: int = Field(
        default=0,
        description="How many plan → research → evaluate cycles have run.",
    )
    max_iterations: int = Field(
        default=2,
        description="Safety cap to prevent infinite loops.",
    )


_plan_llm = init_chat_model(
    model=settings.plan_research_model,
    temperature=settings.plan_research_temperature,
    api_key=settings.anthropic_api_key,
).with_structured_output(ResearchPlan)

_sufficiency_llm = init_chat_model(
    model=settings.evaluate_sufficiency_model,
    temperature=settings.evaluate_sufficiency_temperature,
    api_key=settings.anthropic_api_key,
).with_structured_output(ResearchComplete)

_researcher_graph = build_researcher_subgraph()

_MAX_RETRIES = 3
_BASE_DELAY = 10.0


def plan_research_node(
    state: CoordinatorState,
) -> dict[str, ResearchPlan | int]:

    user_content: str = f"Research brief:\n{state.brief.model_dump_json(indent=2)}"
    if state.sufficiency and state.sufficiency.feedback:
        user_content += (
            f"\n\nPrevious research was insufficient. "
            f"Feedback:\n{state.sufficiency.feedback}"
        )
    if state.research_results:
        covered: str = ", ".join(r.topic_title for r in state.research_results)
        user_content += f"\n\nTopics already covered: {covered}"

    plan: ResearchPlan = cast(
        ResearchPlan,
        _plan_llm.invoke(
            [
                {"role": "system", "content": PLAN_RESEARCH_PROMPT},
                {"role": "user", "content": user_content},
            ]
        ),
    )
    return {"plan": plan, "iteration": state.iteration + 1}


def _parse_researcher_output(
    topic: ResearchTopic,
    researcher_output: dict,
) -> CompressedResearch:
    compressed_data = researcher_output.get("compressed")
    if compressed_data:
        if isinstance(compressed_data, CompressedResearch):
            return compressed_data
        return CompressedResearch.model_validate(compressed_data)
    return CompressedResearch(
        topic_title=topic.title,
        summary=f"Research on '{topic.title}' did not produce results.",
        key_data_points=[],
        confidence=0.0,
    )


async def _invoke_researcher_with_retry(
    topic: ResearchTopic,
    semaphore: asyncio.Semaphore,
) -> dict:
    async with semaphore:
        for attempt in range(_MAX_RETRIES):
            try:
                return await _researcher_graph.ainvoke({"topic": topic.model_dump()})
            except Exception as exc:
                if "rate_limit" in str(exc).lower() or "429" in str(exc):
                    delay = _BASE_DELAY * (2**attempt)
                    await asyncio.sleep(delay)
                else:
                    raise
        # Final attempt — let the exception propagate if it still fails
        return await _researcher_graph.ainvoke({"topic": topic.model_dump()})


async def spawn_researchers_node(
    state: CoordinatorState,
) -> dict[str, list[CompressedResearch]]:
    plan: ResearchPlan | None = state.plan
    if not plan:
        return {"research_results": state.research_results}

    semaphore = asyncio.Semaphore(settings.max_concurrent_researchers)

    researcher_outputs = await asyncio.gather(
        *(_invoke_researcher_with_retry(topic, semaphore) for topic in plan.topics)
    )

    new_results: list[CompressedResearch] = [
        _parse_researcher_output(topic, output)
        for topic, output in zip(plan.topics, researcher_outputs)
    ]

    return {"research_results": state.research_results + new_results}


def evaluate_sufficiency_node(
    state: CoordinatorState,
) -> dict[str, ResearchComplete]:
    results_summary: str = "\n\n".join(
        f"### {r.topic_title}\n{r.summary}\nConfidence: {r.confidence:.0%}"
        for r in state.research_results
    )

    user_content: str = (
        f"Research brief:\n{state.brief.model_dump_json(indent=2)}\n\n"
        f"Research collected so far:\n{results_summary}"
    )

    sufficiency: ResearchComplete = cast(
        ResearchComplete,
        _sufficiency_llm.invoke(
            [
                {"role": "system", "content": EVALUATE_SUFFICIENCY_PROMPT},
                {"role": "user", "content": user_content},
            ]
        ),
    )
    return {"sufficiency": sufficiency}


def should_loop(
    state: CoordinatorState,
) -> Literal["plan_research", "__end__"]:
    sufficiency: ResearchComplete | None = state.sufficiency

    if sufficiency and sufficiency.sufficient:
        return "__end__"

    if state.iteration >= state.max_iterations:
        return "__end__"

    return "plan_research"


def build_research_coordinator() -> CompiledStateGraph:
    graph: StateGraph[CoordinatorState] = StateGraph(CoordinatorState)

    graph.add_node("plan_research", plan_research_node)
    graph.add_node("spawn_researchers", spawn_researchers_node)
    graph.add_node("evaluate_sufficiency", evaluate_sufficiency_node)

    graph.add_edge(START, "plan_research")
    graph.add_edge("plan_research", "spawn_researchers")
    graph.add_edge("spawn_researchers", "evaluate_sufficiency")
    graph.add_conditional_edges("evaluate_sufficiency", should_loop)

    return graph.compile()
