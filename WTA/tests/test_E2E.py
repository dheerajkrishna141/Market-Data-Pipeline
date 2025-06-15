import os
import sys
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel, select

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.db import get_session
from app.api.api import app

from app.core.config import settings
from app.models.models import PollingJob, PricePoint, SymbolAverage

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


@pytest.mark.e2eget
def test_get_request_pipeline(test_client: TestClient, mocker):
    SYMBOL = "PYPL"

    mock_prices = [100.0, 102.0, 104.0, 106.0, 108.0]
    expected_average = sum(mock_prices) / len(mock_prices)

    mocker.patch(
        "app.service.YFinance_service.YFinanceProvider.fetch_price_data",
        side_effect=[
            {"regularMarketPrice": p, "regularMarketTime": int(time.time() + i)} for i, p in enumerate(mock_prices)
        ]
    )

    with Session(engine) as session:
        session.query(PricePoint).filter(PricePoint.symbol == SYMBOL).delete()
        session.query(SymbolAverage).filter(SymbolAverage.symbol == SYMBOL).delete()
        session.commit()

    print(f"\nSeeding 5 price points for {SYMBOL}...")

    for i in range(5):
        response = test_client.get(f"/prices/latest?symbol={SYMBOL}")
        assert response.status_code == 200
        time.sleep(0.5)

    wait_time = 10
    print(f"Waiting {wait_time} seconds for the consumer to process events...")
    time.sleep(wait_time)

    print("Verifying the result in the database...")
    with Session(engine) as session:
        statement = select(SymbolAverage).where(SymbolAverage.symbol == SYMBOL)
        result = session.exec(statement).first()

        assert result is not None, "SymbolAverage record was not created in the database!"
        assert result.moving_average == pytest.approx(expected_average)

    print(f"E2E Test Passed! Correct moving average of {result.moving_average} found for {SYMBOL}.")


@pytest.mark.e2epost
def test_post_pipeline(test_client: TestClient, mocker):
    SYMBOL = "ADBE"

    mocker.patch(
        "app.service.YFinance_service.YFinanceProvider.fetch_price_data",
        return_value={"regularMarketPrice": 200.0, "regularMarketTime": int(time.time())}

    )
    with Session(engine) as session:
        jobs = session.query(PollingJob).all()
        for job in jobs:
            if SYMBOL in job.symbols:
                session.delete(job)
        session.commit()

    req_body = {
        "symbols": [SYMBOL],
        "interval": 10,
        "provider": "yfinance"
    }

    print(f"\nCreating a polling job for {SYMBOL}...")
    response = test_client.post("/prices/poll", json=req_body)
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    wait_time = 20
    print(f"Waiting {wait_time} seconds for the poller to find and execute the job...")
    time.sleep(wait_time)

    print("Verifying the result in the database...")

    with Session(engine) as session:
        price_point_statement = select(PricePoint).where(PricePoint.symbol == SYMBOL)
        price_point_result = session.exec(price_point_statement).first()

        assert price_point_result is not None, "Poller did not create a PricePoint record!"
        # assert price_point_result.price == 200.0
        job_statement = select(PollingJob).where(PollingJob.job_id == job_id)
        job_result = session.exec(job_statement).first()

        assert job_result is not None, "PollingJob record was not found!"
        assert job_result.last_run_at is not None, "Poller did not update the job's last_run_at timestamp!"

    print(f"E2E Test Passed! Poller successfully executed job for {SYMBOL}.")
