# ruff: noqa: E501
from unittest.mock import MagicMock, patch

import pytest

from app.services.amazon_product_service import (
    AmazonProductResponse,
    AuthorReview,
    ProductInfo,
    ReviewsInformation,
    SerpapiAmazonProductService,
    StarHistogram,
)

MOCK_PRODUCT_RESPONSE: dict[str, object] = {
    "product_results": {
        "asin": "B0C4922P4M",
        "title": "Nike Womens Air Max Correlate Running Trainers 511417 Sneakers Shoes",
        "brand": "Brand: Nike",
        "rating": 4.4,
        "reviews": 1430,
        "extracted_price": 485.88,
    },
    "reviews_information": {
        "summary": {
            "text": "Customers find these shoes comfortable and supportive. They describe the shoes as good looking and mention they have a big mom vibe. Customers are happy with the color. However, opinions are mixed regarding the fit, quality, and size of the shoes.",
            "customer_reviews": {
                "5 star": 74,
                "4 star": 11,
                "3 star": 7,
                "2 star": 3,
                "1 star": 5,
            },
        },
        "authors_reviews": [
            {
                "title": "Good fit, good support, and nice colour combinations.",
                "text": "These are my go to shoes for walking on holidays. Good support and they never hurt my feet. I do a lot of walking so that is important.",
                "rating": 5.0,
                "date": "February 6, 2026",
                "author": "Margaret",
                "verified_purchase": True,
            },
            {
                "title": "Super comfortable and looks great",
                "text": "Great shoes, great price",
                "rating": 5.0,
                "date": "October 20, 2025",
                "author": "paul c.",
                "verified_purchase": True,
            },
            {
                "title": "Robuste",
                "text": "Tr\u00e8s belle , bonne taille et super confortable . Arriv\u00e9 dans sa boite Nike .",
                "rating": 5.0,
                "date": "August 25, 2025",
                "author": "Claudine Carrier",
                "verified_purchase": True,
            },
            {
                "title": "Nice shoes",
                "text": "Fit true to size, beautiful shoes. Only giving 4 stars because they came a little later than they said they would. They were delayed awhile, but did come!",
                "rating": 4.0,
                "date": "December 16, 2025",
                "author": "Cassia Davy",
                "verified_purchase": True,
            },
            {
                "title": "Love these!!",
                "text": "Fit great and super comfy!! Absolutely love the colours!",
                "rating": 5.0,
                "date": "January 29, 2026",
                "author": "Ken",
                "verified_purchase": True,
            },
            {
                "title": "Don\u2019t question, just buy them!",
                "text": "Sizing is perfect, great condition, super comfortable!",
                "rating": 5.0,
                "date": "March 5, 2026",
                "author": "Amazon Customer",
                "verified_purchase": True,
            },
            {
                "title": "Run small l, colour may be different but super cute!!!",
                "text": "I'll start by saying these shoes are so sharp. Honestly, great looking sneakers. If that is all you are looking for then these are for you.I will be returning mine unfortunately.Reasons:They fit small. I am usually an 8.5 to 9 depending on the shoe. I ordered a 9 and they fit but my foot felt crammed in. The width was not a comfortable wide for me. They could be good with a narrower foot but go a half size up for sure.Colour was not quite as pictured. The colour was more purple than the burgundy as pictured. Still nice but not what I expected.These could be comfy if I went a half size up but not for exercise. They are very bulky in the back and didn't feel stable for anything more than walking.All in all, very attractive shoe. Comfy for minimal exercise, great looking everyday sneaker, not for the gym or a run etcThey just were not for me and for what I was looking for. Honestly, I would have kept them just for a stylish running shoe and for everyday wear but my budget was for something I could work out in and these just aren't it.",
                "rating": 3.0,
                "date": "January 21, 2026",
                "author": "stephanie loreto",
                "verified_purchase": True,
            },
            {
                "title": "Fits well looking good",
                "text": "Am loving it very comfortable",
                "rating": 5.0,
                "date": "February 1, 2026",
                "author": "Amazon Customer",
                "verified_purchase": True,
            },
        ],
    },
}


@pytest.fixture
def service() -> SerpapiAmazonProductService:
    with patch.object(SerpapiAmazonProductService, "__init__", return_value=None):
        instance = SerpapiAmazonProductService()
        instance.client = MagicMock()
        return instance


def test_search_product_returns_amazon_product_response(
    service: SerpapiAmazonProductService,
) -> None:
    service.client.search = MagicMock(return_value=MOCK_PRODUCT_RESPONSE)

    result: AmazonProductResponse = service.search_product("B0C4922P4M")

    assert isinstance(result, AmazonProductResponse)
    assert isinstance(result.product_info, ProductInfo)
    assert isinstance(result.reviews_information, ReviewsInformation)


def test_search_product_maps_product_info_correctly(
    service: SerpapiAmazonProductService,
) -> None:
    service.client.search = MagicMock(return_value=MOCK_PRODUCT_RESPONSE)

    result: AmazonProductResponse = service.search_product("B0C4922P4M")

    assert result.product_info.asin == "B0C4922P4M"
    assert (
        result.product_info.title
        == "Nike Womens Air Max Correlate Running Trainers 511417 Sneakers Shoes"
    )
    assert result.product_info.brand == "Brand: Nike"
    assert result.product_info.rating == 4.4
    assert result.product_info.reviews == 1430
    assert result.product_info.price == 485.88


def test_search_product_maps_review_summary_correctly(
    service: SerpapiAmazonProductService,
) -> None:
    service.client.search = MagicMock(return_value=MOCK_PRODUCT_RESPONSE)

    result: AmazonProductResponse = service.search_product("B0C4922P4M")
    reviews: ReviewsInformation = result.reviews_information  # type: ignore[assignment]

    assert reviews.summary_text is not None
    assert "comfortable and supportive" in reviews.summary_text


def test_search_product_maps_star_histogram_correctly(
    service: SerpapiAmazonProductService,
) -> None:
    service.client.search = MagicMock(return_value=MOCK_PRODUCT_RESPONSE)

    result: AmazonProductResponse = service.search_product("B0C4922P4M")
    histogram: StarHistogram = result.reviews_information.customer_reviews  # type: ignore[union-attr, assignment]

    assert histogram.five_star == 74
    assert histogram.four_star == 11
    assert histogram.three_star == 7
    assert histogram.two_star == 3
    assert histogram.one_star == 5


def test_search_product_maps_author_reviews_correctly(
    service: SerpapiAmazonProductService,
) -> None:
    service.client.search = MagicMock(return_value=MOCK_PRODUCT_RESPONSE)

    result: AmazonProductResponse = service.search_product("B0C4922P4M")
    author_reviews: list[AuthorReview] = result.reviews_information.author_reviews  # type: ignore[union-attr, assignment]

    assert len(author_reviews) == 8
    assert all(isinstance(r, AuthorReview) for r in author_reviews)

    first_review: AuthorReview = author_reviews[0]
    assert first_review.title == "Good fit, good support, and nice colour combinations."
    assert first_review.rating == 5.0
    assert first_review.author == "Margaret"
    assert first_review.verified_purchase is True


def test_search_product_raises_on_missing_product_results(
    service: SerpapiAmazonProductService,
) -> None:
    service.client.search = MagicMock(
        return_value={
            "reviews_information": MOCK_PRODUCT_RESPONSE["reviews_information"]
        }
    )

    with pytest.raises(Exception):
        service.search_product("B0C4922P4M")


def test_search_product_raises_on_invalid_product_schema(
    service: SerpapiAmazonProductService,
) -> None:
    service.client.search = MagicMock(
        return_value={"product_results": {"bad_field": "no_asin"}}
    )

    with pytest.raises(Exception):
        service.search_product("B0C4922P4M")


def test_search_product_handles_missing_reviews_information(
    service: SerpapiAmazonProductService,
) -> None:
    service.client.search = MagicMock(
        return_value={
            "product_results": MOCK_PRODUCT_RESPONSE["product_results"],
        }
    )

    result: AmazonProductResponse = service.search_product("B0C4922P4M")

    assert result.product_info.asin == "B0C4922P4M"
    assert result.reviews_information is None
