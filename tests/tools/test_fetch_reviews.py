from unittest.mock import MagicMock, patch

import pytest

from app.services.amazon_product_service import (
    AmazonAuthorReview,
    AmazonProductResponse,
    AmazonProductService,
    AmazonReviewsInformation,
)
from app.services.amazon_search_service import (
    AmazonSearchResult,
    AmazonSearchService,
)
from app.tools.fetch_reviews import (
    AmazonFetchReviewStrategy,
    FetchReviewStrategy,
    Review,
    fetch_reviews,
)


def _make_review(
    *,
    title: str = "Great",
    author: str = "Alice",
    text: str = "Loved it",
    source: str = "stub",
    rating: float = 5.0,
) -> Review:
    return Review(
        title=title,
        author=author,
        text=text,
        source=source,
        rating=rating,
    )


def _make_amazon_author_review(
    *,
    title: str | None = "Nice product",
    author: str | None = "Bob",
    text: str | None = "Works great",
    rating: float | None = 4.5,
) -> AmazonAuthorReview:
    review = MagicMock(spec=AmazonAuthorReview)
    review.title = title
    review.author = author
    review.text = text
    review.rating = rating
    return review


class _StubStrategy(FetchReviewStrategy):
    """A trivial strategy that returns a fixed list of reviews."""

    def __init__(self, reviews: list[Review]) -> None:
        self._reviews = reviews

    def fetch_reviews(self, query: str) -> list[Review]:
        return self._reviews


def _mock_amazon_search(mock_get_search: MagicMock, asins: list[str]) -> None:
    results: list[MagicMock] = []
    for asin in asins:
        r = MagicMock(spec=AmazonSearchResult)
        r.asin = asin
        results.append(r)
    mock_search_svc = MagicMock(spec=AmazonSearchService)
    mock_search_svc.search_product.return_value = results
    mock_get_search.return_value = mock_search_svc


def _mock_amazon_product(
    mock_get_product: MagicMock,
    author_reviews: list[AmazonAuthorReview] | None,
    *,
    has_reviews_info: bool = True,
) -> None:
    if has_reviews_info:
        reviews_info = MagicMock(spec=AmazonReviewsInformation)
        reviews_info.author_reviews = author_reviews
    else:
        reviews_info = None

    product_response = MagicMock(spec=AmazonProductResponse)
    product_response.reviews_information = reviews_info

    mock_product_svc = MagicMock(spec=AmazonProductService)
    mock_product_svc.search_product.return_value = product_response
    mock_get_product.return_value = mock_product_svc


@patch("app.tools.fetch_reviews.FETCH_REVIEW_STRATEGY_LIST")
def test_fetch_reviews_calls_every_strategy(mock_strategy_list: MagicMock) -> None:
    strategy_a = MagicMock(spec=FetchReviewStrategy)
    strategy_b = MagicMock(spec=FetchReviewStrategy)
    strategy_a.fetch_reviews.return_value = []
    strategy_b.fetch_reviews.return_value = []

    mock_strategy_list.__iter__ = MagicMock(return_value=iter([strategy_a, strategy_b]))

    fetch_reviews.invoke("headphones")

    strategy_a.fetch_reviews.assert_called_once_with("headphones")
    strategy_b.fetch_reviews.assert_called_once_with("headphones")


@patch("app.tools.fetch_reviews.FETCH_REVIEW_STRATEGY_LIST")
def test_fetch_reviews_combines_results(mock_strategy_list: MagicMock) -> None:
    reviews_a: list[Review] = [_make_review(title="A1"), _make_review(title="A2")]
    reviews_b: list[Review] = [_make_review(title="B1")]

    mock_strategy_list.__iter__ = MagicMock(
        return_value=iter([_StubStrategy(reviews_a), _StubStrategy(reviews_b)])
    )

    result: list[Review] = fetch_reviews.invoke("keyboard")

    assert len(result) == 3
    assert [r.title for r in result] == ["A1", "A2", "B1"]


@patch("app.tools.fetch_reviews.FETCH_REVIEW_STRATEGY_LIST")
def test_fetch_reviews_empty_when_no_reviews(mock_strategy_list: MagicMock) -> None:
    mock_strategy_list.__iter__ = MagicMock(
        return_value=iter([_StubStrategy([]), _StubStrategy([])])
    )

    result: list[Review] = fetch_reviews.invoke("nonexistent")

    assert result == []


@patch("app.tools.fetch_reviews.get_amazon_product_service")
@patch("app.tools.fetch_reviews.get_amazon_search_service")
def test_amazon_strategy_transforms_reviews(
    mock_get_search: MagicMock,
    mock_get_product: MagicMock,
) -> None:
    _mock_amazon_search(mock_get_search, ["B00TEST123"])
    _mock_amazon_product(
        mock_get_product,
        [
            _make_amazon_author_review(
                title="Excellent",
                author="Charlie",
                text="Best purchase ever",
                rating=5.0,
            )
        ],
    )

    strategy = AmazonFetchReviewStrategy()
    result: list[Review] = strategy.fetch_reviews("wireless earbuds")

    assert len(result) == 1
    review: Review = result[0]
    assert review.title == "Excellent"
    assert review.author == "Charlie"
    assert review.text == "Best purchase ever"
    assert review.rating == 5.0
    assert review.source == "amazon"


@patch("app.tools.fetch_reviews.get_amazon_product_service")
@patch("app.tools.fetch_reviews.get_amazon_search_service")
def test_amazon_strategy_skips_reviews_missing_text_or_rating(
    mock_get_search: MagicMock,
    mock_get_product: MagicMock,
) -> None:
    _mock_amazon_search(mock_get_search, ["B00NOTEXT"])
    _mock_amazon_product(
        mock_get_product,
        [
            _make_amazon_author_review(text=None, rating=3.0),
            _make_amazon_author_review(text="OK", rating=None),
            _make_amazon_author_review(text="Good", rating=4.0),
        ],
    )

    strategy = AmazonFetchReviewStrategy()
    result: list[Review] = strategy.fetch_reviews("mouse")

    assert len(result) == 1
    assert result[0].text == "Good"


@patch("app.tools.fetch_reviews.get_amazon_product_service")
@patch("app.tools.fetch_reviews.get_amazon_search_service")
def test_amazon_strategy_defaults_none_title_and_author_to_empty(
    mock_get_search: MagicMock,
    mock_get_product: MagicMock,
) -> None:
    _mock_amazon_search(mock_get_search, ["B00NONE"])
    _mock_amazon_product(
        mock_get_product,
        [
            _make_amazon_author_review(
                title=None, author=None, text="Decent", rating=3.5
            )
        ],
    )

    strategy = AmazonFetchReviewStrategy()
    result: list[Review] = strategy.fetch_reviews("tablet")

    assert len(result) == 1
    assert result[0].title == ""
    assert result[0].author == ""


@patch("app.tools.fetch_reviews.get_amazon_product_service")
@patch("app.tools.fetch_reviews.get_amazon_search_service")
def test_amazon_strategy_propagates_search_service_error(
    mock_get_search: MagicMock,
    mock_get_product: MagicMock,
) -> None:
    mock_search_svc = MagicMock(spec=AmazonSearchService)
    mock_search_svc.search_product.side_effect = ConnectionError("Amazon unreachable")
    mock_get_search.return_value = mock_search_svc
    mock_get_product.return_value = MagicMock(spec=AmazonProductService)

    strategy = AmazonFetchReviewStrategy()

    with pytest.raises(ConnectionError, match="Amazon unreachable"):
        strategy.fetch_reviews("laptop")


@patch("app.tools.fetch_reviews.get_amazon_product_service")
@patch("app.tools.fetch_reviews.get_amazon_search_service")
def test_amazon_strategy_skips_failed_asin_and_returns_partial(
    mock_get_search: MagicMock,
    mock_get_product: MagicMock,
) -> None:
    _mock_amazon_search(mock_get_search, ["B00OK", "B00BAD"])

    good_review = _make_amazon_author_review(text="Solid", rating=4.0)
    good_info = MagicMock(spec=AmazonReviewsInformation)
    good_info.author_reviews = [good_review]
    good_response = MagicMock(spec=AmazonProductResponse)
    good_response.reviews_information = good_info

    mock_product_svc = MagicMock(spec=AmazonProductService)
    mock_product_svc.search_product.side_effect = [
        good_response,
        TimeoutError("Request timed out"),
    ]
    mock_get_product.return_value = mock_product_svc

    strategy = AmazonFetchReviewStrategy()
    result: list[Review] = strategy.fetch_reviews("monitor")

    assert len(result) == 1
    assert result[0].text == "Solid"


@patch("app.tools.fetch_reviews.get_amazon_product_service")
@patch("app.tools.fetch_reviews.get_amazon_search_service")
def test_amazon_strategy_returns_empty_when_no_reviews_information(
    mock_get_search: MagicMock,
    mock_get_product: MagicMock,
) -> None:
    _mock_amazon_search(mock_get_search, ["B00EMPTY"])
    _mock_amazon_product(mock_get_product, None, has_reviews_info=False)

    strategy = AmazonFetchReviewStrategy()
    result: list[Review] = strategy.fetch_reviews("obscure gadget")

    assert result == []


@patch("app.tools.fetch_reviews.get_amazon_product_service")
@patch("app.tools.fetch_reviews.get_amazon_search_service")
def test_amazon_strategy_returns_empty_when_author_reviews_is_none(
    mock_get_search: MagicMock,
    mock_get_product: MagicMock,
) -> None:
    _mock_amazon_search(mock_get_search, ["B00NONEREV"])
    _mock_amazon_product(mock_get_product, None)

    strategy = AmazonFetchReviewStrategy()
    result: list[Review] = strategy.fetch_reviews("niche product")

    assert result == []


@patch("app.tools.fetch_reviews.get_amazon_product_service")
@patch("app.tools.fetch_reviews.get_amazon_search_service")
def test_amazon_strategy_returns_empty_when_search_finds_nothing(
    mock_get_search: MagicMock,
    mock_get_product: MagicMock,
) -> None:
    _mock_amazon_search(mock_get_search, [])
    mock_get_product.return_value = MagicMock(spec=AmazonProductService)

    strategy = AmazonFetchReviewStrategy()
    result: list[Review] = strategy.fetch_reviews("nonexistent product")

    assert result == []


@patch("app.tools.fetch_reviews.FETCH_REVIEW_STRATEGY_LIST")
def test_fetch_reviews_skips_failed_strategy_and_returns_partial(
    mock_strategy_list: MagicMock,
) -> None:
    good_strategy = MagicMock(spec=FetchReviewStrategy)
    good_strategy.fetch_reviews.return_value = [_make_review(title="Survived")]

    failing_strategy = MagicMock(spec=FetchReviewStrategy)
    failing_strategy.fetch_reviews.side_effect = RuntimeError("boom")

    mock_strategy_list.__iter__ = MagicMock(
        return_value=iter([failing_strategy, good_strategy])
    )

    result: list[Review] = fetch_reviews.invoke("anything")

    assert len(result) == 1
    assert result[0].title == "Survived"
