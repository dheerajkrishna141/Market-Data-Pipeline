# app/services/market_data.py

import logging
from datetime import datetime, timezone

import yfinance as yf

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class YFinanceProvider:

    def fetch_price_data(self, symbol: str):

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            if not info or info.get("regularMarketPrice") is None:
                logger.warning(f"yfinance returned no valid data for symbol: {symbol}")
                return None

            return info
        except Exception as e:
            logger.error(f"An error occurred while fetching data for {symbol} from yfinance: {e}")
            return None

    def parse_price_data(self, raw_data: dict):

        try:
            price = float(raw_data["regularMarketPrice"])

            unix_timestamp = raw_data.get("regularMarketTime")
            if unix_timestamp:
                timestamp = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)

            return price, timestamp
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Failed to parse raw yfinance data. Missing key or wrong type: {e}")
            return None, None
