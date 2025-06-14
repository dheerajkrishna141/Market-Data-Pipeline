import json
import logging
import signal
import os
import sys

from confluent_kafka import Consumer, KafkaError, KafkaException
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from app.core.config import settings
from app.models.models import PricePoint, SymbolAverage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    engine = create_engine(settings.DATABASE_URL)
    sessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)
    logger.info("Database engine created successfully.")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    exit(1)

consumer_config = {
    'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
    'group.id': 'MAConsumerGroup',
    'auto.offset.reset': 'earliest'
}

running = True

def graceful_shutdown():
    global running
    logger.info("Shutting down gracefully...")
    running = False

signal.signal(signal.SIGINT, graceful_shutdown)
signal.signal(signal.SIGTERM, graceful_shutdown)

def calculate_and_store_moving_average(symbol: str, db_session):

    try:
        results =  get_ma_and_timestamp(symbol, db_session)

        if results is None:
            logger.error(f"Failed to calculate moving average for {symbol}.")
            return
        ma_value, latest_timestamp = results
        stmt = insert(SymbolAverage).values(symbol= symbol, moving_average=ma_value, last_updated_at=latest_timestamp)
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=['symbol'],
            set_=dict(moving_average=stmt.excluded.moving_average, last_updated_at=stmt.excluded.last_updated_at)
        )
        db_session.execute(upsert_stmt)
        db_session.commit()
        logger.info(f"Stored moving average for {symbol}: {ma_value:.2f} at {latest_timestamp}")

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error storing moving average for {symbol}: {e}")
        return





def get_ma_and_timestamp(symbol: str, db_session):
    try:
        results = (db_session.query(PricePoint.price, PricePoint.timestamp).filter(PricePoint.symbol == symbol).order_by(PricePoint.timestamp.desc()).limit(5).all())

        if not results:
            logger.warning(f"No price points found for symbol: {symbol}")
            return
        if len(results) < 5:
            logger.info(f"Not enough data points for {symbol} calculate moving average (found {len(results)})")
            return

        price_values = [r[0] for r in results]
        ma_value = sum(price_values) / len(price_values)
        latest_timestamp = results[0][1]
        logger.info(f"Calculated moving average for {symbol}: {ma_value:.2f} ")
    except Exception as e:
        logger.error(f"Error calculating moving average for {symbol}: {e}")
        return
    return ma_value, latest_timestamp


def consumer_price_event():
    consumer = Consumer(consumer_config)
    try:
        consumer.subscribe([settings.KAFKA_PRICE_TOPIC])
        logger.info(f"Consumer subscribed to topic: {settings.KAFKA_PRICE_TOPIC}" )

        while running:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    logger.info(f"Reached end of partition for topic {msg.topic()} [{msg.partition()}]")
                elif msg.error():
                    raise KafkaException(msg.error())
            else:
                try:
                    print(msg.value())
                    price_data = json.loads(msg.value().decode('utf-8'))
                    price_event = PricePoint.model_validate(price_data)

                    logger.info(f"Received message for symbol: {price_event.symbol}, price: {price_event.price}, timestamp: {price_event.timestamp}")

                    with sessionLocal() as db_session:
                        calculate_and_store_moving_average(price_event.symbol, db_session)
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode JSON message: {msg.value()}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
    except Exception as e:
        logger.error(f"Consumer error: {e}")
    finally:
        consumer.close()
        logger.info("Consumer closed.")


if __name__ == "__main__":
    consumer_price_event()