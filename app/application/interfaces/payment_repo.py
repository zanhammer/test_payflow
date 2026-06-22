from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domain.entities import Payment
from app.domain.value_objects import PaymentStatus


class PaymentRepository(Protocol):
    async def save(self, payment: Payment) -> None:
        ...

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        ...

    async def get_by_idempotency_key(self, key: str) -> Payment | None:
        ...

    async def mark_processed_if_pending(
        self,
        payment_id: UUID,
        status: PaymentStatus,
        processed_at: datetime,
    ) -> Payment | None:
        ...
