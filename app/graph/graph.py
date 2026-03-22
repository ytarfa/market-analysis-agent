from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.pregel import Pregel

from app.graph.state import AgentState
from app.config import settings

SYSTEM_PROMPT = """You are a market analysis agent specializing in e-commerce intelligence.
When given a product or market query, provide a concise preliminary analysis covering:
- What the product/market is
- Key players and competitive landscape
- General pricing dynamics
- Customer perception signals
- Initial strategic observations

Be analytical, specific, and structured."""

llm = init_chat_model(
    model=settings.model,
    api_key=settings.anthropic_api_key,
    max_tokens=settings.max_tokens,
)


def analyst_node(state: AgentState) -> dict[str, list[BaseMessage]]:
    response = llm.invoke(
        [{"role": "system", "content": SYSTEM_PROMPT}, *state.messages]
    )
    return {"messages": [response]}


def build_graph() -> Pregel:
    graph = StateGraph(AgentState)

    graph.add_node("analyst", analyst_node)

    graph.add_edge(START, "analyst")
    graph.add_edge("analyst", END)

    return graph.compile()


agent = build_graph()