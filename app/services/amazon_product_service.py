# ruff: noqa: E501
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.config import settings
from app.services.serpapi_service import SerpapiService
from app.utils.cache import FileCache

ENGINE = "amazon_product"
DOMAIN = "amazon.ca"

AMAZON_PRODUCT_RESTRICTOR = [
    "product_results.{asin, title, brand, rating, reviews, extracted_price}",
    "reviews_information.summary.{text, customer_reviews}",
    "reviews_information.authors_reviews[].{title, text, rating, date, author, verified_purchase}",
]


class ProductInfo(BaseModel):
    asin: str
    title: str
    brand: str | None = None
    rating: float | None = None
    reviews: int | None = None
    price: float | None = Field(None, alias="extracted_price")

    model_config = {"populate_by_name": True}


class StarHistogram(BaseModel):
    five_star: int | None = None
    four_star: int | None = None
    three_star: int | None = None
    two_star: int | None = None
    one_star: int | None = None

    model_config = {
        "populate_by_name": True,
        "alias_generator": lambda field: {
            "five_star": "5 star",
            "four_star": "4 star",
            "three_star": "3 star",
            "two_star": "2 star",
            "one_star": "1 star",
        }.get(field, field),
    }


class AmazonAuthorReview(BaseModel):
    title: str | None = None
    text: str | None = None
    rating: float | None = None
    date: str | None = None
    author: str | None = None
    verified_purchase: bool | None = None


class AmazonReviewsInformation(BaseModel):
    summary_text: str | None = None
    customer_reviews: StarHistogram | None = None
    author_reviews: list[AmazonAuthorReview] | None = None

    @model_validator(mode="before")
    @classmethod
    def flatten(cls, data: dict[str, object]) -> dict[str, object]:
        summary = data.get("summary", {})
        return {
            "summary_text": summary.get("text"),  # type: ignore
            "customer_reviews": summary.get("customer_reviews"),  # type: ignore
            "author_reviews": data.get("authors_reviews"),
        }


class AmazonProductResponse(BaseModel):
    product_info: ProductInfo
    reviews_information: AmazonReviewsInformation | None = None

    @model_validator(mode="before")
    @classmethod
    def flatten(cls, data: dict[str, object]) -> dict[str, object]:
        return {
            "product_info": data.get("product_results"),
            "reviews_information": data.get("reviews_information"),
        }


class AmazonProductService(ABC):
    @abstractmethod
    def search_product(self, asin: str) -> AmazonProductResponse | None:
        pass


class SerpapiAmazonProductService(AmazonProductService, SerpapiService):
    def __init__(self) -> None:
        super().__init__()
        self._cache: FileCache = FileCache(namespace="amazon_products")

    def search_product(self, asin: str) -> AmazonProductResponse:
        cached: dict[str, Any] | None = self._cache.read(asin)
        if cached is not None:
            return AmazonProductResponse.model_validate(cached)
        results = self.search(
            engine=ENGINE,
            asin=asin,
            amazon_domain=DOMAIN,
            json_restrictor=",".join(AMAZON_PRODUCT_RESTRICTOR),
        )
        self._cache.write(asin, dict(results))
        return AmazonProductResponse.model_validate(results)


class MockAmazonProductService(AmazonProductService):
    def __init__(self) -> None:
        self._cache: FileCache = FileCache(namespace="amazon_products")

    def search_product(self, asin: str) -> AmazonProductResponse | None:
        cached: dict[str, Any] | None = self._cache.read(asin)
        if cached is None:
            return None
        return AmazonProductResponse.model_validate(cached)


def get_amazon_product_service() -> AmazonProductService:
    if settings.serpapi_api_key:
        return SerpapiAmazonProductService()
    return MockAmazonProductService()
