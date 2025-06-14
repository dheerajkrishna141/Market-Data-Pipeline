import datetime
import uuid

from sqlmodel import Session
import yfinance as yf
from fastapi import HTTPException

from app.models.models import RawResponse, PricePoint
from scripts.kafkaProducer import publish_price_event
from app.service.YFinance_service import YFinanceProvider
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def store_raw_response_and_return_price_point(symbol:str, session:Session, provider: str) :
    logger.info("Fetching raw data for symbol:", symbol)
    yf_provider = YFinanceProvider()
    raw_data = yf_provider.fetch_price_data(symbol)
    result = yf_provider.parse_price_data(raw_data)

    if raw_data is None or result is None:
        logger.error(f"Failed to fetch or parse data for symbol: {symbol}")
        raise HTTPException(status_code=404, detail=f"No data found for symbol: {symbol}")

    current_price, timestamp = result
    response_id= uuid.uuid4()



    processed_data = PricePoint(id = uuid.uuid4(), price = current_price, symbol=symbol, provider=provider, timestamp=timestamp, raw_response_id=response_id)



    new_entry = RawResponse(
        id=response_id,
        response_data = raw_data,
        provider= provider,
        symbol=symbol
    )

    try:
        publish_price_event(processed_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error publishing price event: {str(e)}")

    try:
        session.add(new_entry)
        session.add(processed_data)
        session.commit()
        session.refresh(new_entry)
        session.refresh(processed_data)
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error storing raw response: {str(e)}")
    finally:
        session.close()
    return {"message": "Raw response stored successfully", "price":current_price, "symbol": new_entry.symbol,"timestamp": new_entry.received_at, "provider": new_entry.provider}




