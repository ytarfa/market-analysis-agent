from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    query: str = Field(..., description="The product or market to analyze")


class AnalyzeResponse(BaseModel):
    query: str
    response: str
