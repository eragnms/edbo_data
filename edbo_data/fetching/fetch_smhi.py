"""Fetch data from SMHI API

Uses the SMHI API to fetch weather data for a specific location see,
- http://opendata.smhi.se/apidocs/metfcst/index.html
- https://github.com/joysoftware/pypi_smhi?tab=readme-ov-file
"""

import logging

from smhi.smhi_lib import Smhi, SmhiForecast  # type: ignore

log = logging.getLogger("EDBO_DATA")


class FetchSMHI:
    """FetchSMHI is responsible for fetching weather forecasts.

    It also fetches current conditions from the SMHI API.
    """

    def __init__(self, latitude: str, longitude: str) -> None:
        """Initialize FetchSMHI with geographic coordinates.

        Args:
            latitude (str): Latitude of the location.
            longitude (str): Longitude of the location.
        """
        self._latitude = latitude
        self._longitude = longitude

    def _fetch(self) -> list[SmhiForecast]:
        """Fetch forecast data from SMHI.

        Returns:
            list[SmhiForecast]: A list of forecast data.
        """
        log.info("Fetching data from SMHI")
        smhi = Smhi(longitude=self._longitude, latitude=self._latitude)
        forecasts: list[SmhiForecast] = smhi.get_forecast()
        log.info(f"Forecast: {len(forecasts)}")
        for forecast in forecasts:
            log.info(
                f"Forecast: {forecast.valid_time}, {forecast.temperature}, "
                f"{forecast.wind_speed}, {forecast.wind_direction}, {forecast.symbol}"
            )
        return forecasts

    def get_forecast(self) -> list[SmhiForecast]:
        """Retrieve the weather forecast for the initialized location.

        Returns:
            list: A list of forecast data.
        """
        return self._fetch()

    def get_forecast_hour(self) -> list[SmhiForecast]:
        """Retrieve the hourly weather forecast.

        Returns:
            list: A list of hourly forecast data.
        """
        return self._fetch()

    def get_current_conditions(self) -> dict[str, int]:
        """Retrieve the current weather conditions.

        Returns:
            dict: A dictionary containing current weather data.
        """
        # Placeholder implementation
        return {
            "temperature": 20,
            "wind_speed": 5,
            "wind_direction": 180,
            "symbol": 1,
        }
