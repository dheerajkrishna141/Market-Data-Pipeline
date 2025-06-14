import logging
import os
import signal
import sys
import time
import uuid

from sqlalchemy import create_engine, or_, func, Interval
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.models.models import PollingJob, RawResponse, PricePoint
from app.service.YFinance_service import YFinanceProvider

from scripts.kafkaProducer import publish_price_event, flush_producer

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

try:
    engine = create_engine(settings.DATABASE_URL,
                           connect_args={"options": "-c timezone=utc"})
    sessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)
    logger.info("Database connection established successfully.")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    exit(1)

running = True


def graceful_shutdown():
    global running
    logger.info("Shutting down gracefully...")
    running = False


signal.signal(signal.SIGINT, graceful_shutdown)
signal.signal(signal.SIGTERM, graceful_shutdown)


def execute_job(job: PollingJob, db_session):
    logger.info(f"Executing job {job.job_id} for symbols: {job.symbols}")
    # Create an instance of the selected provider
    provider = YFinanceProvider()
    events_to_publish = []

    try:
        for symbol in job.symbols:
            raw_data = provider.fetch_price_data(symbol)
            if raw_data is None:
                logger.warning(f"No data found for symbol: {symbol}")
                continue
            new_response_id = uuid.uuid4()
            new_raw_response = RawResponse(id=new_response_id, provider=job.provider, symbol=symbol,
                                           response_data=raw_data)
            db_session.add(new_raw_response)

            result = provider.parse_price_data(raw_data)
            if result is None:
                logger.warning(f"Failed to parse data for symbol: {symbol}")
                continue
            price, timestamp = result
            new_price_point_id = uuid.uuid4()
            new_price_point = PricePoint(id=new_price_point_id, symbol=symbol, price=price, provider=job.provider,
                                         timestamp=timestamp, raw_response_id=new_raw_response.id)

            db_session.add(new_price_point)
            new_price_event = {
                "id": str(new_price_point.id),
                "symbol": new_price_point.symbol,
                "price": new_price_point.price,
                "provider": new_price_point.provider,
                "timestamp": new_price_point.timestamp.isoformat(),
                "raw_response_id": str(new_price_point.raw_response_id)
            }
            events_to_publish.append(new_price_event)
        if len(events_to_publish) == 0:
            logger.info(f"No data to publish for job {job.job_id}. Skipping commit.")
            return

        job.last_run_at = func.now()

        db_session.commit()
        logger.info(f"Successfully committed {len(events_to_publish)}")

        print(events_to_publish)
        for event in events_to_publish:
            publish_price_event(event)

        logger.info(f"Published price events for job: {job.job_id}.")
    except Exception as e:
        logger.error(f"A problem occurred while executing job {job.job_id}: {e}")
        db_session.rollback()


def poll_for_jobs():
    logger.info("Poller service started.")

    while running:
        try:
            with sessionLocal() as db_session:
                due_jobs = db_session.query(PollingJob).filter(PollingJob.is_active, or_(PollingJob.last_run_at == None,
                                                                                         func.now() >= PollingJob.last_run_at + (
                                                                                                     PollingJob.interval * func.cast(
                                                                                                 "1 second",
                                                                                                 Interval)))).all()
                if due_jobs:
                    logger.info(f"Found {len(due_jobs)} due jobs to execute.")
                    for job in due_jobs:
                        execute_job(job, db_session)
                else:
                    logger.info("No due jobs found. Waiting for the next poll interval.")

        except Exception as e:
            logger.error(f"An error occurred while polling for jobs: {e}")

        for _ in range(5):
            if not running:
                break
            time.sleep(1)

    logger.info("Poller service shutting down")
    flush_producer()
    logger.info("Poller service shutdown complete.")


if __name__ == "__main__":
    poll_for_jobs()
