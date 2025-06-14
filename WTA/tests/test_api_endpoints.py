import os
import sys

import pytest
from click.termui import raw_terminal
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel, select

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.db import get_session
from app.api.api import app

from app.core.config import settings
from app.models.models import PollingJob, RawResponse

engine = create_engine(settings.TEST_DATABASE_URL)


def override_get_session():
    with Session(engine) as session:
        yield session


app.dependency_overrides[get_session] = override_get_session


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    SQLModel.metadata.create_all(bind=engine)



@pytest.fixture(scope="function")
def test_client():
    with TestClient(app) as client:
        yield client

def test_get_latest_price(test_client: TestClient):
    response = test_client.get(
        "/prices/latest",
        params={"symbol": "ADBE", "provider": "yfinance"}
    )
    print("testing response")
    print(response.text)
    assert response.status_code == 200
    data = response.json()
    assert "symbol" in data
    assert data["symbol"] == "ADBE"
    assert "price" in data
    assert "timestamp" in data

    with Session(engine) as db_session:
        stmt = select(RawResponse).where(RawResponse.symbol == "ADBE")
        response = db_session.exec(stmt).first()
        assert response is not None
        assert response.symbol == "ADBE"
        assert response.response_data is not None


def test_get_latest_price_not_found(test_client: TestClient):
    response = test_client.get(
        "/prices/latest",
        params={"symbol": "FAKE", "provider": "yfinance"}
    )
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "No data found for symbol: FAKE"



def test_create_polling_job(test_client: TestClient):
    response = test_client.post(
        "/prices/poll",
        json={
            "symbols": ["AAPL", "GOOGL"],
            "interval": 60,
            "provider": "yfinance"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "accepted"
    assert data["config"]["symbols"] == ["AAPL", "GOOGL"]
    assert data["config"]["interval"] == 60

    job_id = data["job_id"]

    with Session(engine) as db_session:
        stmt = select(PollingJob).where(PollingJob.job_id == job_id)
        job = db_session.exec(stmt).first();

        assert job is not None
        assert job.symbols == ["AAPL", "GOOGL"]
