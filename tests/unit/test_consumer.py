from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.domain.value_objects import PaymentStatus
from app.infrastructure.broker.consumer import PaymentMessage, build_webhook_payload
from tests.factories import make_consumer_handler, make_payment


class TestBuildWebhookPayload:
    def test_serializes_payment_to_json_compatible_dict(self) -> None:
        base = make_payment()
        payment = make_payment(
            status=PaymentStatus.COMPLETED,
            processed_at=base.created_at,
        )
        payload = build_webhook_payload(payment)

        assert isinstance(payload["payment_id"], str)
        assert isinstance(payload["amount"], str)
        assert payload["status"] == "completed"


class TestConsumerBackoff:
    async def test_no_sleep_on_first_delivery(self) -> None:
        payment = make_payment(
            status=PaymentStatus.COMPLETED,
            processed_at=datetime.now(timezone.utc),
        )
        setup = make_consumer_handler(payment)

        msg = PaymentMessage(payment_id=uuid4())
        sleep_mock = AsyncMock()
        with patch("app.infrastructure.broker.consumer.asyncio.sleep", sleep_mock):
            await setup.handler(msg, headers={"x-delivery-count": "0"})

        sleep_mock.assert_not_called()

    async def test_sleep_on_retry(self) -> None:
        payment = make_payment(
            status=PaymentStatus.COMPLETED,
            processed_at=datetime.now(timezone.utc),
        )
        setup = make_consumer_handler(payment)

        msg = PaymentMessage(payment_id=uuid4())
        sleep_mock = AsyncMock()
        with patch("app.infrastructure.broker.consumer.asyncio.sleep", sleep_mock):
            await setup.handler(msg, headers={"x-delivery-count": "1"})

        sleep_mock.assert_called_once_with(1)

    async def test_skips_webhook_when_already_processed(self) -> None:
        setup = make_consumer_handler(payment=None)

        msg = PaymentMessage(payment_id=uuid4())
        with patch("app.infrastructure.broker.consumer.asyncio.sleep", AsyncMock()):
            await setup.handler(msg, headers={})

        setup.webhook.send.assert_not_called()
        setup.uow.commit.assert_not_called()
