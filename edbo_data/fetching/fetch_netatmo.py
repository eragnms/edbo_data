"""Fetch data from my Netatmo weather station

- https://github.com/philippelt/netatmo-api-python
"""

import logging

import lnetatmo  # type: ignore

log = logging.getLogger("EDBO_DATA")


class FetchNetatmo:
    """FetchNetatmo is responsible for fetching weather data from a Netatmo
    weather station.

    It fetches data from the Netatmo API.
    """

    def __init__(self) -> None:
        """Initialize FetchNetatmo."""
        self._authorization = lnetatmo.ClientAuth()

    def get_data(self) -> dict[str, dict[str, int | str | float]]:
        """Retrieve the weather data from the Netatmo object.

        Returns:
            dict: A dictionary of weather data.
        """
        weatherData = lnetatmo.WeatherStationData(self._authorization)
        return {
            "indoor": {
                "temperature": weatherData.lastData()["Indoor"]["Temperature"],
                "co2": weatherData.lastData()["Indoor"]["CO2"],
                "humidity": weatherData.lastData()["Indoor"]["Humidity"],
                "pressure": weatherData.lastData()["Indoor"]["Pressure"],
                "absolute_pressure": weatherData.lastData()["Indoor"][
                    "AbsolutePressure"
                ],
                "noise": weatherData.lastData()["Indoor"]["Noise"],
                "min_temp": weatherData.lastData()["Indoor"]["min_temp"],
                "max_temp": weatherData.lastData()["Indoor"]["max_temp"],
                "date_min_temp": weatherData.lastData()["Indoor"]["date_min_temp"],
                "date_max_temp": weatherData.lastData()["Indoor"]["date_max_temp"],
                "temp_trend": weatherData.lastData()["Indoor"]["temp_trend"],
                "pressure_trend": weatherData.lastData()["Indoor"]["pressure_trend"],
            },
            "outdoor": {
                "temperature": weatherData.lastData()["Outdoor"]["Temperature"],
                "humidity": weatherData.lastData()["Outdoor"]["Humidity"],
                "min_temp": weatherData.lastData()["Outdoor"]["min_temp"],
                "max_temp": weatherData.lastData()["Outdoor"]["max_temp"],
                "date_min_temp": weatherData.lastData()["Outdoor"]["date_min_temp"],
                "date_max_temp": weatherData.lastData()["Outdoor"]["date_max_temp"],
                "battery_percent": weatherData.lastData()["Outdoor"]["battery_percent"],
                "rf_status": weatherData.lastData()["Outdoor"]["rf_status"],
            },
        }
