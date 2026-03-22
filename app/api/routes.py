from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, HTTPException

from app.agent.analysis_pipeline import build_analysis_pipeline
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from app.schemas.research import CompressedResearch, ResearchBrief

router = APIRouter()

MARKDOWN_VIEWER_BASE = "https://markdownviewer.pages.dev"


def _build_report_url(report: str) -> str:
    cleaned = report.replace("\\n", "\n")
    return f"{MARKDOWN_VIEWER_BASE}?md={quote(cleaned, safe='')}"


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

    report: str = result.get("report", "")
    report_url = _build_report_url(report) if report else ""

    return AnalyzeResponse(
        query=request.query,
        brief=brief,
        research_results=research_results,
        report=report,
        report_url=report_url,
    )
