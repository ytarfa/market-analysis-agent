from typing import Any

from serpapi import Client, SerpResults

from app.config import settings


class SerpapiService:
    client: Client

    def __init__(self) -> None:
        if not settings.serpapi_api_key:
            raise ValueError("SERPAPI_API_KEY is not set")
        self.client = Client(api_key=settings.serpapi_api_key)

    def search(self, engine: str, query: str, **kwargs: Any) -> SerpResults:
        return self.client.search({"engine": engine, "k": query, **kwargs})
