from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.application.services.payment_processor import PaymentProcessorService
from app.domain.value_objects import PaymentStatus


class TestPaymentProcessorService:
    async def test_returns_completed_when_random_below_threshold(self) -> None:
        service = PaymentProcessorService()
        with (
            patch(
                "app.application.services.payment_processor.random.random",
                return_value=0.5,
            ),
            patch(
                "app.application.services.payment_processor.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            result = await service.process(uuid4())

        assert result == PaymentStatus.COMPLETED

    async def test_returns_failed_when_random_above_threshold(self) -> None:
        service = PaymentProcessorService()

        with (
            patch(
                "app.application.services.payment_processor.random.random",
                return_value=0.95,
            ),
            patch(
                "app.application.services.payment_processor.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            result = await service.process(uuid4())

        assert result == PaymentStatus.FAILED
