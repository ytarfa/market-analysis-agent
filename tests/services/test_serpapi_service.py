from unittest.mock import MagicMock, patch

import pytest

from app.services.serpapi_service import SerpapiService


def test_serpapi_service_throws_error_when_no_api_key() -> None:
    mock_settings = MagicMock()
    mock_settings.serpapi_api_key = None

    with patch("app.services.serpapi_service.settings", mock_settings):
        with pytest.raises(ValueError, match="SERPAPI_API_KEY is not set"):
            SerpapiService()
