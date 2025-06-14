from datetime import datetime, timezone

from app.service.YFinance_service import YFinanceProvider

SAMPLE_YFINANCE_DATA = {
    "symbol": "FAKE",
    "regularMarketPrice": 125.50,
    "regularMarketTime": 1678886400,  # Corresponds to 2023-03-15 12:00:00 UTC
    "shortName": "Fake Stock Inc."
}


def test_fetch_price_data_success():
    provider = YFinanceProvider()
    price, timestamp = provider.parse_price_data(SAMPLE_YFINANCE_DATA)

    assert price == 125.50
    assert isinstance(timestamp, datetime)
    assert timestamp == datetime.fromtimestamp(1678886400, tz=timezone.utc)


def test_parse_price_data_missing_key():
    provider = YFinanceProvider()

    invalid_data = {
        "symbol": "FAKE",
        "regularMarketTime": 1678886400
    }

    price, timestamp = provider.parse_price_data(invalid_data)

    assert price is None
    assert timestamp is None


def test_fetch_price_data():
    provider = YFinanceProvider()
    data = provider.fetch_price_data("MSFT")

    assert data is not None
    assert "regularMarketPrice" in data
    assert "symbol" in data


def test_fetch_price_data_invalid_symbol():
    provider = YFinanceProvider()
    data = provider.fetch_price_data("FAKE")

    assert data is None or "regularMarketPrice" not in data, "Expected no valid data for invalid symbol"
