"""Fetch data from SMHI API.

Uses the SMHI forecast API via `smhi_pkg`:

- http://opendata.smhi.se/apidocs/metfcst/index.html
- https://github.com/joysoftware/pypi_smhi
"""

from __future__ import annotations

import logging

from smhi.smhi_lib import Smhi, SmhiForecast  # type: ignore

from .weather_base import BaseForecastProvider


class FetchSMHI(BaseForecastProvider):
    """Fetch weather forecasts from SMHI's opendata forecast API."""

    name = "smhi"

    def __init__(
        self, latitude: str, longitude: str, logger: logging.Logger | None = None
    ) -> None:
        super().__init__(latitude, longitude, logger)

    def get_forecast(self) -> list[SmhiForecast]:
        """Return daily forecasts starting tomorrow."""
        smhi = Smhi(longitude=self._longitude, latitude=self._latitude)
        forecasts: list[SmhiForecast] = smhi.get_forecast()
        return forecasts[1:]

    def get_forecast_hour(self) -> list[SmhiForecast]:
        """Return hourly forecasts starting from the next hour."""
        smhi = Smhi(longitude=self._longitude, latitude=self._latitude)
        forecasts: list[SmhiForecast] = smhi.get_forecast_hour()
        return forecasts[1:]

    def get_current_conditions(self) -> SmhiForecast:
        """Return the current (first) daily forecast as a single entry."""
        smhi = Smhi(longitude=self._longitude, latitude=self._latitude)
        forecasts: list[SmhiForecast] = smhi.get_forecast()
        return forecasts[0]
