import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Body as FastAPIBody
from pydantic import BaseModel
from sqlmodel import Session

from app.core.db import init_db, get_session
from app.service.get_service import store_raw_response_and_return_price_point
from app.service.post_service import creating_polling_job

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


class Body(BaseModel):
    symbols: list[str]
    interval: int
    provider: str


@app.get("/prices/latest")
def get_Price_Data(symbol: str, provider: str = "yfinance", session: Session = Depends(get_session)):
    logger.info(f"Fetching latest price data for symbol: {symbol} from provider: {provider}")
    return store_raw_response_and_return_price_point(symbol, session, provider)


@app.post("/prices/poll")
def create_polling_job(body: Body = FastAPIBody(...), session: Session = Depends(get_session)):
    logger.info(
        f"Creating polling job for symbols: {body.symbols} with interval: {body.interval} seconds from provider: {body.provider}")
    return creating_polling_job(body.symbols, body.interval, body.provider, session)
