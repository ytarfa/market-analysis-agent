from pydantic import BaseModel, Field


class ResearchBrief(BaseModel):
    """Structured brief produced by the generate_brief node."""

    product_name: str = Field(
        description="Normalised product or market name (e.g. 'iPhone 16 Pro')."
    )
    market_category: str = Field(
        description="Broad market category (e.g. 'consumer electronics', 'athletic footwear')."  # noqa: E501
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
