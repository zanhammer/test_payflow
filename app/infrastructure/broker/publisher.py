import logging
from typing import Any

from faststream.rabbit import RabbitBroker, RabbitExchange, ExchangeType

logger = logging.getLogger(__name__)

payments_exchange = RabbitExchange(
    name="payments",
    type=ExchangeType.DIRECT,
    durable=True,
)


class RabbitMQPublisher:
    def __init__(self, broker: RabbitBroker) -> None:
        self._broker = broker

    async def publish(self, routing_key: str, payload: dict[str, Any]) -> None:
        await self._broker.publish(
            message=payload,
            exchange=payments_exchange,
            routing_key=routing_key,
        )
        logger.debug("Message published, routing_key=%s", routing_key)
