from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from app.config import settings
from app.services.serpapi_service import SerpapiService
from app.utils.cache import FileCache

DOMAIN = "amazon.ca"
ENGINE = "amazon"


class AmazonSearchResult(BaseModel):
    position: int
    asin: str
    title: str


class AmazonSearchService(ABC):
    @abstractmethod
    def search_product(self, product_name: str) -> list[AmazonSearchResult]:
        pass


class SerpApiAmazonSearchService(AmazonSearchService, SerpapiService):
    def __init__(self) -> None:
        super().__init__()
        self._cache: FileCache = FileCache(namespace="amazon_search")

    def search_product(self, product_name: str) -> list[AmazonSearchResult]:
        cached: dict[str, Any] | None = self._cache.read(product_name)
        if cached is not None:
            return [
                AmazonSearchResult.model_validate(r) for r in cached["organic_results"]
            ]

        results = self.search(engine=ENGINE, k=product_name, amazon_domain=DOMAIN)
        self._cache.write(product_name, dict(results))
        organic_results: list[dict[str, Any]] = results["organic_results"]
        return [AmazonSearchResult.model_validate(r) for r in organic_results]


class MockAmazonSearchService(AmazonSearchService):
    def __init__(self) -> None:
        self._cache: FileCache = FileCache(namespace="amazon_search")

    def search_product(self, product_name: str) -> list[AmazonSearchResult]:
        cached: dict[str, Any] | None = self._cache.read(product_name)
        if cached is None:
            raise ValueError(
                f"No cached data for {product_name!r}. "
                "Run with a real API key first to populate the cache."
            )
        return [AmazonSearchResult.model_validate(r) for r in cached["organic_results"]]


def get_amazon_search_service() -> AmazonSearchService:
    if settings.serpapi_api_key:
        return SerpApiAmazonSearchService()
    return MockAmazonSearchService()
