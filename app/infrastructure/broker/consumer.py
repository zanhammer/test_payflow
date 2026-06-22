import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue, QueueType
from pydantic import BaseModel

from app.application.services.payment_processor import PaymentProcessorService
from app.domain.entities import Payment
from app.domain.value_objects import Currency, PaymentStatus
from app.infrastructure.broker.publisher import payments_exchange
from app.infrastructure.http.webhook_sender import HttpxWebhookSender

logger = logging.getLogger(__name__)


dlx_exchange = RabbitExchange(
    name="payments.dlx",
    type="fanout",
    durable=True,
)

dlq_queue = RabbitQueue(
    name="payments.new.dlq",
    durable=True,
)

payments_queue = RabbitQueue(
    name="payments.new",
    durable=True,
    routing_key="payments.new",
    queue_type=QueueType.QUORUM,
    arguments={
        "x-dead-letter-exchange": "payments.dlx",
        "x-delivery-limit": 3,
    },
)


class PaymentMessage(BaseModel):
    payment_id: UUID


class WebhookPayload(BaseModel):
    payment_id: UUID
    status: PaymentStatus
    amount: Decimal
    currency: Currency
    processed_at: datetime


def build_webhook_payload(payment: Payment) -> dict[str, Any]:
    return WebhookPayload(
        payment_id=payment.id,
        status=payment.status,
        amount=payment.amount,
        currency=payment.currency,
        processed_at=payment.processed_at,  # type: ignore[arg-type]
    ).model_dump(mode="json")


def create_consumer(
    broker: RabbitBroker,
    processor: PaymentProcessorService,
    webhook_sender: HttpxWebhookSender,
    get_uow: Any,
) -> None:
    @broker.subscriber(
        queue=payments_queue,
        exchange=payments_exchange,
    )
    async def handle_payment(
        msg: PaymentMessage,
        headers: dict[str, Any],
    ) -> None:
        delivery_count = int(headers.get("x-delivery-count", 0))

        if delivery_count > 0:
            delay = 2 ** (delivery_count - 1)
            logger.info(
                "Retry processing payment %s (attempt %d), delay %d sec",
                msg.payment_id, delivery_count + 1, delay,
            )
            await asyncio.sleep(delay)

        new_status = await processor.process(msg.payment_id)

        async with get_uow() as uow:
            payment = await uow.payments.mark_processed_if_pending(
                payment_id=msg.payment_id,
                status=new_status,
                processed_at=datetime.now(timezone.utc),
            )

            if payment is None:
                logger.info("Payment %s already processed, skipping", msg.payment_id)
                return

            await uow.commit()

        await webhook_sender.send(
            payment.webhook_url,
            build_webhook_payload(payment),
        )

    @broker.subscriber(queue=dlq_queue)
    async def handle_dlq(
        msg: PaymentMessage,
        headers: dict[str, Any],
    ) -> None:
        logger.error(
            "Payment permanently failed after all retries, manual investigation required",
            extra={"payment_id": str(msg.payment_id), "headers": headers},
        )
