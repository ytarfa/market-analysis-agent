import os

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Anthropic
    anthropic_api_key: str = Field(
        default=os.getenv("ANTHROPIC_API_KEY", ""), alias="ANTHROPIC_API_KEY"
    )
    # Tavily
    tavily_api_key: str = Field(
        default=os.getenv("TAVILY_API_KEY", ""), alias="TAVILY_API_KEY"
    )
    # Langsmith
    langsmith_endpoint: str = Field(
        default="https://api.smith.langchain.com", alias="LANGSMITH_ENDPOINT"
    )
    langsmith_api_key: str | None = Field(default=None, alias="LANGSMITH_API_KEY")
    langsmith_tracing: bool = Field(default=False, alias="LANGSMITH_TRACING")
    langsmith_project: str = Field(default="market-agent", alias="LANGSMITH_PROJECT")
    # SerpApi
    serpapi_api_key: str | None = Field(default=None, alias="SERPAPI_API_KEY")
    max_review_products: int = Field(default=5, alias="MAX_REVIEW_PRODUCTS")
    max_concurrent_researchers: int = Field(
        default=2, alias="MAX_CONCURRENT_RESEARCHERS"
    )

    # Models
    generate_brief_model: str = Field(
        default="claude-haiku-4-5-20251001", alias="GENERATE_BRIEF_MODEL"
    )
    generate_brief_temperature: float = Field(
        default=0.0, alias="GENERATE_BRIEF_TEMPERATURE"
    )

    plan_research_model: str = Field(
        default="claude-haiku-4-5-20251001", alias="PLAN_RESEARCH_MODEL"
    )
    plan_research_temperature: float = Field(
        default=0.0, alias="PLAN_RESEARCH_TEMPERATURE"
    )

    researcher_model: str = Field(
        default="claude-sonnet-4-20250514", alias="RESEARCHER_MODEL"
    )
    researcher_temperature: float = Field(default=0.0, alias="RESEARCHER_TEMPERATURE")
    researcher_max_tokens: int = Field(default=1024, alias="RESEARCHER_MAX_TOKENS")
    # Caps number of researcher ReAct loops
    researcher_max_iterations: int = Field(default=4, alias="RESEARCHER_MAX_ITERATIONS")

    compress_research_model: str = Field(
        default="claude-haiku-4-5-20251001", alias="COMPRESS_RESEARCH_MODEL"
    )
    compress_research_temperature: float = Field(
        default=0.0, alias="COMPRESS_RESEARCH_TEMPERATURE"
    )
    compress_research_retry_limit: int = Field(
        default=2, alias="COMPRESS_RESEARCH_RETRY_LIMIT"
    )

    evaluate_sufficiency_model: str = Field(
        default="claude-haiku-4-5-20251001", alias="EVALUATE_SUFFICIENCY_MODEL"
    )
    evaluate_sufficiency_temperature: float = Field(
        default=0.0, alias="EVALUATE_SUFFICIENCY_TEMPERATURE"
    )

    final_report_model: str = Field(
        default="claude-sonnet-4-20250514", alias="FINAL_REPORT_MODEL"
    )
    final_report_temperature: float = Field(
        default=0.5, alias="FINAL_REPORT_TEMPERATURE"
    )
    final_report_max_tokens: int = Field(default=8192, alias="FINAL_REPORT_MAX_TOKENS")

    model_config = {"env_file": ".env", "populate_by_name": True}

    def model_post_init(self, __context: object) -> None:
        if self.langsmith_api_key:
            os.environ["LANGSMITH_TRACING"] = str(self.langsmith_tracing).lower()
            os.environ["LANGSMITH_API_KEY"] = self.langsmith_api_key
            os.environ["LANGSMITH_PROJECT"] = self.langsmith_project


settings = Settings()
