import argparse
import logging
from importlib.metadata import version

from python_support.configuration import MyConfig  # type: ignore
from python_support.logging import MyLogger  # type: ignore

from .fetching.fetch_smhi import FetchSMHI

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


if __name__ == "__main__":
    main()
