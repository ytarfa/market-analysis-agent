from typing import Any

from fastapi import APIRouter, HTTPException

from app.graph.analysis_pipeline import build_analysis_pipeline
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from app.schemas.research import CompressedResearch, ResearchBrief

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    pipeline = build_analysis_pipeline()
    try:
        result: dict[str, Any] = await pipeline.ainvoke({"query": request.query})
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Pipeline failed: {e}")

    brief: ResearchBrief | None = result.get("brief")
    if brief and not isinstance(brief, ResearchBrief):
        brief = ResearchBrief.model_validate(brief)

    raw_results: list[Any] = result.get("research_results", [])
    research_results: list[CompressedResearch] = [
        r if isinstance(r, CompressedResearch) else CompressedResearch.model_validate(r)
        for r in raw_results
    ]

    return AnalyzeResponse(
        query=request.query,
        brief=brief,
        research_results=research_results,
        report=result.get("report", ""),
    )
