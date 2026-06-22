from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.application.use_cases.get_payment import GetPaymentUseCase
from app.domain.exceptions import PaymentNotFound
from tests.factories import make_payment


class TestGetPaymentUseCase:
    async def test_returns_payment_when_found(self) -> None:
        payment = make_payment()
        repo = AsyncMock()
        repo.get_by_id.return_value = payment

        use_case = GetPaymentUseCase(repo)
        result = await use_case.execute(payment.id)

        assert result == payment
        repo.get_by_id.assert_called_once_with(payment.id)

    async def test_raises_not_found_when_missing(self) -> None:
        repo = AsyncMock()
        repo.get_by_id.return_value = None

        use_case = GetPaymentUseCase(repo)

        with pytest.raises(PaymentNotFound):
            await use_case.execute(uuid4())
