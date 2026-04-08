"""Fetch weather forecasts from Open-Meteo.

Open-Meteo (https://open-meteo.com) is a free, no-API-key weather service that
aggregates data from national meteorological services (including MET Norway
and ECMWF) with excellent Nordic coverage. This module is a drop-in alternative
to `FetchSMHI` when the SMHI forecast API is unavailable.

Open-Meteo returns weather codes in WMO 4677 format (0-99). These are mapped
to SMHI's 1-27 symbol codes so that downstream consumers (including trained
ML models with one-hot encoded weather symbol features) keep working.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from smhi.smhi_lib import SmhiForecast  # type: ignore

from .weather_base import BaseForecastProvider, build_smhi_forecast

_API_URL = "https://api.open-meteo.com/v1/forecast"

# Hourly variables requested from Open-Meteo. Order does not matter — we read
# by name from the response.
_HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "surface_pressure",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
]

# Daily variables used to fill temperature_min / temperature_max for the
# hourly forecasts (SMHI provides these per entry).
_DAILY_VARIABLES = [
    "temperature_2m_min",
    "temperature_2m_max",
    "weather_code",
    "precipitation_sum",
    "wind_speed_10m_max",
    "wind_direction_10m_dominant",
    "wind_gusts_10m_max",
]


def wmo_to_smhi_symbol(wmo_code: int) -> int:
    """Map a WMO 4677 weather code (0-99) to an SMHI symbol code (1-27).

    The mapping is lossy — WMO distinguishes cases SMHI does not, and vice
    versa — but preserves the semantic category (clear/cloudy/rain/snow/etc.)
    that matters for the trained model's one-hot features.
    """
    mapping: dict[int, int] = {
        0: 1,  # Clear sky
        1: 2,  # Mainly clear -> Nearly clear sky
        2: 3,  # Partly cloudy -> Variable cloudiness
        3: 6,  # Overcast
        45: 7,  # Fog
        48: 7,  # Depositing rime fog -> Fog
        51: 18,  # Light drizzle -> Light rain
        53: 19,  # Moderate drizzle -> Moderate rain
        55: 20,  # Dense drizzle -> Heavy rain
        56: 22,  # Light freezing drizzle -> Light sleet
        57: 23,  # Dense freezing drizzle -> Moderate sleet
        61: 18,  # Slight rain
        63: 19,  # Moderate rain
        65: 20,  # Heavy rain
        66: 22,  # Light freezing rain -> Light sleet
        67: 24,  # Heavy freezing rain -> Heavy sleet
        71: 25,  # Slight snow fall
        73: 26,  # Moderate snow fall
        75: 27,  # Heavy snow fall
        77: 25,  # Snow grains -> Light snowfall
        80: 8,  # Slight rain showers
        81: 9,  # Moderate rain showers
        82: 10,  # Violent rain showers -> Heavy rain showers
        85: 15,  # Slight snow showers
        86: 17,  # Heavy snow showers
        95: 11,  # Thunderstorm
        96: 11,  # Thunderstorm with slight hail
        99: 11,  # Thunderstorm with heavy hail
    }
    return mapping.get(wmo_code, 6)  # Default to Overcast for unknown codes


def wmo_to_smhi_precipitation(wmo_code: int) -> int:
    """Map a WMO code to SMHI precipitation category (0-6).

    SMHI categories:
        0=none, 1=snow, 2=snow+rain, 3=rain, 4=drizzle,
        5=freezing rain, 6=freezing drizzle
    """
    if wmo_code in {51, 53, 55}:
        return 4  # Drizzle
    if wmo_code in {56, 57}:
        return 6  # Freezing drizzle
    if wmo_code in {66, 67}:
        return 5  # Freezing rain
    if wmo_code in {61, 63, 65, 80, 81, 82}:
        return 3  # Rain
    if wmo_code in {71, 73, 75, 77, 85, 86}:
        return 1  # Snow
    if wmo_code in {96, 99}:
        return 2  # Snow and rain (thunder + hail)
    return 0  # None / clear / fog / thunder without precip


class FetchOpenMeteo(BaseForecastProvider):
    """Fetch weather forecasts from Open-Meteo as `SmhiForecast` objects."""

    name = "open_meteo"

    def __init__(
        self,
        latitude: str,
        longitude: str,
        logger: logging.Logger | None = None,
        *,
        timeout: float = 15.0,
    ) -> None:
        super().__init__(latitude, longitude, logger)
        self._timeout = timeout
        self._cached_payload: dict[str, Any] | None = None

    def _fetch_payload(self) -> dict[str, Any]:
        """Fetch the raw JSON response from Open-Meteo (cached per instance).

        A single Open-Meteo request returns both hourly and daily forecasts,
        so we cache the response to avoid hitting the API multiple times when
        `get_forecast()` / `get_forecast_hour()` / `get_current_conditions()`
        are called in sequence.
        """
        if self._cached_payload is not None:
            return self._cached_payload

        params = {
            "latitude": self._latitude,
            "longitude": self._longitude,
            "hourly": ",".join(_HOURLY_VARIABLES),
            "daily": ",".join(_DAILY_VARIABLES),
            "timezone": "UTC",
            "forecast_days": 10,
            "wind_speed_unit": "ms",
        }
        url = f"{_API_URL}?{urlencode(params)}"
        self._log.debug("Fetching Open-Meteo forecast: %s", url)
        request = Request(url, headers={"User-Agent": "edbo_data/1.x"})
        with urlopen(request, timeout=self._timeout) as response:  # nosec B310
            raw = response.read()
        payload: dict[str, Any] = json.loads(raw)
        self._cached_payload = payload
        return payload

    def _hourly_entries(self) -> list[SmhiForecast]:
        payload = self._fetch_payload()
        hourly = payload.get("hourly", {})
        times: list[str] = hourly.get("time", [])
        if not times:
            return []

        # Build a per-day index of daily min/max so we can attach them to each
        # hourly entry (SMHI provides min/max on every entry).
        daily = payload.get("daily", {})
        daily_times: list[str] = daily.get("time", [])
        daily_min = daily.get("temperature_2m_min", [])
        daily_max = daily.get("temperature_2m_max", [])
        day_min_by_date: dict[str, float] = {
            d: (
                daily_min[i] if i < len(daily_min) and daily_min[i] is not None else 0.0
            )
            for i, d in enumerate(daily_times)
        }
        day_max_by_date: dict[str, float] = {
            d: (
                daily_max[i] if i < len(daily_max) and daily_max[i] is not None else 0.0
            )
            for i, d in enumerate(daily_times)
        }

        def _get(field: str, idx: int, default: float = 0.0) -> float:
            values = hourly.get(field, [])
            if idx >= len(values) or values[idx] is None:
                return default
            return float(values[idx])

        forecasts: list[SmhiForecast] = []
        for i, time_str in enumerate(times):
            # Open-Meteo returns ISO8601 without timezone suffix when tz=UTC.
            valid_time = datetime.fromisoformat(time_str)
            date_key = time_str[:10]
            wmo = int(_get("weather_code", i, 0))
            forecasts.append(
                build_smhi_forecast(
                    valid_time=valid_time,
                    temperature=_get("temperature_2m", i),
                    temperature_min=day_min_by_date.get(date_key, 0.0),
                    temperature_max=day_max_by_date.get(date_key, 0.0),
                    humidity=int(_get("relative_humidity_2m", i)),
                    pressure=_get("surface_pressure", i),
                    precipitation=wmo_to_smhi_precipitation(wmo),
                    wind_speed=_get("wind_speed_10m", i),
                    wind_direction=int(_get("wind_direction_10m", i)),
                    wind_gust=_get("wind_gusts_10m", i),
                    symbol=wmo_to_smhi_symbol(wmo),
                )
            )
        return forecasts

    def _daily_entries(self) -> list[SmhiForecast]:
        payload = self._fetch_payload()
        daily = payload.get("daily", {})
        times: list[str] = daily.get("time", [])
        if not times:
            return []

        def _get(field: str, idx: int, default: float = 0.0) -> float:
            values = daily.get(field, [])
            if idx >= len(values) or values[idx] is None:
                return default
            return float(values[idx])

        forecasts: list[SmhiForecast] = []
        for i, date_str in enumerate(times):
            # Daily "valid_time" is midday for that date.
            valid_time = datetime.fromisoformat(f"{date_str}T12:00:00")
            wmo = int(_get("weather_code", i, 0))
            t_min = _get("temperature_2m_min", i)
            t_max = _get("temperature_2m_max", i)
            forecasts.append(
                build_smhi_forecast(
                    valid_time=valid_time,
                    temperature=(t_min + t_max) / 2.0,
                    temperature_min=t_min,
                    temperature_max=t_max,
                    humidity=0,
                    pressure=0.0,
                    precipitation=wmo_to_smhi_precipitation(wmo),
                    wind_speed=_get("wind_speed_10m_max", i),
                    wind_direction=int(_get("wind_direction_10m_dominant", i)),
                    wind_gust=_get("wind_gusts_10m_max", i),
                    symbol=wmo_to_smhi_symbol(wmo),
                )
            )
        return forecasts

    def get_forecast(self) -> list[SmhiForecast]:
        """Daily forecasts starting tomorrow (matches FetchSMHI behaviour)."""
        entries = self._daily_entries()
        return entries[1:]

    def get_forecast_hour(self) -> list[SmhiForecast]:
        """Hourly forecasts starting from the next hour."""
        entries = self._hourly_entries()
        return entries[1:]

    def get_current_conditions(self) -> SmhiForecast:
        """Return the current (first) hourly entry as a single forecast."""
        entries = self._hourly_entries()
        if not entries:
            raise RuntimeError("Open-Meteo returned no hourly data")
        return entries[0]
