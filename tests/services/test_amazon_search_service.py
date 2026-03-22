# ruff: noqa: E501
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from app.services.amazon_search_service import (
    AmazonSearchResult,
    SerpApiAmazonSearchService,
)

MOCK_ORGANIC_RESULTS = [
    {
        "position": 1,
        "asin": "B0C2Z3BF4G",
        "options": "1 image",
        "options_link": "https://www.amazon.com/STAMTECH-Custom-Logo-Embosser-Stamp/dp/B0C2Z3BF4G/ref=vo_sr_l_dp?dib=eyJ2IjoiMSJ9.gVxvFICXxTXcpukJNVxQkBKCMdo9jUqOaBimFvOOLChWPDrgHqAEM7ZMIiuzxetzsgqXCnMQIp4U05kyFxfKTKRjmke9Mjyoiya0-gXEpoIyaBxF619QYha2N8STneeU30DBbTt0qaqS9fmKZGoIMxVuMyKZd1EzIv4mf9xvbn2vXw4d_AvA_Jyjkda__a_d-4xwgNRwAMvqjXphMovKpe2yHxV3kDLtbR1CPjFJrTR1iBhBIQL5lyHzCXgHt3HDh-_7_To4EcGiOTJ9g9b5t4T-cPYDE4rZPdutIxyHXvU.XMnFJKtwjqcGcbeN3dt7fDARY8LSUysxswlAgppUSk4&dib_tag=se&keywords=steel+book+embosser&qid=1767028167&sr=8-5",
        "title": "STAMTECH Custom Logo Embosser Stamp - Heavy Steel Embosser Stamps Design Your Own Logo or Emblem Perfect for Weddings Libraries Book Embosser",
        "link": "https://www.amazon.com/STAMTECH-Custom-Logo-Embosser-Stamp/dp/B0C2Z3BF4G/ref=sr_1_5?dib=eyJ2IjoiMSJ9.gVxvFICXxTXcpukJNVxQkBKCMdo9jUqOaBimFvOOLChWPDrgHqAEM7ZMIiuzxetzsgqXCnMQIp4U05kyFxfKTKRjmke9Mjyoiya0-gXEpoIyaBxF619QYha2N8STneeU30DBbTt0qaqS9fmKZGoIMxVuMyKZd1EzIv4mf9xvbn2vXw4d_AvA_Jyjkda__a_d-4xwgNRwAMvqjXphMovKpe2yHxV3kDLtbR1CPjFJrTR1iBhBIQL5lyHzCXgHt3HDh-_7_To4EcGiOTJ9g9b5t4T-cPYDE4rZPdutIxyHXvU.XMnFJKtwjqcGcbeN3dt7fDARY8LSUysxswlAgppUSk4&dib_tag=se&keywords=steel+book+embosser&qid=1767028167&sr=8-5",
        "link_clean": "https://www.amazon.com/STAMTECH-Custom-Logo-Embosser-Stamp/dp/B0C2Z3BF4G/",
        "serpapi_link": "https://serpapi.com/search?amazon_domain=amazon.com&asin=B0C2Z3BF4G&device=desktop&engine=amazon_product",
        "thumbnail": "https://m.media-amazon.com/images/I/61G8KEZXgPL._AC_UL320_.jpg",
        "rating": 4.5,
        "reviews": 257,
        "bought_last_month": "50+ bought in past month",
        "price": "$14.99",
        "extracted_price": 14.99,
        "save_with_coupon": "Save 30% with coupon",
        "delivery": ["$4.99 delivery Wed, Jan 14"],
        "customizable": True,
    },
    {
        "position": 2,
        "asin": "B0C2Z3BF4G",
        "options": "1 image",
        "options_link": "https://www.amazon.com/STAMTECH-Custom-Logo-Embosser-Stamp/dp/B0C2Z3BF4G/ref=vo_sr_l_dp?dib=eyJ2IjoiMSJ9.gVxvFICXxTXcpukJNVxQkBKCMdo9jUqOaBimFvOOLChWPDrgHqAEM7ZMIiuzxetzsgqXCnMQIp4U05kyFxfKTKRjmke9Mjyoiya0-gXEpoIyaBxF619QYha2N8STneeU30DBbTt0qaqS9fmKZGoIMxVuMyKZd1EzIv4mf9xvbn2vXw4d_AvA_Jyjkda__a_d-4xwgNRwAMvqjXphMovKpe2yHxV3kDLtbR1CPjFJrTR1iBhBIQL5lyHzCXgHt3HDh-_7_To4EcGiOTJ9g9b5t4T-cPYDE4rZPdutIxyHXvU.XMnFJKtwjqcGcbeN3dt7fDARY8LSUysxswlAgppUSk4&dib_tag=se&keywords=steel+book+embosser&qid=1767028167&sr=8-5",
        "title": "STAMTECH Custom Logo Embosser Stamp - Heavy Steel Embosser Stamps Design Your Own Logo or Emblem Perfect for Weddings Libraries Book Embosser",
        "link": "https://www.amazon.com/STAMTECH-Custom-Logo-Embosser-Stamp/dp/B0C2Z3BF4G/ref=sr_1_5?dib=eyJ2IjoiMSJ9.gVxvFICXxTXcpukJNVxQkBKCMdo9jUqOaBimFvOOLChWPDrgHqAEM7ZMIiuzxetzsgqXCnMQIp4U05kyFxfKTKRjmke9Mjyoiya0-gXEpoIyaBxF619QYha2N8STneeU30DBbTt0qaqS9fmKZGoIMxVuMyKZd1EzIv4mf9xvbn2vXw4d_AvA_Jyjkda__a_d-4xwgNRwAMvqjXphMovKpe2yHxV3kDLtbR1CPjFJrTR1iBhBIQL5lyHzCXgHt3HDh-_7_To4EcGiOTJ9g9b5t4T-cPYDE4rZPdutIxyHXvU.XMnFJKtwjqcGcbeN3dt7fDARY8LSUysxswlAgppUSk4&dib_tag=se&keywords=steel+book+embosser&qid=1767028167&sr=8-5",
        "link_clean": "https://www.amazon.com/STAMTECH-Custom-Logo-Embosser-Stamp/dp/B0C2Z3BF4G/",
        "serpapi_link": "https://serpapi.com/search?amazon_domain=amazon.com&asin=B0C2Z3BF4G&device=desktop&engine=amazon_product",
        "thumbnail": "https://m.media-amazon.com/images/I/61G8KEZXgPL._AC_UL320_.jpg",
        "rating": 4.5,
        "reviews": 257,
        "bought_last_month": "50+ bought in past month",
        "price": "$14.99",
        "extracted_price": 14.99,
        "save_with_coupon": "Save 30% with coupon",
        "delivery": ["$4.99 delivery Wed, Jan 14"],
        "customizable": True,
    },
]

MOCK_SEARCH_RESPONSE = {"organic_results": MOCK_ORGANIC_RESULTS}


@pytest.fixture
def service() -> SerpApiAmazonSearchService:
    with patch.object(SerpApiAmazonSearchService, "__init__", return_value=None):
        instance = SerpApiAmazonSearchService()
        instance.client = MagicMock()
        instance._cache = MagicMock()
        instance._cache.read.return_value = None
        return instance


def test_search_product_returns_list_of_organic_results(
    service: SerpApiAmazonSearchService,
) -> None:
    cast(MagicMock, service._cache).read.return_value = None
    service.client.search = MagicMock(return_value=MOCK_SEARCH_RESPONSE)

    results = service.search_product("iPhone 16")

    assert len(results) == 2
    assert all(isinstance(r, AmazonSearchResult) for r in results)


def test_search_product_maps_fields_correctly(
    service: SerpApiAmazonSearchService,
) -> None:
    cast(MagicMock, service._cache).read.return_value = None
    service.client.search = MagicMock(return_value=MOCK_SEARCH_RESPONSE)

    results = service.search_product("iPhone 16")

    assert results[0].position == 1
    assert results[0].asin == "B0C2Z3BF4G"
    assert (
        results[0].title
        == "STAMTECH Custom Logo Embosser Stamp - Heavy Steel Embosser Stamps Design Your Own Logo or Emblem Perfect for Weddings Libraries Book Embosser"
    )


def test_search_product_raises_on_invalid_result_schema(
    service: SerpApiAmazonSearchService,
) -> None:
    cast(MagicMock, service._cache).read.return_value = None
    service.client.search = MagicMock(
        return_value={"organic_results": [{"bad_field": "no_asin_or_position"}]}
    )

    with pytest.raises(Exception):
        service.search_product("iPhone 16")


def test_search_product_returns_cached_results_on_cache_hit(
    service: SerpApiAmazonSearchService,
) -> None:
    cast(MagicMock, service._cache).read.return_value = MOCK_SEARCH_RESPONSE

    results = service.search_product("iPhone 16")

    cast(MagicMock, service.client.search).assert_not_called()
    assert len(results) == 2
    assert all(isinstance(r, AmazonSearchResult) for r in results)


def test_search_product_writes_to_cache_on_cache_miss(
    service: SerpApiAmazonSearchService,
) -> None:
    cast(MagicMock, service._cache).read.return_value = None
    service.client.search = MagicMock(return_value=MOCK_SEARCH_RESPONSE)

    service.search_product("iPhone 16")

    cast(MagicMock, service._cache).write.assert_called_once_with(
        "iPhone 16", dict(MOCK_SEARCH_RESPONSE)
    )


def test_search_product_does_not_call_api_on_cache_hit(
    service: SerpApiAmazonSearchService,
) -> None:
    cast(MagicMock, service._cache).read.return_value = MOCK_SEARCH_RESPONSE

    service.search_product("iPhone 16")

    cast(MagicMock, service.client.search).assert_not_called()
