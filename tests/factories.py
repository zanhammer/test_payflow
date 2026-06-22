from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import FastAPI

from app.domain.entities import OutboxEvent, Payment
from app.domain.exceptions import DuplicateIdempotencyKey
from app.domain.value_objects import Currency, PaymentStatus
from app.presentation.api.v1.dependencies import (
    get_create_payment_use_case,
    get_payment_use_case,
    verify_api_key,
)
from app.presentation.api.v1.payments import router


def make_payment(**kwargs: Any) -> Payment:
    defaults: dict[str, Any] = {
        "id": uuid4(),
        "amount": Decimal("100.00"),
        "currency": Currency.USD,
        "description": "Test payment",
        "metadata": {},
        "status": PaymentStatus.PENDING,
        "idempotency_key": "key-123",
        "request_hash": "abc123",
        "webhook_url": "https://example.com/hook",
        "created_at": datetime.now(timezone.utc),
        "processed_at": None,
    }
    return Payment(**{**defaults, **kwargs})


def make_create_payment_kwargs(**kwargs: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "amount": Decimal("100.00"),
        "currency": Currency.USD,
        "description": "Test",
        "metadata": {},
        "webhook_url": "https://example.com/hook",
        "idempotency_key": "key-123",
    }
    return {**defaults, **kwargs}


def make_fake_uow() -> AsyncMock:
    uow = AsyncMock()
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None
    uow.payments.save.return_value = None
    uow.outbox.save.return_value = None
    uow.commit.return_value = None
    uow.payments.get_by_idempotency_key.return_value = None
    return uow


def make_fake_uow_with_conflict(existing_payment: Payment) -> AsyncMock:
    uow = AsyncMock()
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None
    uow.payments.save.side_effect = DuplicateIdempotencyKey()
    uow.outbox.save.return_value = None
    uow.commit.return_value = None
    uow.payments.get_by_idempotency_key.return_value = existing_payment
    return uow


def make_event(event_type: str = "payment.created", **kwargs: Any) -> OutboxEvent:
    defaults: dict[str, Any] = {
        "id": uuid4(),
        "aggregate_id": uuid4(),
        "event_type": event_type,
        "payload": {"payment_id": "123"},
        "created_at": datetime.now(timezone.utc),
        "published": False,
        "published_at": None,
    }
    return OutboxEvent(**{**defaults, **kwargs})


@dataclass
class ConsumerHandler:
    handler: Any
    processor: AsyncMock = field(default_factory=AsyncMock)
    webhook: AsyncMock = field(default_factory=AsyncMock)
    uow: AsyncMock = field(default_factory=AsyncMock)


def make_consumer_handler(payment: Payment | None = None) -> ConsumerHandler:
    from faststream.rabbit import RabbitBroker

    from app.domain.value_objects import PaymentStatus
    from app.infrastructure.broker.consumer import create_consumer, payments_queue

    processor = AsyncMock()
    processor.process.return_value = PaymentStatus.COMPLETED
    webhook = AsyncMock()

    uow = AsyncMock()
    uow.payments.mark_processed_if_pending.return_value = payment
    uow.commit.return_value = None

    @asynccontextmanager
    async def get_uow():  # type: ignore[no-untyped-def]
        yield uow

    broker = MagicMock(spec=RabbitBroker)
    handlers: dict[Any, Any] = {}

    def subscriber_decorator(*args: Any, **kwargs: Any) -> Any:
        def decorator(func: Any) -> Any:
            handlers[kwargs.get("queue", args[0] if args else None)] = func
            return func
        return decorator

    broker.subscriber = subscriber_decorator
    create_consumer(broker, processor, webhook, get_uow)

    return ConsumerHandler(
        handler=handlers[payments_queue],
        processor=processor,
        webhook=webhook,
        uow=uow,
    )


def make_test_app(
    create_use_case: AsyncMock | None = None,
    get_use_case: AsyncMock | None = None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[verify_api_key] = lambda: None

    if create_use_case:
        app.dependency_overrides[get_create_payment_use_case] = lambda: create_use_case
    if get_use_case:
        app.dependency_overrides[get_payment_use_case] = lambda: get_use_case

    return app
