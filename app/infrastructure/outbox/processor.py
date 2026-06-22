import asyncio
import logging
from typing import Callable, AsyncIterator

from app.infrastructure.broker.publisher import RabbitMQPublisher
from app.infrastructure.db.repositories.outbox_repo import SQLAlchemyOutboxRepository

logger = logging.getLogger(__name__)


class OutboxProcessor:
    def __init__(
        self,
        get_repo: Callable[[], AsyncIterator[SQLAlchemyOutboxRepository]],
        publisher: RabbitMQPublisher,
        poll_interval: float = 1.0,
    ) -> None:
        self._get_repo = get_repo
        self._publisher = publisher
        self._poll_interval = poll_interval
        self._running = False

    async def run(self) -> None:
        self._running = True
        logger.info(
            "Outbox processor started, poll interval=%.1f sec",
            self._poll_interval,
        )

        while self._running:
            try:
                await self._process_batch()
            except Exception:
                logger.exception("Error processing outbox batch, will retry later")

            await asyncio.sleep(self._poll_interval)

    def stop(self) -> None:
        self._running = False
        logger.info("Outbox processor stopping")

    async def _process_batch(self) -> None:
        async with self._get_repo() as repo:
            events = await repo.get_unpublished(limit=100)

        if not events:
            return

        logger.debug("Outbox processor: %d events in batch", len(events))

        for event in events:
            if event.event_type == "payment.created":
                routing_key = "payments.new"
            elif event.event_type == "payment.processed":
                routing_key = "payments.processed"
            else:
                logger.error(
                    "Unknown event type '%s', event %s skipped",
                    event.event_type, event.id,
                )
                continue

            await self._publisher.publish(routing_key, event.payload)

            async with self._get_repo() as repo:
                await repo.mark_published(event.id)

            logger.debug(
                "Event %s published, routing_key=%s",
                event.id,
                routing_key,
            )
