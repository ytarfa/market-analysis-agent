# ruff: noqa: E501
from enum import Enum

from pydantic import BaseModel, Field


class ResearchBrief(BaseModel):
    product_name: str = Field(
        description="Normalised product or market name (e.g. 'iPhone 16 Pro')."
    )
    market_category: str = Field(
        description="Broad market category (e.g. 'consumer electronics', 'athletic footwear')."
    )
    research_questions: list[str] = Field(
        description=(
            "Concrete research questions the analysis must answer. "
            "Include at least: competitive landscape, pricing dynamics, "
            "customer sentiment, and market trends."
        ),
        min_length=3,
    )
    target_audience: str = Field(
        default="business decision-maker",
        description="Intended reader of the final report.",
    )


class ToolHint(str, Enum):
    WEB_SEARCH = "web_search"
    FETCH_REVIEWS = "fetch_reviews"
    GOOGLE_TRENDS = "google_trends"


class ResearchTopic(BaseModel):
    title: str = Field(
        description="Short label for the topic (e.g. 'Pricing comparison').",
    )
    description: str = Field(
        description=(
            "What the researcher should investigate, detailed enough to "
            "guide tool usage and scoping."
        ),
    )
    tool_hints: list[ToolHint] = Field(
        default_factory=list,
        description=(
            "Suggested tools the researcher should prioritise. "
            "The researcher is free to use any available tool regardless."
        ),
    )


class ResearchPlan(BaseModel):
    topics: list[ResearchTopic] = Field(
        description="Research topics to assign to individual researcher agents.",
        min_length=1,
    )
    rationale: str = Field(
        default="",
        description="Brief explanation of why these topics were chosen.",
    )


class CompressedResearch(BaseModel):
    topic_title: str = Field(
        description="The topic this research addresses.",
    )
    summary: str = Field(
        description="2-4 paragraph summary of key findings.",
    )
    key_data_points: list[str] = Field(
        default_factory=list,
        description=("Specific facts, figures, or quotes extracted from tool results."),
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "Self-assessed confidence in the findings (0 = no data, 1 = strong)."
        ),
    )


class ResearchComplete(BaseModel):
    sufficient: bool = Field(
        description="True if research is adequate to write the final report.",
    )
    feedback: str = Field(
        default="",
        description=(
            "If not sufficient, describes what is missing so plan_research "
            "can fill the gaps on the next iteration."
        ),
    )
