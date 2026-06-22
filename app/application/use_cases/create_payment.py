import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from app.domain.entities import OutboxEvent, Payment
from app.domain.exceptions import DuplicateIdempotencyKey, IdempotencyConflict
from app.domain.value_objects import Currency, PaymentStatus
from app.infrastructure.db.unit_of_work import SQLAlchemyUnitOfWork


def compute_request_hash(
    *,
    amount: Decimal,
    currency: Currency,
    description: str,
    metadata: dict[str, Any],
    webhook_url: str,
) -> str:
    data: dict[str, Any] = {
        "amount": str(Decimal(str(amount)).quantize(Decimal("0.01"))),
        "currency": str(currency),
        "description": description,
        "metadata": metadata,
        "webhook_url": webhook_url,
    }
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class CreatePaymentUseCase:
    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        *,
        amount: Decimal,
        currency: Currency,
        description: str,
        metadata: dict[str, Any],
        webhook_url: str,
        idempotency_key: str,
    ) -> tuple[Payment, bool]:
        request_hash = compute_request_hash(
            amount=amount,
            currency=currency,
            description=description,
            metadata=metadata,
            webhook_url=webhook_url,
        )

        payment = Payment(
            id=uuid4(),
            amount=amount,
            currency=currency,
            description=description,
            metadata=metadata,
            status=PaymentStatus.PENDING,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            webhook_url=webhook_url,
            created_at=datetime.now(timezone.utc),
            processed_at=None,
        )

        event = OutboxEvent(
            id=uuid4(),
            aggregate_id=payment.id,
            event_type="payment.created",
            payload={"payment_id": str(payment.id)},
            created_at=datetime.now(timezone.utc),
            published=False,
            published_at=None,
        )

        async with self._uow:
            try:
                await self._uow.payments.save(payment)
                await self._uow.outbox.save(event)
                await self._uow.commit()
                return payment, True

            except DuplicateIdempotencyKey:
                existing = await self._uow.payments.get_by_idempotency_key(
                    idempotency_key
                )

                if existing is None:
                    raise RuntimeError(
                        "Inconsistent state: DuplicateIdempotencyKey raised, "
                        "but payment not found by key"
                    )

                if existing.request_hash != request_hash:
                    raise IdempotencyConflict(
                        f"Idempotency key '{idempotency_key}' already used "
                        "with a different request body"
                    )

                return existing, False
