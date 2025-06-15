# Real-Time Market Data Pipeline

## Overview

This application provides a REST API to fetch the latest stock prices on-demand and to set up recurring polling jobs for continuous data collection. New price points are published to a Kafka topic, processed by a background consumer to calculate a 5-point moving average, and stored in a PostgreSQL database for historical analysis and retrieval.


---

## Features

- **Scheduled Polling**: Create background jobs to poll for market data at configurable intervals.
- **Asynchronous Data Processing**: A resilient Kafka pipeline decouples data ingestion from processing.
- **Moving Average Calculation**: A dedicated consumer calculates and stores a 5-point moving average for each symbol.
- **Scalable Architecture**: Built with containerization in mind, allowing individual components (API, consumer, poller) to be scaled independently.
- **Comprehensive Test Suite**: Includes unit, integration, and end-to-end tests to ensure code quality and reliability.

## Architecture

The system is designed as a set of interacting microservices, communicating asynchronously through a message queue. This decouples the components, improving fault tolerance and scalability.

### System Sequential Diagram
![System Architecture](/assets/sequential_diagram.png)


## Technology Stack

- **Backend**: FastAPI with SQLModel
- **Database**: PostgreSQL
- **Message Queue**: Apache Kafka & ZooKeeper
- **Data Provider**: `yfinance` library (for Yahoo Finance)
- **Containerization**: Docker & Docker Compose
- **Testing**: Pytest, HTTPX, Pytest-Mock

---


## Getting Started

Follow these instructions to get the entire application stack running on your local machine.

### Prerequisites

- [Docker](https://www.docker.com/products/docker-desktop/)
- [Docker Compose](https://docs.docker.com/compose/install/)


### Documentation
- **API Documentation**: The FastAPI application automatically generates interactive API documentation. You can access it at [API-Documentation](assets/documentation.html).

### Configuration

1.  **Environment File**: The application requires an `.env` file for configuration. You can create one by copying the example file:
    ```
    cp .env.example .env
    ```
    The default values in the `.env.example` are configured to work with the `docker-compose.yml` setup.

    **.env.example:**
    ```ini
    # PostgreSQL Config
    DATABASE_URL="postgresql://user:password@db/marketdata"
    TEST_DATABASE_URL="postgresql://user:password@db/marketdata_test"
    POSTGRES_USER=root
    POSTGRES_PASSWORD=root
    POSTGRES_DB=postgres

    # Kafka Config
    KAFKA_BOOTSTRAP_SERVERS="kafka:9092"
    KAFKA_PRICE_TOPIC="price-events"
    KAFKA_PRICE_TOPIC=price_topic
    POLLING_INTERVAL=10
    
### Running the Application

Once your `.env` file is configured, you can start the entire application stack with a single command from the project's root directory:

```
docker-compose up -d --build
```

## Testing
The project includes a comprehensive test suite using pytest. The testing setup is designed to be fully automated and does not require any manual changes to the application's source code.

### Test Environment

- **Unit & Integration Tests**: These tests run against a dedicated PostgreSQL test database defined by `TEST_DATABASE_URL`. 


- **End-to-End Tests**:These tests run against the live services started by docker-compose up and connect to the main `DATABASE_URL`. They are designed to verify the interaction between all components of the system.

## Running the Tests
All test commands should be executed from the project's root directory.


### Running Unit & Integration Tests
These tests are fast and check individual components in isolation. The Docker containers do not need to be running for these.

```
pytest
```

### Running End-to-End Tests
These tests are slower and verify the entire data pipeline. This requires the full `docker-compose` stack to be running.


```
# First, ensure your application is running
docker-compose up -d

# Then, run only the E2E tests
pytest -m e2e -v -s

```

