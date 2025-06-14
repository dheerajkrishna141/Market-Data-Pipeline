import json
import logging

from confluent_kafka import Producer

from app.core.config import settings
from app.models.models import PricePoint

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

producer_config = {
    'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS
}

try:
    producer = Producer(producer_config)
    logger.info("Kafka Producer initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Kafka Producer: {e}")
    producer = None


def delivery_report(err, msg):
    if err is not None:
        logger.error(f"Message delivery failed: {err}")
    else:
        logger.info(f"Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")


def publish_price_event(price_event):
    if producer is None:
        logger.error("Kafka Producer is not initialized.")
        return

    try:
        event_value = json.dumps(price_event).encode("utf-8")
        event_key = price_event['symbol'].encode('utf-8')

        producer.produce(
            topic=settings.KAFKA_PRICE_TOPIC,
            key=event_key,
            value=event_value,
            callback=delivery_report
        )
        producer.poll(0)

    except BufferError:
        logger.error("Local producer queue is full ({} messages awaiting delivery).".format(len(producer)))

    except Exception as e:
        logger.error(f"Failed to publish price event: {e}")


def flush_producer():
    if producer is not None:
        try:
            producer.flush()
            logger.info("Flushing producer..")
        except Exception as e:
            logger.error(f"Failed to flush Producer: {e}")
    else:
        logger.error("Kafka Producer is not initialized, cannot flush.")
