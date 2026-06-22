import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from faststream.rabbit import RabbitBroker

from app.core.config import settings
from app.domain.exceptions import PaymentNotFound
from app.infrastructure.broker.publisher import RabbitMQPublisher
from app.infrastructure.db.database import AsyncSessionFactory, engine
from app.infrastructure.db.repositories.outbox_repo import SQLAlchemyOutboxRepository
from app.infrastructure.outbox.processor import OutboxProcessor
from app.presentation.api.v1.payments import router

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting PayFlow API...")

    broker = RabbitBroker(str(settings.rabbitmq_url))
    await broker.connect()

    publisher = RabbitMQPublisher(broker)

    @asynccontextmanager
    async def get_outbox_repo():  # type: ignore[return-type]  # async generator confuses mypy here
        session = AsyncSessionFactory()
        try:
            yield SQLAlchemyOutboxRepository(session)
        finally:
            await session.close()

    outbox_processor = OutboxProcessor(
        get_repo=get_outbox_repo,
        publisher=publisher,
        poll_interval=1.0,
    )
    outbox_task = asyncio.create_task(outbox_processor.run())

    logger.info("PayFlow API started")

    yield

    logger.info("Shutting down PayFlow API...")

    outbox_processor.stop()
    outbox_task.cancel()
    try:
        await outbox_task
    except asyncio.CancelledError:
        pass

    await broker.close()
    await engine.dispose()

    logger.info("Shutdown complete")


app = FastAPI(
    title="PayFlow",
    description="Async payment processing service",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(PaymentNotFound)
async def payment_not_found_handler(
    request: Request, exc: PaymentNotFound
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception("Unhandled exception: %s %s", request.method, request.url)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
