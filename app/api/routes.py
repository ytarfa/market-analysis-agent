from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage

from app.graph.graph import agent
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    try:
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=request.query)]}
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Agent call failed: {e}")

    last_message = result["messages"][-1]
    return AnalyzeResponse(query=request.query, response=last_message.content)
