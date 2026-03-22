from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from app.services.serpapi_service import SerpapiService

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

    def search_product(self, product_name: str) -> list[AmazonSearchResult]:
        results = self.search(engine=ENGINE, k=product_name, amazon_domain=DOMAIN)
        organic_results: list[dict[str, Any]] = results["organic_results"]
        return [AmazonSearchResult.model_validate(r) for r in organic_results]


class MockAmazonSearchService(AmazonSearchService):
    pass
