from __future__ import annotations

import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from edbo_data.fetching.weather_provider import (
    WeatherProviderWithFallback,
    _is_transient,
)


def _make_provider(name: str) -> MagicMock:
    """Create a mock provider with required base-class attributes."""
    p = MagicMock()
    p.name = name
    p._latitude = 59.0
    p._longitude = 18.0
    return p


def _http_error(code: int, msg: str = "") -> urllib.error.HTTPError:
    return urllib.error.HTTPError("url", code, msg, {}, None)  # type: ignore[arg-type]


class TestIsTransient:
    def test_502_is_transient(self) -> None:
        assert _is_transient(_http_error(502)) is True

    def test_503_is_transient(self) -> None:
        assert _is_transient(_http_error(503)) is True

    def test_429_is_transient(self) -> None:
        assert _is_transient(_http_error(429)) is True

    def test_404_is_not_transient(self) -> None:
        assert _is_transient(_http_error(404)) is False

    def test_string_match_fallback(self) -> None:
        exc = Exception("HTTP Error 502: Bad Gateway")
        assert _is_transient(exc) is True

    def test_none_is_not_transient(self) -> None:
        assert _is_transient(None) is False


class TestWeatherProviderRetry:
    def _make_wrapper(self, providers: list[MagicMock]) -> WeatherProviderWithFallback:
        wrapper = WeatherProviderWithFallback.__new__(WeatherProviderWithFallback)
        wrapper._providers = providers
        wrapper._active_index = 0
        wrapper._primary_name = providers[0].name
        wrapper._used_fallback = False
        wrapper._log = MagicMock()
        return wrapper

    def test_first_provider_succeeds(self) -> None:
        a = _make_provider("a")
        b = _make_provider("b")
        a.get_forecast.return_value = ["sunny"]
        wrapper = self._make_wrapper([a, b])

        result = wrapper._try_each("get_forecast", lambda p: p.get_forecast())

        assert result == ["sunny"]
        b.get_forecast.assert_not_called()

    def test_fallback_on_first_failure(self) -> None:
        a = _make_provider("a")
        b = _make_provider("b")
        a.get_forecast.side_effect = Exception("HTTP Error 404: Not Found")
        b.get_forecast.return_value = ["cloudy"]
        wrapper = self._make_wrapper([a, b])

        result = wrapper._try_each("get_forecast", lambda p: p.get_forecast())

        assert result == ["cloudy"]
        assert wrapper._used_fallback is True

    @patch("edbo_data.fetching.weather_provider.time.sleep")
    def test_retry_on_transient_failure_of_both(self, mock_sleep: MagicMock) -> None:
        """A->404, B->502, wait, A->404, B->success."""
        a = _make_provider("a")
        b = _make_provider("b")
        a.get_forecast.side_effect = Exception("HTTP Error 404: Not Found")
        b.get_forecast.side_effect = [
            _http_error(502, "Bad Gateway"),
            ["rain"],  # succeeds on retry
        ]
        wrapper = self._make_wrapper([a, b])

        result = wrapper._try_each(
            "get_forecast", lambda p: p.get_forecast(), retries=2, retry_delay=1.0
        )

        assert result == ["rain"]
        mock_sleep.assert_called_once_with(1.0)

    @patch("edbo_data.fetching.weather_provider.time.sleep")
    def test_no_retry_on_non_transient(self, mock_sleep: MagicMock) -> None:
        """A->404, B->404 — no retry since neither is transient."""
        a = _make_provider("a")
        b = _make_provider("b")
        a.get_forecast.side_effect = Exception("HTTP Error 404: Not Found")
        b.get_forecast.side_effect = _http_error(404, "Not Found")
        wrapper = self._make_wrapper([a, b])

        with pytest.raises(urllib.error.HTTPError):
            wrapper._try_each(
                "get_forecast", lambda p: p.get_forecast(), retries=2, retry_delay=1.0
            )

        mock_sleep.assert_not_called()

    @patch("edbo_data.fetching.weather_provider.time.sleep")
    def test_retries_exhausted(self, mock_sleep: MagicMock) -> None:
        """All attempts fail — raises after exhausting retries."""
        a = _make_provider("a")
        b = _make_provider("b")
        err = _http_error(502, "Bad Gateway")
        a.get_forecast.side_effect = err
        b.get_forecast.side_effect = err
        wrapper = self._make_wrapper([a, b])

        with pytest.raises(urllib.error.HTTPError):
            wrapper._try_each(
                "get_forecast", lambda p: p.get_forecast(), retries=2, retry_delay=0.0
            )

        # 2 retries = 2 sleeps
        assert mock_sleep.call_count == 2
