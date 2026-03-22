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
    # Model config
    model: str = Field(default="claude-sonnet-4-20250514", alias="MODEL")
    max_tokens: int = Field(default=1024, alias="MAX_TOKENS")

    model_config = {"env_file": ".env", "populate_by_name": True}

    def model_post_init(self, __context: object) -> None:
        if self.langsmith_api_key:
            os.environ["LANGSMITH_TRACING"] = str(self.langsmith_tracing).lower()
            os.environ["LANGSMITH_API_KEY"] = self.langsmith_api_key
            os.environ["LANGSMITH_PROJECT"] = self.langsmith_project


settings = Settings()
