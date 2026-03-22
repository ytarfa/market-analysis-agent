import os

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    anthropic_api_key: str = Field(
        default=os.getenv("ANTHROPIC_API_KEY", ""), alias="ANTHROPIC_API_KEY"
    )
    tavily_api_key: str = Field(
        default=os.getenv("TAVILY_API_KEY", ""), alias="TAVILY_API_KEY"
    )
    model: str = Field(default="claude-sonnet-4-20250514", alias="MODEL")
    max_tokens: int = Field(default=1024, alias="MAX_TOKENS")

    model_config = {"env_file": ".env", "populate_by_name": True}


settings = Settings()
