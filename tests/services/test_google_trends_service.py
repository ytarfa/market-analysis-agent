# ruff: noqa: E501
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from app.services.google_trends_service import (
    GoogleTrendsResponse,
    MockGoogleTrendsService,
    SerpapiGoogleTrendsService,
    get_google_trends_service,
)

MOCK_TIMESERIES_RESULT = {
    "interest_over_time": {
        "timeline_data": [
            {
                "date": "Dec 29 – Jan 4, 2019",
                "timestamp": "1546128000",
                "values": [
                    {"query": "electric bike", "value": "61", "extracted_value": 61}
                ],
            },
            {
                "date": "Jan 5 – 11, 2020",
                "timestamp": "1578182400",
                "values": [
                    {"query": "electric bike", "value": "75", "extracted_value": 75}
                ],
            },
        ],
        "averages": [68],
    }
}

MOCK_RELATED_TOPICS_RESULT = {
    "related_topics": {
        "rising": [
            {
                "topic": {"value": "/m/0257_98", "title": "E-bike", "type": "Topic"},
                "value": "Breakout",
                "extracted_value": 0,
                "link": "https://trends.google.com/trends/explore?q=%2Fm%2F0257_98&date=today+5-y",
            }
        ],
        "top": [
            {
                "topic": {"value": "/m/0257_98", "title": "E-bike", "type": "Topic"},
                "value": "100",
                "extracted_value": 100,
                "link": "https://trends.google.com/trends/explore?q=%2Fm%2F0257_98&date=today+5-y",
            }
        ],
    }
}

MOCK_RELATED_QUERIES_RESULT = {
    "related_queries": {
        "rising": [
            {
                "query": "best electric bike",
                "value": "Breakout",
                "extracted_value": 0,
                "link": "https://trends.google.com/trends/explore?q=best+electric+bike&date=today+5-y",
            }
        ],
        "top": [
            {
                "query": "electric bicycle",
                "value": "100",
                "extracted_value": 100,
                "link": "https://trends.google.com/trends/explore?q=electric+bicycle&date=today+5-y",
            }
        ],
    }
}

MOCK_CACHED_RAW = {
    "query": "electric bike",
    "date": "today 5-y",
    "_timeseries": MOCK_TIMESERIES_RESULT,
    "_related_topics": MOCK_RELATED_TOPICS_RESULT,
    "_related_queries": MOCK_RELATED_QUERIES_RESULT,
}


@pytest.fixture
def service() -> SerpapiGoogleTrendsService:
    with patch.object(SerpapiGoogleTrendsService, "__init__", return_value=None):
        instance = SerpapiGoogleTrendsService()
        instance.client = MagicMock()
        cache_mock = MagicMock()
        cache_mock.read.return_value = None
        instance._cache = cache_mock
        instance.client.search.side_effect = [
            MOCK_TIMESERIES_RESULT,
            MOCK_RELATED_TOPICS_RESULT,
            MOCK_RELATED_QUERIES_RESULT,
        ]
        return instance


def test_search_trend_returns_google_trends_response(
    service: SerpapiGoogleTrendsService,
) -> None:
    result = service.search_trend("electric bike", "today 5-y")

    assert isinstance(result, GoogleTrendsResponse)


def test_search_trend_maps_fields_correctly(
    service: SerpapiGoogleTrendsService,
) -> None:
    result = service.search_trend("electric bike", "today 5-y")

    assert result.query == "electric bike"
    assert result.date == "today 5-y"
    assert result.interest_over_time is not None
    assert len(result.interest_over_time.timeline_data) == 2
    assert result.interest_over_time.averages == [68]
    assert result.related_topics is not None
    assert len(result.related_topics.rising) == 1
    assert result.related_topics.rising[0].topic.title == "E-bike"
    assert result.related_queries is not None
    assert len(result.related_queries.top) == 1
    assert result.related_queries.top[0].query == "electric bicycle"


def test_search_trend_makes_three_search_calls(
    service: SerpapiGoogleTrendsService,
) -> None:
    service.search_trend("electric bike", "today 5-y")

    mock_search = cast(MagicMock, service.client.search)
    assert mock_search.call_count == 3
    calls = mock_search.call_args_list
    data_types = [call.args[0]["data_type"] for call in calls]
    assert data_types == ["TIMESERIES", "RELATED_TOPICS", "RELATED_QUERIES"]


def test_search_trend_uses_cache_on_hit(
    service: SerpapiGoogleTrendsService,
) -> None:
    cast(MagicMock, service._cache).read.return_value = MOCK_CACHED_RAW

    result = service.search_trend("electric bike", "today 5-y")

    cast(MagicMock, service.client.search).assert_not_called()
    assert isinstance(result, GoogleTrendsResponse)
    assert result.query == "electric bike"


def test_search_trend_writes_cache_on_miss(
    service: SerpapiGoogleTrendsService,
) -> None:
    service.search_trend("electric bike", "today 5-y")

    cast(MagicMock, service._cache).write.assert_called_once()
    cache_key, written_data = cast(MagicMock, service._cache).write.call_args.args
    assert cache_key == "electric bike::today 5-y"
    assert written_data["query"] == "electric bike"
    assert written_data["date"] == "today 5-y"
    assert "_timeseries" in written_data
    assert "_related_topics" in written_data
    assert "_related_queries" in written_data


def test_search_trend_cache_key_format(
    service: SerpapiGoogleTrendsService,
) -> None:
    service.search_trend("electric bike", "today 5-y")

    cast(MagicMock, service._cache).read.assert_called_once_with(
        "electric bike::today 5-y"
    )


@pytest.fixture
def mock_service() -> MockGoogleTrendsService:
    with patch.object(MockGoogleTrendsService, "__init__", return_value=None):
        instance = MockGoogleTrendsService()
        instance._cache = MagicMock()
        return instance


def test_mock_service_returns_response_on_cache_hit(
    mock_service: MockGoogleTrendsService,
) -> None:
    cast(MagicMock, mock_service._cache).read.return_value = MOCK_CACHED_RAW

    result = mock_service.search_trend("electric bike", "today 5-y")

    assert isinstance(result, GoogleTrendsResponse)
    assert result.query == "electric bike"


def test_mock_service_raises_on_cache_miss(
    mock_service: MockGoogleTrendsService,
) -> None:
    cast(MagicMock, mock_service._cache).read.return_value = None

    with pytest.raises(Exception, match="Google Trends cache wasn't hit"):
        mock_service.search_trend("electric bike", "today 5-y")


def test_google_trends_response_flatten_with_all_data() -> None:
    result = GoogleTrendsResponse.model_validate(MOCK_CACHED_RAW)

    assert result.query == "electric bike"
    assert result.date == "today 5-y"
    assert result.interest_over_time is not None
    assert result.related_topics is not None
    assert result.related_queries is not None


def test_google_trends_response_flatten_with_missing_sub_results() -> None:
    raw = {"query": "electric bike", "date": "today 5-y"}

    result = GoogleTrendsResponse.model_validate(raw)

    assert result.interest_over_time is None
    assert result.related_topics is None
    assert result.related_queries is None


def test_get_google_trends_service_returns_serpapi_when_key_set() -> None:
    with patch("app.services.google_trends_service.settings") as mock_settings:
        mock_settings.serpapi_api_key = "test-key"
        with patch.object(SerpapiGoogleTrendsService, "__init__", return_value=None):
            service = get_google_trends_service()

    assert isinstance(service, SerpapiGoogleTrendsService)


def test_get_google_trends_service_returns_mock_when_no_key() -> None:
    with patch("app.services.google_trends_service.settings") as mock_settings:
        mock_settings.serpapi_api_key = None
        with patch.object(MockGoogleTrendsService, "__init__", return_value=None):
            service = get_google_trends_service()

    assert isinstance(service, MockGoogleTrendsService)
