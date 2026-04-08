"""Base class and common helpers for weather forecast providers.

Different providers (SMHI, Open-Meteo, ...) can share the symbol and
precipitation string lookup tables as well as the `forecast_to_conditions`
conversion, since they all normalize their output into `SmhiForecast` objects.
"""

from __future__ import annotations

import logging
from datetime import datetime

from smhi.smhi_lib import SmhiForecast  # type: ignore


class BaseForecastProvider:
    """Abstract base for weather forecast providers.

    Subclasses must implement `get_forecast`, `get_forecast_hour`, and
    `get_current_conditions`. All providers normalize their output into
    `SmhiForecast` objects so downstream code can treat them uniformly.
    """

    #: Human-readable provider name (e.g. "smhi", "open_meteo"). Subclasses override.
    name: str = "base"

    def __init__(
        self, latitude: str, longitude: str, logger: logging.Logger | None = None
    ) -> None:
        self._latitude = latitude
        self._longitude = longitude
        self._log = logger if logger is not None else logging.getLogger(__name__)

    def get_forecast(self) -> list[SmhiForecast]:
        raise NotImplementedError

    def get_forecast_hour(self) -> list[SmhiForecast]:
        raise NotImplementedError

    def get_current_conditions(self) -> SmhiForecast:
        raise NotImplementedError

    def forecast_to_conditions(
        self, forecast: SmhiForecast
    ) -> dict[str, int | str | float | datetime]:
        """Convert a forecast to a dictionary of conditions."""
        return {
            "valid_time": forecast.valid_time,
            "temperature": forecast.temperature,
            "temperature_min": forecast.temperature_min,
            "temperature_max": forecast.temperature_max,
            "wind_speed": forecast.wind_speed,
            "wind_direction": forecast.wind_direction,
            "wind_gust": forecast.wind_gust,
            "symbol": forecast.symbol,
            "symbol_string": self.symbol_to_string(forecast.symbol),
            "humidity": forecast.humidity,
            "pressure": forecast.pressure,
            "precipitation": forecast.precipitation,
            "precipitation_string": self.precipitation_to_string(
                forecast.precipitation
            ),
        }

    @staticmethod
    def precipitation_to_string(precipitation: int) -> str:
        """Convert an SMHI precipitation category (0-6) to a string."""
        mapping = {
            0: "No precipitation",
            1: "Snow",
            2: "Snow and rain",
            3: "Rain",
            4: "Drizzle",
            5: "Freezing rain",
            6: "Freezing drizzle",
        }
        try:
            return mapping[precipitation]
        except KeyError as exc:
            raise ValueError(f"Unknown precipitation code: {precipitation}") from exc

    @staticmethod
    def symbol_to_string(symbol: int) -> str:
        """Convert an SMHI weather symbol (1-27) to a string."""
        mapping = {
            1: "Clear sky",
            2: "Nearly clear sky",
            3: "Variable cloudiness",
            4: "Halfclear sky",
            5: "Cloudy sky",
            6: "Overcast",
            7: "Fog",
            8: "Light rain showers",
            9: "Moderate rain showers",
            10: "Heavy rain showers",
            11: "Thunderstorm",
            12: "Light sleet showers",
            13: "Moderate sleet showers",
            14: "Heavy sleet showers",
            15: "Light snow showers",
            16: "Moderate snow showers",
            17: "Heavy snow showers",
            18: "Light rain",
            19: "Moderate rain",
            20: "Heavy rain",
            21: "Thunder",
            22: "Light sleet",
            23: "Moderate sleet",
            24: "Heavy sleet",
            25: "Light snowfall",
            26: "Moderate snowfall",
            27: "Heavy snowfall",
        }
        try:
            return mapping[symbol]
        except KeyError as exc:
            raise ValueError(f"Unknown symbol code: {symbol}") from exc


def build_smhi_forecast(
    *,
    valid_time: datetime,
    temperature: float,
    temperature_min: float,
    temperature_max: float,
    humidity: int,
    pressure: float,
    precipitation: int,
    wind_speed: float,
    wind_direction: int,
    wind_gust: float,
    symbol: int,
    cloudiness: int = 0,
    thunder: int = 0,
    mean_precipitation: float = 0.0,
    total_precipitation: float = 0.0,
    horizontal_visibility: float = 0.0,
) -> SmhiForecast:
    """Construct an `SmhiForecast` with sensible defaults for optional fields.

    Non-SMHI providers can use this to build compatible forecast objects
    without having to fill in every field SMHI happens to expose.
    """
    return SmhiForecast(
        temperature=temperature,
        temperature_max=temperature_max,
        temperature_min=temperature_min,
        humidity=humidity,
        pressure=pressure,
        thunder=thunder,
        cloudiness=cloudiness,
        precipitation=precipitation,
        wind_direction=wind_direction,
        wind_speed=wind_speed,
        horizontal_visibility=horizontal_visibility,
        wind_gust=wind_gust,
        mean_precipitation=mean_precipitation,
        total_precipitation=total_precipitation,
        symbol=symbol,
        valid_time=valid_time,
    )
