# ruff: noqa: E501
from abc import ABC, abstractmethod

from langchain.tools import tool
from pydantic import BaseModel

from app.config import settings
from app.services.amazon_product_service import (
    AmazonAuthorReview,
    AmazonProductResponse,
    AmazonProductService,
    get_amazon_product_service,
)
from app.services.amazon_search_service import (
    AmazonSearchService,
    get_amazon_search_service,
)


class Review(BaseModel):
    title: str
    author: str
    text: str
    source: str
    rating: float


class FetchReviewStrategy(ABC):
    @abstractmethod
    def fetch_reviews(self, query: str) -> list[Review]:
        pass


class AmazonFetchReviewStrategy(FetchReviewStrategy):
    amazon_search_service: AmazonSearchService
    amazon_product_service: AmazonProductService

    def __init__(self) -> None:
        self.amazon_search_service = get_amazon_search_service()
        self.amazon_product_service = get_amazon_product_service()

    def fetch_reviews(self, query: str) -> list[Review]:
        max_products = settings.max_review_products
        search_results = self.amazon_search_service.search_product(query)
        if not search_results:
            return []
        asins: list[str] = [r.asin for r in search_results[:max_products]]

        reviews: list[Review] = []
        for asin in asins:
            try:
                reviews.extend(self._reviews_for_asin(asin))
            except Exception:
                print("Failed to fetch reviews for ASIN=%s", asin)
                continue
        return reviews

    def _reviews_for_asin(self, asin: str) -> list[Review]:
        response: AmazonProductResponse | None = (
            self.amazon_product_service.search_product(asin)
        )

        if not response or not response.reviews_information:
            return []

        author_reviews: list[AmazonAuthorReview] | None = (
            response.reviews_information.author_reviews
        )
        if not author_reviews:
            return []

        return [
            Review(
                title=r.title or "",
                text=r.text,
                rating=r.rating,
                author=r.author or "",
                source="amazon",
            )
            for r in author_reviews
            if r.text and r.rating
        ]


FETCH_REVIEW_STRATEGY_LIST: list[FetchReviewStrategy] = [AmazonFetchReviewStrategy()]


@tool
def fetch_reviews(query: str) -> list[Review]:
    """Collect customer reviews and ratings for a product from e-commerce platforms.

    Use this tool when you need real customer feedback, sentiment data, or product ratings
    to inform your market analysis. Returns structured reviews including title, text, rating,
    author, and source platform.

    Currently sources reviews from Amazon. Results may vary in volume depending on product
    availability and listing coverage.

    Args:
        query: Product name or search terms (e.g. "iPhone 16 Pro", "Nike Air Max 90")
    """
    reviews = []
    for strategy in FETCH_REVIEW_STRATEGY_LIST:
        try:
            result = strategy.fetch_reviews(query)
            reviews.extend(result)
        except Exception:
            print("Strategy %s failed for query=%s", type(strategy).__name__, query)
            continue

    return reviews
