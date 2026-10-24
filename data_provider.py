# data_provider.py
"""Unified data‑provider abstraction for Valora.

Environment variables
---------------------
- ``DATA_PROVIDER`` (default: ``ALPHA_VANTAGE``) – selects which
  provider implementation is used. Accepted values are ``ALPHA_VANTAGE``,
  ``FINNHUB`` and ``POLYGON``.
- ``ALPHA_VANTAGE_API_KEY`` – API key for the Alpha Vantage service.
- ``FINNHUB_API_KEY`` – API key for Finnhub.
- ``POLYGON_API_KEY`` – API key for Polygon (optional, used only for the
  paid tier).

The module exposes three high‑level functions that match the existing
code‑base naming convention:

```
get_earnings_calendar(start_date: str, end_date: str) -> List[Dict]
get_symbol_earnings(symbol: str) -> Dict
get_intraday_price(symbol: str, interval: str = "5min") -> List[Dict]
```

Internally each function delegates to the concrete provider class
(``AlphaVantageProvider`` or ``FinnhubProvider``).  If the selected
provider raises a ``DataProviderError`` the caller can decide whether to
fallback to the secondary provider – the default behaviour implemented
here is to try ``FINNHUB`` when ``ALPHA_VANTAGE`` fails.

Logging
-------
A module‑level ``logger`` (``logging.getLogger(__name__)``) is used.  The
default configuration prints ``INFO`` messages to ``stderr``; the
application may re‑configure it (e.g. JSON logging, file handlers) before
importing this module.
"""

import os
import logging
from typing import List, Dict, Any

import httpx

logger = logging.getLogger(__name__)
if not logger.handlers:
    # Configure a very lightweight default logger only once.
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(name)s – %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class DataProviderError(RuntimeError):
    """Raised when a provider call fails or returns an unexpected response."""


class BaseProvider:
    """Common interface for concrete provider implementations."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.Client(timeout=10.0)

    def get_earnings_calendar(self, start_date: str, end_date: str) -> List[Dict]:
        raise NotImplementedError

    def get_symbol_earnings(self, symbol: str) -> Dict:
        raise NotImplementedError

    def get_intraday_price(self, symbol: str, interval: str = "5min") -> List[Dict]:
        raise NotImplementedError

    def _handle_response(self, resp: httpx.Response) -> Any:
        if resp.status_code != 200:
            logger.error("HTTP %s from %s", resp.status_code, resp.url)
            raise DataProviderError(f"Unexpected status {resp.status_code}")
        try:
            return resp.json()
        except Exception as exc:
            logger.exception("Failed to parse JSON response")
            raise DataProviderError("Invalid JSON response") from exc


class AlphaVantageProvider(BaseProvider):
    BASE_URL = "https://www.alphavantage.co/query"

    def get_earnings_calendar(self, start_date: str, end_date: str) -> List[Dict]:
        # Alpha Vantage does not provide a direct calendar endpoint.
        # As a fallback we retrieve the earnings for a set of symbols
        # (the caller can pass a pre‑filtered symbol list if needed).
        logger.info("AlphaVantage: earnings calendar not directly supported – returning empty list")
        return []

    def get_symbol_earnings(self, symbol: str) -> Dict:
        params = {
            "function": "EARNINGS",
            "symbol": symbol,
            "apikey": self.api_key,
        }
        resp = self.client.get(self.BASE_URL, params=params)
        data = self._handle_response(resp)
        # Alpha Vantage wraps earnings under "quarterlyEarnings" & "annualEarnings"
        return data

    def get_intraday_price(self, symbol: str, interval: str = "5min") -> List[Dict]:
        params = {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": symbol,
            "interval": interval,
            "apikey": self.api_key,
            "outputsize": "compact",
        }
        resp = self.client.get(self.BASE_URL, params=params)
        data = self._handle_response(resp)
        # The payload key varies by interval, e.g. "Time Series (5min)"
        key = f"Time Series ({interval})"
        return data.get(key, {})


class FinnhubProvider(BaseProvider):
    BASE_URL = "https://finnhub.io/api/v1"

    def get_earnings_calendar(self, start_date: str, end_date: str) -> List[Dict]:
        endpoint = f"{self.BASE_URL}/calendar/earnings"
        params = {
            "from": start_date,
            "to": end_date,
            "token": self.api_key,
        }
        resp = self.client.get(endpoint, params=params)
        data = self._handle_response(resp)
        return data.get("earningsCalendar", [])

    def get_symbol_earnings(self, symbol: str) -> Dict:
        endpoint = f"{self.BASE_URL}/stock/earnings"
        params = {"symbol": symbol, "token": self.api_key}
        resp = self.client.get(endpoint, params=params)
        return self._handle_response(resp)

    def get_intraday_price(self, symbol: str, interval: str = "5") -> List[Dict]:
        # Finnhub uses numeric intervals: 1, 5, 15, 30, 60 (minutes)
        interval_map = {"1min": "1", "5min": "5", "15min": "15", "30min": "30", "60min": "60"}
        fin_interval = interval_map.get(interval, "5")
        endpoint = f"{self.BASE_URL}/stock/candle"
        params = {
            "symbol": symbol,
            "resolution": fin_interval,
            "from": "0",  # caller can replace with epoch seconds if needed
            "to": "2147483647",
            "token": self.api_key,
        }
        resp = self.client.get(endpoint, params=params)
        return self._handle_response(resp)


def _load_provider() -> BaseProvider:
    provider_name = os.getenv("DATA_PROVIDER", "ALPHA_VANTAGE").upper()
    logger.info("Loading data provider: %s", provider_name)
    if provider_name == "FINNHUB":
        api_key = os.getenv("FINNHUB_API_KEY")
        if not api_key:
            raise DataProviderError("FINNHUB_API_KEY not set")
        return FinnhubProvider(api_key)
    # Default / fallback to Alpha Vantage
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        raise DataProviderError("ALPHA_VANTAGE_API_KEY not set")
    return AlphaVantageProvider(api_key)


# Public façade – callers import these three functions.
def get_earnings_calendar(start_date: str, end_date: str) -> List[Dict]:
    try:
        provider = _load_provider()
        return provider.get_earnings_calendar(start_date, end_date)
    except DataProviderError as exc:
        logger.warning("Primary provider failed: %s", exc)
        # Attempt simple fallback to Finnhub if the primary was Alpha Vantage
        if isinstance(provider, AlphaVantageProvider):
            try:
                fallback_key = os.getenv("FINNHUB_API_KEY")
                if fallback_key:
                    logger.info("Falling back to Finnhub provider for earnings calendar")
                    return FinnhubProvider(fallback_key).get_earnings_calendar(start_date, end_date)
            except DataProviderError as fallback_exc:
                logger.error("Fallback also failed: %s", fallback_exc)
        raise


def get_symbol_earnings(symbol: str) -> Dict:
    provider = _load_provider()
    return provider.get_symbol_earnings(symbol)


def get_intraday_price(symbol: str, interval: str = "5min") -> List[Dict]:
    provider = _load_provider()
    return provider.get_intraday_price(symbol, interval)
