import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.agent.analysis_pipeline import build_analysis_pipeline
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from app.schemas.research import CompressedResearch, ResearchBrief

router = APIRouter()

REPORTS_DIR = Path("reports")


def _slugify(text: str, max_length: int = 80) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_]+", "_", slug).strip("_")
    return slug[:max_length]


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest, http_request: Request) -> AnalyzeResponse:
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
    report_filename: str | None = None
    report_url: str | None = None
    if report:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        report_filename = f"{_slugify(request.query)}_{timestamp}.md"
        path = REPORTS_DIR / report_filename
        path.write_text(report, encoding="utf-8")
        report_url = str(
            http_request.url_for("download_report", filename=report_filename)
        )

    return AnalyzeResponse(
        query=request.query,
        brief=brief,
        research_results=research_results,
        report=report,
        report_filename=report_filename,
        report_url=report_url,
    )


@router.get("/reports/{filename}")
async def download_report(filename: str) -> FileResponse:
    path = REPORTS_DIR / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Report '{filename}' not found")
    # Prevent path traversal
    if not path.resolve().is_relative_to(REPORTS_DIR.resolve()):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return FileResponse(
        path=str(path),
        media_type="text/markdown",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
