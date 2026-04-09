"""Tests for the Open-Meteo weather provider and provider factory."""

from __future__ import annotations

import io
import json
import logging
from typing import Any
from unittest.mock import patch

import pytest

from edbo_data.fetching.fetch_open_meteo import (
    FetchOpenMeteo,
    wmo_to_smhi_precipitation,
    wmo_to_smhi_symbol,
)
from edbo_data.fetching.weather_provider import (
    WeatherProviderWithFallback,
    create_weather_provider,
)

# ---------------------------------------------------------------------------
# WMO -> SMHI mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "wmo,expected_symbol",
    [
        (0, 1),  # Clear
        (1, 2),  # Mainly clear
        (2, 3),  # Partly cloudy
        (3, 6),  # Overcast
        (45, 7),  # Fog
        (48, 7),  # Freezing fog
        (61, 18),  # Light rain
        (65, 20),  # Heavy rain
        (71, 25),  # Slight snow
        (75, 27),  # Heavy snow
        (95, 11),  # Thunderstorm
        (96, 11),  # Thunder + hail
    ],
)
def test_wmo_to_smhi_symbol_known_codes(wmo: int, expected_symbol: int) -> None:
    assert wmo_to_smhi_symbol(wmo) == expected_symbol


def test_wmo_to_smhi_symbol_unknown_falls_back_to_overcast() -> None:
    assert wmo_to_smhi_symbol(123) == 6


@pytest.mark.parametrize(
    "wmo,expected_category",
    [
        (0, 0),  # No precip
        (51, 4),  # Drizzle
        (56, 6),  # Freezing drizzle
        (61, 3),  # Rain
        (66, 5),  # Freezing rain
        (71, 1),  # Snow
        (96, 2),  # Snow + rain (hail)
    ],
)
def test_wmo_to_smhi_precipitation(wmo: int, expected_category: int) -> None:
    assert wmo_to_smhi_precipitation(wmo) == expected_category


# ---------------------------------------------------------------------------
# FetchOpenMeteo HTTP parsing
# ---------------------------------------------------------------------------


def _fake_open_meteo_payload() -> dict[str, Any]:
    """Two hourly entries on the same day, plus matching daily summary."""
    return {
        "hourly": {
            "time": ["2026-04-08T00:00", "2026-04-08T01:00"],
            "temperature_2m": [3.4, 3.1],
            "relative_humidity_2m": [85, 87],
            "surface_pressure": [1010.2, 1010.0],
            "precipitation": [0.0, 0.2],
            "weather_code": [3, 61],
            "wind_speed_10m": [4.5, 5.0],
            "wind_direction_10m": [180, 190],
            "wind_gusts_10m": [7.0, 7.5],
        },
        "daily": {
            "time": ["2026-04-08", "2026-04-09"],
            "temperature_2m_min": [1.2, 0.5],
            "temperature_2m_max": [6.8, 5.5],
            "weather_code": [61, 3],
            "precipitation_sum": [1.5, 0.0],
            "wind_speed_10m_max": [6.0, 5.0],
            "wind_direction_10m_dominant": [185, 200],
            "wind_gusts_10m_max": [8.5, 7.0],
        },
    }


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._buf = io.BytesIO(json.dumps(payload).encode("utf-8"))

    def read(self) -> bytes:
        return self._buf.read()

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._buf.close()


def test_fetch_open_meteo_parses_hourly_into_smhi_forecast() -> None:
    payload = _fake_open_meteo_payload()
    provider = FetchOpenMeteo("59.22", "18.15")
    with patch(
        "edbo_data.fetching.fetch_open_meteo.urlopen",
        return_value=_FakeResponse(payload),
    ):
        current = provider.get_current_conditions()

    assert current.temperature == pytest.approx(3.4)
    assert current.humidity == 85
    assert current.symbol == 6  # WMO 3 (overcast) -> SMHI 6
    assert current.temperature_min == pytest.approx(1.2)
    assert current.temperature_max == pytest.approx(6.8)


def test_fetch_open_meteo_get_forecast_hour_skips_first_entry() -> None:
    payload = _fake_open_meteo_payload()
    provider = FetchOpenMeteo("59.22", "18.15")
    with patch(
        "edbo_data.fetching.fetch_open_meteo.urlopen",
        return_value=_FakeResponse(payload),
    ):
        forecasts = provider.get_forecast_hour()

    assert len(forecasts) == 1
    assert forecasts[0].temperature == pytest.approx(3.1)
    assert forecasts[0].symbol == 18  # WMO 61 -> SMHI 18 (Light rain)
    assert forecasts[0].precipitation == 3  # Rain category


def test_fetch_open_meteo_get_forecast_skips_today() -> None:
    payload = _fake_open_meteo_payload()
    provider = FetchOpenMeteo("59.22", "18.15")
    with patch(
        "edbo_data.fetching.fetch_open_meteo.urlopen",
        return_value=_FakeResponse(payload),
    ):
        forecasts = provider.get_forecast()

    assert len(forecasts) == 1
    # Second daily entry: 2026-04-09 (overcast)
    assert forecasts[0].temperature_min == pytest.approx(0.5)
    assert forecasts[0].temperature_max == pytest.approx(5.5)
    assert forecasts[0].symbol == 6


def test_fetch_open_meteo_caches_payload_across_calls() -> None:
    payload = _fake_open_meteo_payload()
    provider = FetchOpenMeteo("59.22", "18.15")
    with patch(
        "edbo_data.fetching.fetch_open_meteo.urlopen",
        return_value=_FakeResponse(payload),
    ) as mock_urlopen:
        provider.get_current_conditions()
        provider.get_forecast_hour()
        provider.get_forecast()

    assert mock_urlopen.call_count == 1


# ---------------------------------------------------------------------------
# Provider factory and fallback wrapper
# ---------------------------------------------------------------------------


class _StubConfig:
    """Minimal stand-in for python_support.MyConfig."""

    def __init__(self, **attrs: str) -> None:
        self._attrs = attrs

    def __getattr__(self, name: str) -> str:
        if name.startswith("_"):
            raise AttributeError(name)
        if name not in self._attrs:
            raise AttributeError(name)
        return self._attrs[name]


def test_create_weather_provider_defaults_to_smhi_with_open_meteo_fallback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    config = _StubConfig(map_latitude="59.22", map_longitude="18.15")
    log = logging.getLogger("test_default")
    with caplog.at_level(logging.INFO, logger="test_default"):
        provider = create_weather_provider(config, log)

    assert isinstance(provider, WeatherProviderWithFallback)
    # First in chain is SMHI, fallback is Open-Meteo.
    assert provider._providers[0].name == "smhi"
    assert provider._providers[1].name == "open_meteo"
    assert any("smhi" in r.message for r in caplog.records)


def test_create_weather_provider_explicit_open_meteo_primary() -> None:
    config = _StubConfig(
        map_latitude="59.22",
        map_longitude="18.15",
        weather_provider="open_meteo",
    )
    provider = create_weather_provider(config)
    assert isinstance(provider, WeatherProviderWithFallback)
    assert provider._providers[0].name == "open_meteo"
    assert provider._providers[1].name == "smhi"


def test_create_weather_provider_disabled_fallback_returns_single_provider() -> None:
    config = _StubConfig(
        map_latitude="59.22",
        map_longitude="18.15",
        weather_provider="open_meteo",
        weather_fallback="none",
    )
    provider = create_weather_provider(config)
    assert provider.name == "open_meteo"


def test_create_weather_provider_unknown_primary_raises() -> None:
    config = _StubConfig(
        map_latitude="59.22",
        map_longitude="18.15",
        weather_provider="bogus",
    )
    with pytest.raises(ValueError, match="Unknown weather provider"):
        create_weather_provider(config)


class _BrokenProvider(FetchOpenMeteo):
    """Always raises when fetching — used to simulate primary failure."""

    name = "broken"

    def _fetch_payload(self) -> dict[str, Any]:
        raise RuntimeError("primary down")


class _StubProvider(FetchOpenMeteo):
    """Returns a fixed payload without touching the network."""

    name = "stub"

    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__("59.22", "18.15")
        self._stub_payload = payload

    def _fetch_payload(self) -> dict[str, Any]:
        return self._stub_payload


def test_fallback_wrapper_falls_back_when_primary_raises(
    caplog: pytest.LogCaptureFixture,
) -> None:
    primary = _BrokenProvider("59.22", "18.15")
    fallback = _StubProvider(_fake_open_meteo_payload())

    wrapper = WeatherProviderWithFallback([primary, fallback])
    with caplog.at_level(logging.WARNING):
        current = wrapper.get_current_conditions()

    assert current.temperature == pytest.approx(3.4)
    assert wrapper.active_provider is fallback
    assert any("fell back" in r.message for r in caplog.records)


def test_fallback_wrapper_raises_when_all_providers_fail() -> None:
    primary = _BrokenProvider("59.22", "18.15")
    fallback = _BrokenProvider("59.22", "18.15")

    wrapper = WeatherProviderWithFallback([primary, fallback])
    with pytest.raises(RuntimeError, match="primary down"):
        wrapper.get_current_conditions()


def test_fallback_wrapper_tracks_primary_and_used_fallback_flag() -> None:
    primary = _BrokenProvider("59.22", "18.15")
    fallback = _StubProvider(_fake_open_meteo_payload())

    wrapper = WeatherProviderWithFallback([primary, fallback])
    assert wrapper.primary_name == "broken"
    assert wrapper.used_fallback is False

    wrapper.get_current_conditions()
    assert wrapper.used_fallback is True
    # primary_name should still point at the original primary, not the
    # currently-active provider.
    assert wrapper.primary_name == "broken"


def test_fallback_wrapper_used_fallback_stays_false_on_primary_success() -> None:
    primary = _StubProvider(_fake_open_meteo_payload())
    fallback = _BrokenProvider("59.22", "18.15")

    wrapper = WeatherProviderWithFallback([primary, fallback])
    wrapper.get_current_conditions()
    assert wrapper.used_fallback is False
