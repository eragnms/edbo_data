"""Fetch data from my Netatmo weather station

- https://github.com/philippelt/netatmo-api-python

Authentication: See the installation instructions in the
documentation.
"""

import logging
from typing import Any, Optional

import lnetatmo  # type: ignore


class FetchNetatmo:
    """FetchNetatmo is responsible for fetching weather data from a Netatmo
    weather station.

    It fetches data from the Netatmo API.
    """

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        """Initialize FetchNetatmo."""
        self._log = logger if logger is not None else logging.getLogger(__name__)
        try:
            self._authorization = lnetatmo.ClientAuth()
        except Exception as e:
            self._log.error(f"Failed to authenticate with Netatmo API: {e}")
            raise

    def get_data(self) -> dict[str, dict[str, Any]]:
        """Retrieve the weather data from the Netatmo object.

        Returns:
            dict: A dictionary of weather data with all required keys.
        """
        try:
            weatherData = lnetatmo.WeatherStationData(self._authorization)
            latest_data = weatherData.lastData()
        except Exception as e:
            self._log.error(f"Failed to fetch data from Netatmo API: {e}")
            return {}

        data: dict[str, dict[str, Any]] = {}

        # Define default values with desired keys (lowercase)
        default_values = {
            "indoor": {
                "temperature": -999.0,
                "co2": -999,
                "humidity": -999.0,
                "pressure": -999.0,
                "absolute_pressure": -999.0,
                "noise": -999,
                "min_temp": -999.0,
                "max_temp": -999.0,
                "date_min_temp": "",
                "date_max_temp": "",
                "temp_trend": "",
                "pressure_trend": "",
            },
            "outdoor": {
                "temperature": -999.0,
                "humidity": -999.0,
                "min_temp": -999.0,
                "max_temp": -999.0,
                "date_min_temp": "",
                "date_max_temp": "",
                "battery_percent": -999,
                "rf_status": -999,
            },
        }

        # Define mapping from final keys to fetched data keys
        key_mapping = {
            "indoor": {
                "temperature": "Temperature",
                "co2": "CO2",
                "humidity": "Humidity",
                "pressure": "Pressure",
                "absolute_pressure": "AbsolutePressure",
                "noise": "Noise",
                "min_temp": "min_temp",
                "max_temp": "max_temp",
                "date_min_temp": "date_min_temp",
                "date_max_temp": "date_max_temp",
                "temp_trend": "temp_trend",
                "pressure_trend": "pressure_trend",
            },
            "outdoor": {
                "temperature": "Temperature",
                "humidity": "Humidity",
                "min_temp": "min_temp",
                "max_temp": "max_temp",
                "date_min_temp": "date_min_temp",
                "date_max_temp": "date_max_temp",
                "battery_percent": "battery_percent",
                "rf_status": "rf_status",
            },
        }

        # Helper function to fetch data with defaults
        def fetch_sensor_data(
            sensor_type: str, keys: dict[str, str], defaults: dict[str, Any]
        ) -> dict[str, Any]:
            sensor_data = latest_data.get(sensor_type, {})
            fetched_data = {}
            for final_key, fetched_key in keys.items():
                value = sensor_data.get(fetched_key, defaults[final_key])
                if value == defaults[final_key]:
                    self._log.warning(
                        f"Missing '{fetched_key}' in {sensor_type} data. "
                        f"Using default value: {defaults[final_key]}"
                    )
                fetched_data[final_key] = value
            return fetched_data

        # Fetch indoor data
        if "Indoor" in latest_data:
            data["indoor"] = fetch_sensor_data(
                "Indoor", key_mapping["indoor"], default_values["indoor"]
            )
        else:
            self._log.warning("No indoor data available. Using default indoor values.")
            data["indoor"] = default_values["indoor"]

        # Fetch outdoor data
        if "Outdoor" in latest_data:
            data["outdoor"] = fetch_sensor_data(
                "Outdoor", key_mapping["outdoor"], default_values["outdoor"]
            )
        else:
            self._log.warning(
                "No outdoor data available. Using default outdoor values."
            )
            data["outdoor"] = default_values["outdoor"]

        return data
