from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.domain.value_objects import Currency, PaymentStatus


@dataclass
class Payment:
    id: UUID
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any]
    status: PaymentStatus
    idempotency_key: str
    request_hash: str
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None


@dataclass
class OutboxEvent:
    id: UUID
    aggregate_id: UUID
    event_type: str
    payload: dict[str, Any]
    created_at: datetime
    published: bool
    published_at: datetime | None
