from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import OutboxEvent
from app.infrastructure.db.models import OutboxEventModel


class SQLAlchemyOutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, event: OutboxEvent) -> None:
        self._session.add(self._to_orm(event))
        await self._session.flush()

    async def get_unpublished(self, limit: int = 100) -> list[OutboxEvent]:
        result = await self._session.execute(
            select(OutboxEventModel)
            .where(OutboxEventModel.published == False)  # noqa: E712
            .order_by(OutboxEventModel.created_at)
            .limit(limit)
        )
        return [self._to_domain(m) for m in result.scalars()]

    async def mark_published(self, event_id: UUID) -> None:
        await self._session.execute(
            update(OutboxEventModel)
            .where(OutboxEventModel.id == event_id)
            .values(published=True, published_at=datetime.now(timezone.utc))
        )
        await self._session.commit()

    @staticmethod
    def _to_orm(event: OutboxEvent) -> OutboxEventModel:
        return OutboxEventModel(
            id=event.id,
            aggregate_id=event.aggregate_id,
            event_type=event.event_type,
            payload=event.payload,
            created_at=event.created_at,
            published=event.published,
            published_at=event.published_at,
        )

    @staticmethod
    def _to_domain(model: OutboxEventModel) -> OutboxEvent:
        return OutboxEvent(
            id=model.id,
            aggregate_id=model.aggregate_id,
            event_type=model.event_type,
            payload=model.payload,
            created_at=model.created_at,
            published=model.published,
            published_at=model.published_at,
        )
