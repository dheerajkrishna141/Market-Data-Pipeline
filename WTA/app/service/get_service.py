import datetime
import uuid

from sqlmodel import Session
import yfinance as yf
from fastapi import HTTPException

from app.models.models import RawResponse, PricePoint
from scripts.kafkaProducer import publish_price_event


def store_raw_response_and_return_price_point(symbol:str, session:Session):
    print("Fetching raw data for symbol:", symbol)
    ticker = yf.Ticker(symbol)
    raw_data = ticker.info
    current_price = ticker.fast_info.last_price
    response_id= uuid.uuid4()
    raw_response = {

        "provider": "yfinance",
        "symbol": symbol,
        "response_data": raw_data
    }


    processed_data = PricePoint(id = uuid.uuid4(), price = current_price, symbol=symbol, provider=raw_response['provider'], timestamp=datetime.datetime.utcnow(), raw_response_id=response_id)



    new_entry = RawResponse(
        id=response_id,
        response_data = raw_response['response_data'],
        provider=raw_response['provider'],
        symbol=raw_response['symbol']
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




