"""Weather provider selection with automatic fallback.

Picks a primary weather forecast provider from configuration and wraps it
with one or more fallbacks. If the primary provider raises during a call,
the fallback is tried next and a warning is logged.

Configuration:
    [WEATHER]
    provider = smhi       # primary provider: "smhi" or "open_meteo"
    fallback = open_meteo # optional, fallback provider on primary failure
                          # (defaults to the "other" provider if unset)

When the `[WEATHER]` section is missing entirely the default is
`provider=smhi`, `fallback=open_meteo` — which matches historical behaviour
while providing automatic resilience against SMHI outages.
"""

from __future__ import annotations

import logging
import time
import urllib.error
from typing import Any, Callable

from smhi.smhi_lib import SmhiForecast  # type: ignore

from .fetch_open_meteo import FetchOpenMeteo
from .fetch_smhi import FetchSMHI
from .weather_base import BaseForecastProvider

_PROVIDERS: dict[str, type[BaseForecastProvider]] = {
    "smhi": FetchSMHI,
    "open_meteo": FetchOpenMeteo,
}

# For each primary, the default fallback if none is configured.
_DEFAULT_FALLBACK = {
    "smhi": "open_meteo",
    "open_meteo": "smhi",
}


def _read_config_value(config: Any, attr: str, default: str) -> str:
    """Read an attribute from a MyConfig-like object, returning default if missing."""
    try:
        value = getattr(config, attr)
    except AttributeError:
        return default
    if not value:
        return default
    return str(value).strip().lower()


_TRANSIENT_HTTP_CODES = {502, 503, 504, 429}


def _is_transient(exc: Exception | None) -> bool:
    """Return True if the exception looks like a transient HTTP error."""
    if exc is None:
        return False
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in _TRANSIENT_HTTP_CODES
    msg = str(exc)
    return any(f"HTTP Error {c}" in msg for c in _TRANSIENT_HTTP_CODES)


class WeatherProviderWithFallback(BaseForecastProvider):
    """A weather provider that tries a primary, then one or more fallbacks.

    Each public method (get_forecast, get_forecast_hour, get_current_conditions)
    iterates providers in order; the first successful result is returned.
    Caching is per-call, so a single `get_data()` pass only logs a fallback
    switch once even if multiple methods are called.
    """

    name = "with_fallback"

    def __init__(
        self,
        providers: list[BaseForecastProvider],
        logger: logging.Logger | None = None,
    ) -> None:
        if not providers:
            raise ValueError("At least one provider is required")
        # Use the primary's coordinates for the base class (cosmetic only).
        first = providers[0]
        super().__init__(first._latitude, first._longitude, logger)
        self._providers = providers
        self._active_index = 0
        # Remember the originally-configured primary so callers can detect
        # whether a fallback was used during this wrapper's lifetime.
        self._primary_name = providers[0].name
        self._used_fallback = False

    @property
    def active_provider(self) -> BaseForecastProvider:
        return self._providers[self._active_index]

    @property
    def primary_name(self) -> str:
        """Name of the originally-configured primary provider."""
        return self._primary_name

    @property
    def used_fallback(self) -> bool:
        """True if any call has fallen back from the primary provider."""
        return self._used_fallback

    def _try_each(
        self,
        method_name: str,
        call: Callable[[BaseForecastProvider], Any],
        retries: int = 2,
        retry_delay: float = 5.0,
    ) -> Any:
        """Try each provider in order; on total failure, wait and retry.

        One "round" iterates all providers. If every provider fails with a
        transient HTTP error (5xx) the round is retried after *retry_delay*
        seconds, up to *retries* extra rounds. Non-transient errors (e.g.
        404) still cause an immediate skip to the next provider within a
        round but do NOT block retries of other providers in later rounds.
        """
        last_error: Exception | None = None

        for attempt in range(1 + retries):
            if attempt > 0:
                self._log.info(
                    "Retrying weather providers for %s "
                    "(attempt %d/%d, waiting %.0fs)...",
                    method_name,
                    attempt + 1,
                    1 + retries,
                    retry_delay,
                )
                time.sleep(retry_delay)

            for idx, provider in enumerate(self._providers):
                try:
                    result = call(provider)
                    if idx != self._active_index:
                        self._log.warning(
                            "Weather provider fell back from '%s' to '%s' for %s",
                            self._providers[self._active_index].name,
                            provider.name,
                            method_name,
                        )
                        self._active_index = idx
                    # Any call that ends on a non-primary provider counts as
                    # having used the fallback, even if subsequent calls succeed
                    # on the primary again.
                    if idx != 0:
                        self._used_fallback = True
                    return result
                except Exception as exc:  # noqa: BLE001 - we want to try next provider
                    self._log.warning(
                        "Weather provider '%s' failed on %s: %s",
                        provider.name,
                        method_name,
                        exc,
                    )
                    last_error = exc

            # If no error in this round was transient, retrying won't help.
            if not _is_transient(last_error):
                break

        assert last_error is not None
        raise last_error

    def get_forecast(self) -> list[SmhiForecast]:
        result: list[SmhiForecast] = self._try_each(
            "get_forecast", lambda p: p.get_forecast()
        )
        return result

    def get_forecast_hour(self) -> list[SmhiForecast]:
        result: list[SmhiForecast] = self._try_each(
            "get_forecast_hour", lambda p: p.get_forecast_hour()
        )
        return result

    def get_current_conditions(self) -> SmhiForecast:
        result: SmhiForecast = self._try_each(
            "get_current_conditions", lambda p: p.get_current_conditions()
        )
        return result


def create_weather_provider(
    config: Any, logger: logging.Logger | None = None
) -> BaseForecastProvider:
    """Build the configured weather provider, wrapped with fallback.

    Reads `config.weather_provider` (primary) and `config.weather_fallback`
    (secondary). Unknown provider names raise `ValueError`. A missing
    `[WEATHER]` section defaults to SMHI primary with Open-Meteo fallback.
    """
    log = logger if logger is not None else logging.getLogger(__name__)

    latitude = config.map_latitude
    longitude = config.map_longitude

    primary_name = _read_config_value(config, "weather_provider", "smhi")
    if primary_name not in _PROVIDERS:
        raise ValueError(
            f"Unknown weather provider '{primary_name}'. "
            f"Valid options: {sorted(_PROVIDERS)}"
        )

    default_fallback = _DEFAULT_FALLBACK[primary_name]
    fallback_name = _read_config_value(config, "weather_fallback", default_fallback)

    # "none" / "" disables fallback entirely.
    if fallback_name in {"none", "off", "disabled"}:
        fallback_name = ""

    if fallback_name and fallback_name not in _PROVIDERS:
        raise ValueError(
            f"Unknown weather fallback provider '{fallback_name}'. "
            f"Valid options: {sorted(_PROVIDERS)} or 'none'"
        )

    providers: list[BaseForecastProvider] = [
        _PROVIDERS[primary_name](latitude, longitude, log)
    ]
    if fallback_name and fallback_name != primary_name:
        providers.append(_PROVIDERS[fallback_name](latitude, longitude, log))

    log.info(
        "Weather provider: primary=%s fallback=%s",
        primary_name,
        fallback_name or "none",
    )

    if len(providers) == 1:
        return providers[0]
    return WeatherProviderWithFallback(providers, logger=log)
