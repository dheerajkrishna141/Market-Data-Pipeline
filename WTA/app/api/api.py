

from fastapi import FastAPI, Depends
from sqlmodel import Session
from contextlib import asynccontextmanager
import yfinance as yf

from app.core.db import init_db, get_session

from app.models.models import  RawResponse, PricePoint, SymbolAverage, PollingJob
from app.service.service import store_raw_response_and_return_price_point


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/prices/latest")
def get_Price_Data(symbol: str, provider: str = None, session: Session = Depends(get_session)):
    print("Request received for symbol:", symbol)
    return store_raw_response_and_return_price_point(symbol, session)
