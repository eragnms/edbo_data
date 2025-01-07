import argparse
import logging
import os
from datetime import datetime
from importlib.metadata import version
from typing import cast

from python_support.configuration import MyConfig  # type: ignore
from python_support.logging import MyLogger  # type: ignore

from .fetching.fetch_netatmo import FetchNetatmo
from .fetching.fetch_smhi import FetchSMHI
from .fetching.fetch_tibber import FetchTibber

LOGGER_NAME = "EDBO_DATA"

log = logging.getLogger(LOGGER_NAME)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="See README and project documentation for details."
    )
    parser.add_argument(
        "--loglevel",
        "-l",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="Displays the version of the package",
    )
    parser.add_argument(
        "-fs",
        "--fetch_smhi",
        action="store_true",
        help="Fetch data from SMHI",
    )
    parser.add_argument(
        "-fn",
        "--fetch_netatmo",
        action="store_true",
        help="Fetch data from Netatmo",
    )
    parser.add_argument(
        "-ft",
        "--fetch_tibber",
        action="store_true",
        help="Fetch data from Tibber",
    )
    args = parser.parse_args()

    if args.version:
        package_version = version("asset_predictor")
        print(f"Installed version of asset predictor: {package_version}")
        exit(0)

    if args.loglevel:
        numeric_level = getattr(logging, args.loglevel.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError("Invalid log level: %s" % args.loglevel)
        level = numeric_level
    MyLogger().setup_logger(level, LOGGER_NAME)

    config = MyConfig("ED_CONFIG")

    if args.fetch_smhi:
        fetch_smhi = FetchSMHI(config.map_latitude, config.map_longitude)
        current = fetch_smhi.get_current_conditions()
        log.info(f"Current conditions: {fetch_smhi.forecast_to_conditions(current)}")
        forecast = fetch_smhi.get_forecast()
        for f in forecast:
            conditions = fetch_smhi.forecast_to_conditions(f)
            valid_time = cast(datetime, conditions["valid_time"])
            date_str = valid_time.strftime("%A, %d %B")
            log.info(
                f"{date_str}, "
                f"{conditions['temperature_min']} to "
                f"{conditions['temperature_max']} degrees Celsius, "
                f"{conditions['precipitation']} mm precipitation, "
                f"{conditions['wind_speed']} m/s wind speed, "
                f"{conditions['wind_direction']} wind direction, "
                f"{conditions['symbol_string']}"
            )
    if args.fetch_netatmo:
        fetch_netatmo = FetchNetatmo()
        data = fetch_netatmo.get_data()
        log.info(f"Netatmo data: {data}")

    if args.fetch_tibber:
        tibber_token = os.environ["TIBBER_TOKEN"]
        fetcher = FetchTibber(tibber_token)
        data = fetcher.get_data()
        print("Account Name:", data["account_name"])
        print("Address:", data["address"])
        print("Current Price Info:", data["current_price_info"])
        print(data["price_unit"])
        print(f"Has real time consumption data: {data['has_real_time_consumption']}")
        consumption = fetcher.get_consumption_data()
        print("Consumption data (last 3 entries):", consumption[-3:])


if __name__ == "__main__":
    main()
