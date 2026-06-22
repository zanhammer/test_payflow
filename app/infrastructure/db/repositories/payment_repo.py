from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import Payment
from app.domain.exceptions import DuplicateIdempotencyKey
from app.domain.value_objects import Currency, PaymentStatus
from app.infrastructure.db.models import PaymentModel


class SQLAlchemyPaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, payment: Payment) -> None:
        model = self._to_orm(payment)
        try:
            async with self._session.begin_nested():
                self._session.add(model)
                await self._session.flush()
        except IntegrityError:
            raise DuplicateIdempotencyKey()

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        result = await self._session.execute(
            select(PaymentModel).where(PaymentModel.id == payment_id)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_idempotency_key(self, key: str) -> Payment | None:
        result = await self._session.execute(
            select(PaymentModel).where(PaymentModel.idempotency_key == key)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def mark_processed_if_pending(
        self,
        payment_id: UUID,
        status: PaymentStatus,
        processed_at: datetime,
    ) -> Payment | None:
        result = await self._session.execute(
            update(PaymentModel)
            .where(
                PaymentModel.id == payment_id,
                PaymentModel.status == PaymentStatus.PENDING,
            )
            .values(status=str(status), processed_at=processed_at)
            .returning(PaymentModel)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    @staticmethod
    def _to_orm(payment: Payment) -> PaymentModel:
        return PaymentModel(
            id=payment.id,
            amount=payment.amount,
            currency=str(payment.currency),
            description=payment.description,
            metadata_=payment.metadata,
            status=str(payment.status),
            idempotency_key=payment.idempotency_key,
            request_hash=payment.request_hash,
            webhook_url=payment.webhook_url,
            created_at=payment.created_at,
            processed_at=payment.processed_at,
        )

    @staticmethod
    def _to_domain(model: PaymentModel) -> Payment:
        return Payment(
            id=model.id,
            amount=model.amount,
            currency=Currency(model.currency),
            description=model.description,
            metadata=model.metadata_,
            status=PaymentStatus(model.status),
            idempotency_key=model.idempotency_key,
            request_hash=model.request_hash,
            webhook_url=model.webhook_url,
            created_at=model.created_at,
            processed_at=model.processed_at,
        )
