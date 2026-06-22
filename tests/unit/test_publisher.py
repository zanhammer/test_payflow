from unittest.mock import AsyncMock

from app.infrastructure.broker.publisher import RabbitMQPublisher


class TestRabbitMQPublisher:
    async def test_publish_calls_broker_with_correct_args(self) -> None:
        broker = AsyncMock()
        publisher = RabbitMQPublisher(broker)

        payload = {"payment_id": "123"}
        await publisher.publish("payments.new", payload)

        broker.publish.assert_called_once()
        call_kwargs = broker.publish.call_args.kwargs
        assert call_kwargs["message"] == payload
        assert call_kwargs["routing_key"] == "payments.new"

    async def test_publish_uses_payments_exchange(self) -> None:
        from app.infrastructure.broker.publisher import payments_exchange

        broker = AsyncMock()
        publisher = RabbitMQPublisher(broker)

        await publisher.publish("payments.new", {})

        call_kwargs = broker.publish.call_args.kwargs
        assert call_kwargs["exchange"] == payments_exchange
