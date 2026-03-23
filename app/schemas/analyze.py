from pydantic import BaseModel, Field

from app.schemas.research import CompressedResearch, ResearchBrief


class AnalyzeRequest(BaseModel):
    query: str = Field(..., description="The product or market to analyze")


class AnalyzeResponse(BaseModel):
    query: str
    brief: ResearchBrief | None = None
    research_results: list[CompressedResearch] = Field(default_factory=list)
    report: str = ""
    report_filename: str | None = None
    report_url: str | None = None
