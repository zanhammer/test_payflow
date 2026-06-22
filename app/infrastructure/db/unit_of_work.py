from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db.repositories.outbox_repo import SQLAlchemyOutboxRepository
from app.infrastructure.db.repositories.payment_repo import SQLAlchemyPaymentRepository


class SQLAlchemyUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.payments: SQLAlchemyPaymentRepository
        self.outbox: SQLAlchemyOutboxRepository

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        self._session: AsyncSession = self._session_factory()
        self.payments = SQLAlchemyPaymentRepository(self._session)
        self.outbox = SQLAlchemyOutboxRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: object,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
        await self._session.close()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
