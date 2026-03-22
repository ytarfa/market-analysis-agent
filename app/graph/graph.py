from typing import Literal, cast

from langchain.chat_models import init_chat_model
from langchain.tools import BaseTool
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.config import settings
from app.graph.state import AgentState
from app.tools.fetch_reviews import fetch_reviews
from app.tools.web_search import web_search

SYSTEM_PROMPT = """
You are a market analysis agent specializing in e-commerce intelligence.
Always search for current data before responding — never rely on your training
knowledge alone.

When given a product or market query, provide a concise analysis covering:
- What the product/market is
- Key players and competitive landscape
- General pricing dynamics
- Customer perception signals
- Initial strategic observations

Be analytical, specific, and structured. Only report what you can back with data you
have gathered."""

llm = init_chat_model(
    model=settings.model,
    api_key=settings.anthropic_api_key,
    max_tokens=settings.max_tokens,
)

tools: list[BaseTool] = [web_search, fetch_reviews]
tools_by_name: dict[str, BaseTool] = {t.name: t for t in tools}
llm_with_tools = llm.bind_tools(tools)


def analyst_node(state: AgentState) -> dict[str, list[BaseMessage]]:
    response = llm_with_tools.invoke(
        [{"role": "system", "content": SYSTEM_PROMPT}, *state.messages]
    )
    return {"messages": [response]}


async def tool_node(state: AgentState) -> dict[str, list[ToolMessage]]:
    last_message: AIMessage = cast(AIMessage, state.messages[-1])
    results: list[ToolMessage] = []

    for tool_call in last_message.tool_calls:
        tool: BaseTool = tools_by_name[tool_call["name"]]
        observation: str = await tool.ainvoke(tool_call["args"])
        results.append(
            ToolMessage(content=str(observation), tool_call_id=tool_call["id"])
        )

    return {"messages": results}


async def should_continue(state: AgentState) -> Literal["tool_node", "__end__"]:
    last_message: AIMessage = cast(AIMessage, state.messages[-1])
    if last_message.tool_calls:
        return "tool_node"
    return "__end__"


def build_graph() -> CompiledStateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("analyst", analyst_node)
    graph.add_node("tool_node", tool_node)

    graph.add_edge(START, "analyst")
    graph.add_edge("tool_node", "analyst")
    graph.add_conditional_edges("analyst", should_continue)

    return graph.compile()


agent = build_graph()
