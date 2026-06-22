from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.domain.exceptions import DuplicateIdempotencyKey
from app.domain.value_objects import PaymentStatus
from app.infrastructure.db.repositories.payment_repo import SQLAlchemyPaymentRepository
from tests.factories import make_payment


class TestSQLAlchemyPaymentRepository:
    async def test_save_and_get_by_id(self, session) -> None:  # type: ignore[no-untyped-def]
        repo = SQLAlchemyPaymentRepository(session)
        payment = make_payment(description="Integration test", metadata={"order_id": "42"})

        await repo.save(payment)
        await session.commit()

        found = await repo.get_by_id(payment.id)

        assert found is not None
        assert found.id == payment.id
        assert found.metadata == {"order_id": "42"}
        assert found.status == PaymentStatus.PENDING

    async def test_get_by_id_returns_none_when_not_found(self, session) -> None:  # type: ignore[no-untyped-def]
        repo = SQLAlchemyPaymentRepository(session)
        result = await repo.get_by_id(uuid4())
        assert result is None

    async def test_duplicate_idempotency_key_raises_domain_exception(self, session) -> None:  # type: ignore[no-untyped-def]
        repo = SQLAlchemyPaymentRepository(session)
        payment1 = make_payment(idempotency_key="unique-key")
        payment2 = make_payment(idempotency_key="unique-key")

        await repo.save(payment1)
        await session.flush()

        with pytest.raises(DuplicateIdempotencyKey):
            await repo.save(payment2)

        found = await repo.get_by_idempotency_key("unique-key")
        assert found is not None
        assert found.id == payment1.id

    async def test_mark_processed_if_pending_updates_status(self, session) -> None:  # type: ignore[no-untyped-def]
        repo = SQLAlchemyPaymentRepository(session)
        payment = make_payment()
        await repo.save(payment)
        await session.flush()

        processed_at = datetime.now(timezone.utc)
        result = await repo.mark_processed_if_pending(
            payment_id=payment.id,
            status=PaymentStatus.COMPLETED,
            processed_at=processed_at,
        )

        assert result is not None
        assert result.status == PaymentStatus.COMPLETED
        assert result.processed_at is not None

    async def test_mark_processed_if_pending_returns_none_when_not_pending(self, session) -> None:  # type: ignore[no-untyped-def]
        repo = SQLAlchemyPaymentRepository(session)
        payment = make_payment()
        await repo.save(payment)
        await session.flush()

        await repo.mark_processed_if_pending(
            payment_id=payment.id,
            status=PaymentStatus.COMPLETED,
            processed_at=datetime.now(timezone.utc),
        )

        result = await repo.mark_processed_if_pending(
            payment_id=payment.id,
            status=PaymentStatus.FAILED,
            processed_at=datetime.now(timezone.utc),
        )

        assert result is None

    async def test_jsonb_metadata_stored_correctly(self, session) -> None:  # type: ignore[no-untyped-def]
        repo = SQLAlchemyPaymentRepository(session)
        payment = make_payment(
            metadata={
                "order_id": "42",
                "items": [1, 2, 3],
                "nested": {"key": "value"},
            }
        )

        await repo.save(payment)
        await session.flush()

        found = await repo.get_by_id(payment.id)
        assert found is not None
        assert found.metadata["items"] == [1, 2, 3]
        assert found.metadata["nested"]["key"] == "value"
