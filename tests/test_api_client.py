"""Tests for the API client module."""

from unittest.mock import MagicMock, patch

import pytest

from src.api.client import get


@pytest.mark.unit
class TestApiClient:
    """Tests for src.api.client.get()."""

    @patch("src.api.client._get_session")
    @patch("src.api.client.time.sleep")
    def test_get_returns_json(self, mock_sleep: MagicMock, mock_session: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"data": [{"id": 1}]}
        mock_response.raise_for_status = MagicMock()
        mock_session.return_value.get.return_value = mock_response

        result = get("/test")

        assert result == {"data": [{"id": 1}]}
        mock_sleep.assert_called_once()

    @patch("src.api.client._get_session")
    def test_get_raises_on_non_json(self, mock_session: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.url = "https://example.com/test"
        mock_response.status_code = 200
        mock_session.return_value.get.return_value = mock_response

        with pytest.raises(RuntimeError, match="Expected JSON"):
            get("/test")
