import asyncio
import random
from uuid import UUID

from app.domain.value_objects import PaymentStatus


class PaymentProcessorService:
    async def process(self, payment_id: UUID) -> PaymentStatus:
        await asyncio.sleep(random.uniform(2, 5))

        if random.random() < 0.9:
            return PaymentStatus.COMPLETED
        return PaymentStatus.FAILED
