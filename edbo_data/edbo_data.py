"""
This script serves as the entry point for the edbo_data package,
providing a command-line interface to fetch data from various sources.

For all available options, run the script with the --help flag.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from typing import Any, cast

from dateutil.parser import parse as parse_datetime  # type: ignore
from python_support.configuration import MyConfig  # type: ignore
from python_support.logging import MyLogger  # type: ignore
from rich import box  # type: ignore
from rich.console import Console  # type: ignore
from rich.table import Table  # type: ignore

from .fetching.fetch_all import FetchAll
from .fetching.fetch_netatmo import FetchNetatmo
from .fetching.fetch_smhi import FetchSMHI
from .fetching.fetch_tibber import FetchTibber

LOGGER_NAME = "EDBO_DATA"

log = logging.getLogger(LOGGER_NAME)


def main() -> None:
    """
    Parse command-line arguments and execute the corresponding data fetching routines.
    """
    parser = argparse.ArgumentParser(
        description=(
            "With no options the script will pretty print data from all sources. "
            "See README and project documentation for details."
        )
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
    parser.add_argument(
        "-fa",
        "--fetch_all",
        action="store_true",
        help="Fetch data from all sources, prints to console as a JSON string",
    )
    args = parser.parse_args()

    if args.version:
        package_version = version("edbo_data")
        print(f"Installed version of asset predictor: {package_version}")
        exit(0)

    if args.loglevel:
        numeric_level = getattr(logging, args.loglevel.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError("Invalid log level: %s" % args.loglevel)
        level = numeric_level

    config = MyConfig("ED_CONFIG")
    if config.general_log_with_timestamp == "true":
        add_timestamp = True
    else:
        add_timestamp = False
    MyLogger(add_timestamp=add_timestamp).setup_logger(
        level, LOGGER_NAME, config.general_log_file
    )

    if args.fetch_smhi:
        fetch_smhi = FetchSMHI(config.map_latitude, config.map_longitude)
        current = fetch_smhi.get_current_conditions()
        log.info(f"Current conditions: {fetch_smhi.forecast_to_conditions(current)}")
        forecast = fetch_smhi.get_forecast()
        for f in forecast:
            conditions = fetch_smhi.forecast_to_conditions(f)
            print(conditions)
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
    elif args.fetch_netatmo:
        fetch_netatmo = FetchNetatmo()
        data = fetch_netatmo.get_data()
        log.info(f"Netatmo data: {data}")
    elif args.fetch_tibber:
        tibber_token = os.environ["TIBBER_TOKEN"]
        fetcher = FetchTibber(tibber_token)
        data = fetcher.get_data()
        print("Account Name:", data["account_name"])
        print("Address:", data["address"])
        print("Current Price Info:", data["current_price_info"])
        print(data["price_unit"])
        print(f"Has real time consumption data: {data['has_real_time_consumption']}")
        print(data)
        consumption = fetcher.get_consumption_data()
        print("Consumption data (last 3 entries):", consumption[-3:])
        price_info = fetcher.get_2_days_price_info()
        print("Price info:", price_info)
    elif args.fetch_all:
        try:
            fetch_all = FetchAll(config, log)
            all_data = fetch_all.get_data()
        except Exception as e:
            log.error(f"Error fetching data: {e}")
            sys.exit(1)
        print(json.dumps(all_data))
    else:
        log.debug("Fetching data from all sources")
        present_all_data(config)


def present_all_data(config: MyConfig) -> None:
    fetch_all = FetchAll(config)
    all_data = fetch_all.get_data()
    pretty_print_data(all_data)


def pretty_print_data(all_data: dict[str, Any]) -> None:
    console = Console()

    # -----------------------------
    # 1) Indoor Data
    # -----------------------------
    if "indoor" in all_data:
        indoor_table = Table(
            title="Indoor Data",
            box=box.SIMPLE_HEAVY,
            show_lines=False,
            title_style="bold magenta",
        )
        indoor_table.add_column("Key", style="bold green")
        indoor_table.add_column("Value", style="cyan")

        for key, val in all_data["indoor"].items():
            indoor_table.add_row(str(key), str(val))

        console.print(indoor_table)

    # -----------------------------
    # 2) Outdoor Data - Current
    # -----------------------------
    if "outdoor" in all_data and "current" in all_data["outdoor"]:
        out_current_table = Table(
            title="Outdoor - Current",
            box=box.SIMPLE_HEAVY,
            show_lines=False,
            title_style="bold magenta",
        )
        out_current_table.add_column("Key", style="bold green")
        out_current_table.add_column("Value", style="cyan")

        for key, val in all_data["outdoor"]["current"].items():
            out_current_table.add_row(str(key), str(val))

        console.print(out_current_table)

    # -----------------------------------
    # 3) Outdoor Data - Forecast 24 hours
    # -----------------------------------
    if "outdoor" in all_data and "forecast_24h" in all_data["outdoor"]:
        # Build a table for daily forecast. We'll assume each day is a row.
        forecast_table = Table(
            title="Outdoor - Forecast 24 hours",
            box=box.SIMPLE_HEAVY,
            show_lines=False,
            title_style="bold magenta",
        )
        # Let’s define columns we’d like to show. Adjust as needed.
        forecast_table.add_column("Time", style="bold green")
        forecast_table.add_column("Temp", justify="right")
        forecast_table.add_column("Min", justify="right")
        forecast_table.add_column("Max", justify="right")
        forecast_table.add_column("Prec", justify="right")
        forecast_table.add_column("Wind Spd", justify="right")
        forecast_table.add_column("Wind Dir", justify="right")
        forecast_table.add_column("Humidity", justify="right")
        forecast_table.add_column("Pressure", justify="right")
        forecast_table.add_column("Symbol", justify="center")

        for date_str, forecast_data in all_data["outdoor"]["forecast_24h"].items():
            temperature = forecast_data.get("temperature", "-")
            t_min = forecast_data.get("temperature_min", "-")
            t_max = forecast_data.get("temperature_max", "-")
            precipitation = forecast_data.get("precipitation", "-")
            wind_speed = forecast_data.get("wind_speed", "-")
            wind_dir = forecast_data.get("wind_direction", "-")
            humidity = forecast_data.get("humidity", "-")
            pressure = forecast_data.get("pressure", "-")
            symbol_str = forecast_data.get("symbol_string", "-")

            forecast_table.add_row(
                date_str,
                str(temperature),
                str(t_min),
                str(t_max),
                str(precipitation),
                str(wind_speed),
                str(wind_dir),
                str(humidity),
                str(pressure),
                symbol_str,
            )

        console.print(forecast_table)

    # ----------------------------------
    # 3) Outdoor Data - Forecast 10 days
    # ----------------------------------
    if "outdoor" in all_data and "forecast" in all_data["outdoor"]:
        # Build a table for daily forecast. We'll assume each day is a row.
        forecast_table = Table(
            title="Outdoor - Forecast 10 days",
            box=box.SIMPLE_HEAVY,
            show_lines=False,
            title_style="bold magenta",
        )
        # Let’s define columns we’d like to show. Adjust as needed.
        forecast_table.add_column("Date", style="bold green")
        forecast_table.add_column("Temp", justify="right")
        forecast_table.add_column("Min", justify="right")
        forecast_table.add_column("Max", justify="right")
        forecast_table.add_column("Prec", justify="right")
        forecast_table.add_column("Wind Spd", justify="right")
        forecast_table.add_column("Wind Dir", justify="right")
        forecast_table.add_column("Humidity", justify="right")
        forecast_table.add_column("Pressure", justify="right")
        forecast_table.add_column("Symbol", justify="center")

        for date_str, forecast_data in all_data["outdoor"]["forecast"].items():
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%a %d %b")
            temperature = forecast_data.get("temperature", "-")
            t_min = forecast_data.get("temperature_min", "-")
            t_max = forecast_data.get("temperature_max", "-")
            precipitation = forecast_data.get("precipitation", "-")
            wind_speed = forecast_data.get("wind_speed", "-")
            wind_dir = forecast_data.get("wind_direction", "-")
            humidity = forecast_data.get("humidity", "-")
            pressure = forecast_data.get("pressure", "-")
            symbol_str = forecast_data.get("symbol_string", "-")

            forecast_table.add_row(
                formatted_date,
                str(temperature),
                str(t_min),
                str(t_max),
                str(precipitation),
                str(wind_speed),
                str(wind_dir),
                str(humidity),
                str(pressure),
                symbol_str,
            )

        console.print(forecast_table)

    # -----------------------------
    # 4) Energy Data - Current Price
    # -----------------------------
    if "energy" in all_data and "current_price" in all_data["energy"]:
        price_data = all_data["energy"]["current_price"]

        energy_price_table = Table(
            title="Energy - Current Price",
            box=box.SIMPLE_HEAVY,
            show_lines=False,
            title_style="bold magenta",
        )
        energy_price_table.add_column("Key", style="bold green")
        energy_price_table.add_column("Value", style="cyan")

        for key, val in price_data.items():
            energy_price_table.add_row(str(key), str(val))

        console.print(energy_price_table)

    # Check if we have energy consumption data
    if "energy" not in all_data or "consumption" not in all_data["energy"]:
        return

    # 1) Aggregate the hourly data by date
    #    We'll do a "consumption-weighted" average of unitPrice.
    aggregated: dict[str, dict[str, float]] = {}
    # Structure of aggregated[date_str] = {
    #    "consumption": float,
    #    "cost": float,
    #    "price_times_consumption": float  # for computing weighted average
    # }

    for dt_str, cdata in all_data["energy"]["consumption"].items():
        # dt_str looks like "2025-01-17 21:00:00"
        date_only = dt_str[:10]  # "2025-01-17"
        try:
            consumption = float(cdata.get("consumption", 0.0))
            cost = float(cdata.get("cost", 0.0))
            unit_price = float(cdata.get("unitPrice", 0.0))
        except ValueError:
            continue
        except TypeError:
            continue

        if date_only not in aggregated:
            aggregated[date_only] = {
                "consumption": 0.0,
                "cost": 0.0,
                "price_times_consumption": 0.0,
            }

        aggregated[date_only]["consumption"] += consumption
        aggregated[date_only]["cost"] += cost
        aggregated[date_only]["price_times_consumption"] += unit_price * consumption

    # 2) Create a Rich table
    consumption_table = Table(
        title="Energy - Daily Aggregated Consumption",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
        title_style="bold magenta",
    )
    consumption_table.add_column("Date", style="bold green", no_wrap=True)
    consumption_table.add_column("Consumption", justify="right")
    consumption_table.add_column("Unit Price", justify="right")
    consumption_table.add_column("Cost", justify="right")

    # 3) Populate table rows (sorted by date)
    for date_str in sorted(aggregated.keys()):
        total_cons = aggregated[date_str]["consumption"]
        price_times_cons = aggregated[date_str]["price_times_consumption"]
        total_cost = aggregated[date_str]["cost"]

        # Compute consumption-weighted average price
        if total_cons > 0:
            avg_price = price_times_cons / total_cons
        else:
            avg_price = 0.0

        consumption_table.add_row(
            date_str,
            f"{total_cons:.2f}",
            f"{avg_price:.2f}",
            f"{total_cost:.2f}",
        )

    console.print(consumption_table)

    # ------------------------------
    # 4) Energy Data - Future Price
    # ------------------------------
    # Collect all entries that are strictly in the future.
    # We'll parse the datetime string, convert to UTC, then compare with "now" in UTC.
    now_utc = datetime.now(timezone.utc)
    future_entries = []

    for dt_str, price_value in all_data["energy"]["prices"].items():
        dt_parsed = parse_datetime(dt_str)  # dt will have a tz from the string
        dt_utc = dt_parsed.astimezone(timezone.utc)
        if dt_utc > now_utc:
            future_entries.append((dt_utc, price_value))

    # If no future prices exist, optionally show a message or exit.
    if not future_entries:
        console.print("[bold red]No future prices available.[/bold red]")
        return

    # Sort the entries chronologically
    future_entries.sort(key=lambda x: x[0])

    # Build the Rich table
    price_table = Table(
        title="Energy - Future Price Info",
        title_style="bold magenta",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
    )
    price_table.add_column("Time (Local)", style="bold green", no_wrap=True)
    price_table.add_column("Price [SEK/kWh]", justify="right")

    for dt_utc, price_value in future_entries:
        # Convert UTC time to local time (omit `.astimezone()` if
        # you want to stay in UTC)
        dt_local = dt_utc.astimezone()
        # Format just hours, minutes, seconds (24-hour format)
        time_str = dt_local.strftime("%H:%M:%S")
        # Price with two decimal digits
        price_str = f"{price_value:.2f}"
        price_table.add_row(time_str, price_str)

    console.print(price_table)


if __name__ == "__main__":
    main()
