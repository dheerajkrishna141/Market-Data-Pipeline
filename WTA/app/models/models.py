from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import Column, String, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import SQLModel, Field, ARRAY


class RawResponse(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    provider: str = Field(max_length=50)
    symbol: str = Field(max_length=20)
    response_data: dict = Field(sa_column=Column(JSONB))
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PricePoint(SQLModel, table=True):
    id: UUID = Field(default_factory=UUID, primary_key=True)
    symbol: str = Field(max_length=20)
    price: float
    provider: str = Field(max_length=50)
    timestamp: datetime
    raw_response_id: UUID = Field(default=None, foreign_key="rawresponse.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SymbolAverage(SQLModel, table=True):
    symbol: str = Field(primary_key=True, max_length=20)
    moving_average: float
    last_updated_at: datetime


class PollingJob(SQLModel, table=True):
    job_id: UUID = Field(default_factory=UUID, primary_key=True, index=True)
    symbols: List[str] = Field(sa_column=Column(ARRAY(String)))
    provider: str = Field(max_length=50)
    interval: int = Field(sa_column=Column("interval", Integer, nullable=False))
    is_active: bool = Field(default=True)
    last_run_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
