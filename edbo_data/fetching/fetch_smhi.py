"""Fetch data from SMHI API

Uses the SMHI API to fetch weather data for a specific location see,
- http://opendata.smhi.se/apidocs/metfcst/index.html
- https://github.com/joysoftware/pypi_smhi?tab=readme-ov-file
"""

import logging

from smhi.smhi_lib import Smhi, SmhiForecast  # type: ignore

log = logging.getLogger("EDBO_DATA")


class FetchSMHI:
    def __init__(self) -> None:
        pass

    def fetch(self) -> list[SmhiForecast]:
        log.info("Fetching data from SMHI")
        smhi = Smhi(longitude="18.152", latitude="59.192")
        forecasts: list[SmhiForecast] = smhi.get_forecast_hour()
        log.info(f"Forecast: {len(forecasts)}")
        for forecast in forecasts:
            log.info(
                f"Forecast: {forecast.valid_time}, {forecast.temperature}, "
                f"{forecast.wind_speed}, {forecast.wind_direction}, {forecast.symbol}"
            )
        return forecasts
