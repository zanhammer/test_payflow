import asyncio
import logging
from contextlib import asynccontextmanager

from faststream.rabbit import RabbitBroker

from app.application.services.payment_processor import PaymentProcessorService
from app.core.config import settings
from app.infrastructure.broker.consumer import create_consumer
from app.infrastructure.db.database import AsyncSessionFactory
from app.infrastructure.db.unit_of_work import SQLAlchemyUnitOfWork
from app.infrastructure.http.webhook_sender import HttpxWebhookSender

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("Starting PayFlow Consumer...")

    broker = RabbitBroker(str(settings.rabbitmq_url))

    processor = PaymentProcessorService()
    webhook_sender = HttpxWebhookSender()

    @asynccontextmanager  # type: ignore[arg-type]
    async def get_uow():  # type: ignore[no-untyped-def]
        async with SQLAlchemyUnitOfWork(AsyncSessionFactory) as uow:
            yield uow

    create_consumer(broker, processor, webhook_sender, get_uow)

    async with broker:
        logger.info("Consumer started, waiting for messages...")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
