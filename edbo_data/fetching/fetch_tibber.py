"""Fetch data from Tibber API"""

import asyncio
from typing import Any

import tibber  # type: ignore
import tibber.const  # type: ignore


class FetchTibber:
    """FetchTibber is responsible for fetching energy data from the Tibber API.

    It fetches the current price and the current energy consumption.
    """

    def __init__(
        self, token: str = tibber.const.DEMO_TOKEN, user_agent: str = "change_this"
    ) -> None:
        """Initialize the FetchTibber class.

        Args:
            token (str): The API token for Tibber. Defaults to the DEMO_TOKEN
                         from tibber.const.
            user_agent (str): A custom user agent for Tibber. Defaults to
                              "change_this".
        """
        self.token = token
        self.user_agent = user_agent

    def get_data(self) -> dict[str, Any]:
        """Synchronous-looking method that wraps the actual async Tibber calls.

        Returns:
            dict[str, Any]: Dictionary containing various data fetched from Tibber.
        """
        return asyncio.run(self._get_data())

    def get_consumption_data(self) -> list[dict[Any, Any]]:
        """Public synchronous method to fetch consumption data.

        Returns:
            list[dict[Any, Any]]: Consumption data as a list of dictionaries.
        """
        return asyncio.run(self._get_consumption_data_async())

    async def _get_consumption_data_async(self) -> Any:
        """Async method that fetches consumption data using Tibber's async library.

        Steps:
            1. Create the Tibber connection.
            2. Access the home object.
            3. Fetch consumption data.
            4. Read and return the data.
            5. Clean up the connection.

        Returns:
            list[dict[Any, Any]]: New consumption data fetched.
        """
        # 1) Create the Tibber connection
        tibber_connection = tibber.Tibber(self.token, user_agent=self.user_agent)
        await tibber_connection.update_info()  # get account-level info

        # 2) Access the home object(s)
        home = tibber_connection.get_homes()[0]

        # 3) Fetch consumption data
        await home.fetch_consumption_data()

        # 4) Read it
        data = home.hourly_consumption_data

        # 5) Clean up
        await tibber_connection.close_connection()

        # Return the new data
        return data

    async def _get_data(self) -> dict[str, Any]:
        """Internal async method that interacts with the Tibber library to fetch data.

        Steps:
            1. Create Tibber connection.
            2. Update account and home info.
            3. Fetch consumption and price data.
            4. Close the connection.
            5. Return collected data.

        Returns:
            dict[str, Any]: Dictionary containing account name, address,
                            current price info, price unit, and real-time
                            consumption availability.
        """
        # Create Tibber connection
        tibber_connection = tibber.Tibber(self.token, user_agent=self.user_agent)

        # Update account info and store the account name
        await tibber_connection.update_info()
        account_name: str = tibber_connection.name

        # Retrieve the first home from the account
        home = tibber_connection.get_homes()[0]

        # Fetch consumption data
        await home.fetch_consumption_data()

        # Update home info (address, etc.)
        await home.update_info()
        address: str = home.address1

        # Update and retrieve price info
        await home.update_current_price_info()
        current_price_info: dict[str, Any] = home.current_price_info

        # Close the Tibber connection
        await tibber_connection.close_connection()

        return {
            "account_name": account_name,
            "address": address,
            "current_price_info": current_price_info,
            "price_unit": home.price_unit,
            "has_real_time_consumption": home.has_real_time_consumption,
        }
