from pydantic_settings import BaseSettings;


class Settings(BaseSettings):
    DATABASE_URL: str
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_PRICE_TOPIC: str
    TEST_DATABASE_URL: str
    POLLING_INTERVAL: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
print(f"Configured Kafka bootstrap servers: {settings.KAFKA_BOOTSTRAP_SERVERS}")
