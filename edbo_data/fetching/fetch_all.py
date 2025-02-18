"""Fetch data from all sources."""

import logging
from datetime import datetime
from typing import Any, cast

from python_support.configuration import MyConfig  # type: ignore

from .fetch_netatmo import FetchNetatmo
from .fetch_smhi import FetchSMHI
from .fetch_tibber import FetchTibber


class FetchAll:
    def __init__(self, config: MyConfig, logger: logging.Logger | None = None) -> None:
        self._config = config
        self._log = logger if logger is not None else logging.getLogger(__name__)

    def get_data(self) -> dict[str, Any]:
        # Fetch Netatmo data
        try:
            netatmo_data: dict[str, Any] = FetchNetatmo(self._log).get_data()
        except Exception as e:
            self._log.error(f"Failed to fetch Netatmo data: {e}")
            raise e

        # Fetch Tibber data
        tibber_token = self._config.tibber_token
        if not tibber_token:
            raise ValueError("TIBBER_TOKEN must be set")
        fetch_tibber = FetchTibber(token=tibber_token, logger=self._log)
        try:
            tibber_data: dict[str, Any] = fetch_tibber.get_data()
        except Exception as e:
            self._log.error(f"Failed to fetch Tibber data: {e}")
            raise e
        try:
            energy_data: list[dict[str, Any]] = fetch_tibber.get_consumption_data()
        except Exception as e:
            self._log.error(f"Failed to fetch Tibber consumption data: {e}")
            raise e
        try:
            price_data: dict[str, Any] = fetch_tibber.get_2_days_price_info()
        except Exception as e:
            self._log.error(f"Failed to fetch Tibber price data: {e}")
            raise e

        # Fetch SMHI data
        try:
            fetch_smhi = FetchSMHI(
                self._config.map_latitude, self._config.map_longitude, self._log
            )
        except Exception as e:
            self._log.error(f"Failed to fetch SMHI data: {e}")
            raise e
        current_smhi_data: dict[str, Any] = fetch_smhi.get_current_conditions()
        forecast_smhi_data: list[dict[str, Any]] = fetch_smhi.get_forecast()
        forecast_h_smhi_data: list[dict[str, Any]] = fetch_smhi.get_forecast_hour()
        forecast_24h_smhi_data = forecast_h_smhi_data[1:25]

        # Build final data structure
        all_data: dict[str, Any] = {}

        # Copy/merge Netatmo data at the top level
        all_data.update(netatmo_data)

        # --- Outdoor data ---
        all_data["outdoor"] = {}
        current: dict[str, Any] = fetch_smhi.forecast_to_conditions(current_smhi_data)
        # We'll remove the valid_time from the 'current' block
        del current["valid_time"]
        all_data["outdoor"]["current"] = current
        # Check if the Netatmo outdoor data is available and if so, use it
        if "outdoor" in netatmo_data:
            if netatmo_data["outdoor"]["temperature"] > -999:
                self._log.info("Netatmo outdoor data is available, using it")
                all_data["outdoor"]["current"]["temperature"] = netatmo_data["outdoor"][
                    "temperature"
                ]
            if netatmo_data["outdoor"]["min_temp"] > -999:
                all_data["outdoor"]["current"]["temperature_min"] = netatmo_data[
                    "outdoor"
                ]["min_temp"]
            if netatmo_data["outdoor"]["max_temp"] > -999:
                all_data["outdoor"]["current"]["temperature_max"] = netatmo_data[
                    "outdoor"
                ]["max_temp"]
            if netatmo_data["outdoor"]["humidity"] > -999:
                all_data["outdoor"]["current"]["humidity"] = netatmo_data["outdoor"][
                    "humidity"
                ]

        # Create the "forecast" subdict
        all_data["outdoor"]["forecast"] = {}
        for entry in forecast_smhi_data:
            conditions: dict[str, Any] = fetch_smhi.forecast_to_conditions(entry)
            valid_time = cast(datetime, conditions["valid_time"])
            date_str = valid_time.strftime("%Y-%m-%d")

            forecast: dict[str, Any] = {
                "temperature": conditions["temperature"],
                "temperature_min": conditions["temperature_min"],
                "temperature_max": conditions["temperature_max"],
                "precipitation": conditions["precipitation"],
                "wind_speed": conditions["wind_speed"],
                "wind_direction": conditions["wind_direction"],
                "wind_gust": conditions["wind_gust"],
                "symbol": conditions["symbol"],
                "symbol_string": conditions["symbol_string"],
                "humidity": conditions["humidity"],
                "pressure": conditions["pressure"],
                "precipitation_string": conditions["precipitation_string"],
            }
            all_data["outdoor"]["forecast"][date_str] = forecast

        # Create the "forecast_24h" subdict
        all_data["outdoor"]["forecast_24h"] = {}
        for entry in forecast_24h_smhi_data:
            conditions_24h: dict[str, Any] = fetch_smhi.forecast_to_conditions(entry)
            valid_time = cast(datetime, conditions_24h["valid_time"])
            date_str = valid_time.strftime("%H:%M:%S")

            forecast_24h: dict[str, Any] = {
                "temperature": conditions_24h["temperature"],
                "temperature_min": conditions_24h["temperature_min"],
                "temperature_max": conditions_24h["temperature_max"],
                "precipitation": conditions_24h["precipitation"],
                "wind_speed": conditions_24h["wind_speed"],
                "wind_direction": conditions_24h["wind_direction"],
                "wind_gust": conditions_24h["wind_gust"],
                "symbol": conditions_24h["symbol"],
                "symbol_string": conditions_24h["symbol_string"],
                "humidity": conditions_24h["humidity"],
                "pressure": conditions_24h["pressure"],
                "precipitation_string": conditions_24h["precipitation_string"],
            }
            all_data["outdoor"]["forecast_24h"][date_str] = forecast_24h

        # --- Energy data ---
        all_data["energy"] = {}
        all_data["energy"]["current_price"] = tibber_data["current_price_info"]
        all_data["energy"]["consumption"] = {}

        for entry in energy_data:
            date_str = entry["from"][0:10] + " " + entry["from"][11:19]
            del entry["from"]
            all_data["energy"]["consumption"][date_str] = entry

        all_data["energy"]["prices"] = price_data

        return all_data
