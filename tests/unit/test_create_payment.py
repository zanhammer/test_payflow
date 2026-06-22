from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from app.application.use_cases.create_payment import (
    CreatePaymentUseCase,
    compute_request_hash,
)
from app.domain.exceptions import DuplicateIdempotencyKey, IdempotencyConflict
from app.domain.value_objects import Currency, PaymentStatus
from tests.factories import (
    make_create_payment_kwargs,
    make_fake_uow,
    make_fake_uow_with_conflict,
    make_payment,
)


class TestComputeRequestHash:
    @staticmethod
    def _hash_kwargs(**overrides: Any) -> dict[str, Any]:
        return {
            "amount": Decimal("100.00"),
            "currency": Currency.USD,
            "description": "Test payment",
            "metadata": {},
            "webhook_url": "https://example.com/hook",
            **overrides,
        }

    def test_same_input_gives_same_hash(self) -> None:
        kwargs = self._hash_kwargs()
        assert compute_request_hash(**kwargs) == compute_request_hash(**kwargs)

    def test_different_amount_gives_different_hash(self) -> None:
        h1 = compute_request_hash(**self._hash_kwargs(amount=Decimal("100.00")))
        h2 = compute_request_hash(**self._hash_kwargs(amount=Decimal("200.00")))
        assert h1 != h2

    def test_amount_normalization(self) -> None:
        h1 = compute_request_hash(**self._hash_kwargs(amount=Decimal("100")))
        h2 = compute_request_hash(**self._hash_kwargs(amount=Decimal("100.0")))
        h3 = compute_request_hash(**self._hash_kwargs(amount=Decimal("100.00")))
        assert h1 == h2 == h3


class TestCreatePaymentUseCase:
    async def test_new_payment_is_created(self) -> None:
        uow = make_fake_uow()
        use_case = CreatePaymentUseCase(uow)

        payment, created = await use_case.execute(**make_create_payment_kwargs())

        assert created is True
        assert payment.status == PaymentStatus.PENDING
        uow.payments.save.assert_called_once()
        uow.outbox.save.assert_called_once()
        uow.commit.assert_called_once()

    async def test_duplicate_key_same_payload_returns_existing(self) -> None:
        kwargs = make_create_payment_kwargs()
        request_hash = compute_request_hash(
            amount=kwargs["amount"],
            currency=kwargs["currency"],
            description=kwargs["description"],
            metadata=kwargs["metadata"],
            webhook_url=kwargs["webhook_url"],
        )
        existing = make_payment(
            amount=kwargs["amount"],
            currency=kwargs["currency"],
            description=kwargs["description"],
            metadata=kwargs["metadata"],
            idempotency_key=kwargs["idempotency_key"],
            request_hash=request_hash,
            webhook_url=kwargs["webhook_url"],
            created_at=datetime.now(timezone.utc),
        )
        uow = make_fake_uow_with_conflict(existing)
        use_case = CreatePaymentUseCase(uow)

        payment, created = await use_case.execute(**kwargs)

        assert created is False
        assert payment.id == existing.id

    async def test_duplicate_key_different_payload_raises_conflict(self) -> None:
        kwargs = make_create_payment_kwargs()
        existing = make_payment(
            amount=kwargs["amount"],
            currency=kwargs["currency"],
            description=kwargs["description"],
            metadata=kwargs["metadata"],
            idempotency_key=kwargs["idempotency_key"],
            request_hash="different_hash",
            webhook_url=kwargs["webhook_url"],
            created_at=datetime.now(timezone.utc),
        )
        uow = make_fake_uow_with_conflict(existing)
        use_case = CreatePaymentUseCase(uow)

        with pytest.raises(IdempotencyConflict):
            await use_case.execute(**kwargs)
