"""Fetch data from SMHI API

Uses the SMHI API to fetch weather data for a specific location see:

- http://opendata.smhi.se/apidocs/metfcst/index.html
- https://github.com/joysoftware/pypi_smhi?tab=readme-ov-file
"""

from smhi.smhi_lib import Smhi, SmhiForecast  # type: ignore


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

    def get_forecast(self) -> list[SmhiForecast]:
        """Retrieve the weather forecast for the initialized location.

        Returns:
            list: A list of forecast data.
        """
        smhi = Smhi(longitude=self._longitude, latitude=self._latitude)
        forecasts: list[SmhiForecast] = smhi.get_forecast()
        return forecasts[1:]

    def get_forecast_hour(self) -> list[SmhiForecast]:
        """Retrieve the hourly weather forecast.

        Returns:
            list: A list of hourly forecast data.
        """
        smhi = Smhi(longitude=self._longitude, latitude=self._latitude)
        forecasts: list[SmhiForecast] = smhi.get_forecast_hour()
        return forecasts[1:]

    def get_current_conditions(self) -> SmhiForecast:
        """Retrieve the current weather conditions.

        Returns:
            SmhiForecast: The current weather conditions.
        """
        smhi = Smhi(longitude=self._longitude, latitude=self._latitude)
        forecasts: list[SmhiForecast] = smhi.get_forecast()
        return forecasts[0]

    def forecast_to_conditions(
        self, forecast: SmhiForecast
    ) -> dict[str, int | str | float]:
        """Convert a forecast to a dictionary of conditions.

        Args:
            forecast (SmhiForecast): The forecast to convert.

        Returns:
            dict: A dictionary of conditions.
        """
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

    def precipitation_to_string(self, precipitation: int) -> str:
        """Convert a precipitation code to a string.

        Args:
            precipitation (int): The precipitation code.

        Returns:
            str: The precipitation as a string.
        """
        match precipitation:
            case 0:
                return "No precipitation"
            case 1:
                return "Snow"
            case 2:
                return "Snow and rain"
            case 3:
                return "Rain"
            case 4:
                return "Drizzle"
            case 5:
                return "Freezing rain"
            case 6:
                return "Freezing drizzle"
            case _:
                raise ValueError(f"Unknown precipitation code: {precipitation}")

    def symbol_to_string(self, symbol: int) -> str:
        """Convert a symbol code to a string.

        Args:
            symbol (int): The symbol code.

        Returns:
            str: The symbol as a string.
        """
        match symbol:
            case 1:
                return "Clear sky"
            case 2:
                return "Nearly clear sky"
            case 3:
                return "Variable cloudiness"
            case 4:
                return "Halfclear sky"
            case 5:
                return "Cloudy sky"
            case 6:
                return "Overcast"
            case 7:
                return "Fog"
            case 8:
                return "Light rain showers"
            case 9:
                return "Moderate rain showers"
            case 10:
                return "Heavy rain showers"
            case 11:
                return "Thunderstorm"
            case 12:
                return "Light sleet showers"
            case 13:
                return "Moderate sleet showers"
            case 14:
                return "Heavy sleet showers"
            case 15:
                return "Light snow showers"
            case 16:
                return "Moderate snow showers"
            case 17:
                return "Heavy snow showers"
            case 18:
                return "Light rain"
            case 19:
                return "Moderate rain"
            case 20:
                return "Heavy rain"
            case 21:
                return "Thunder"
            case 22:
                return "Light sleet"
            case 23:
                return "Moderate sleet"
            case 24:
                return "Heavy sleet"
            case 25:
                return "Light snowfall"
            case 26:
                return "Moderate snowfall"
            case 27:
                return "Heavy snowfall"
            case _:
                raise ValueError(f"Unknown symbol code: {symbol}")
