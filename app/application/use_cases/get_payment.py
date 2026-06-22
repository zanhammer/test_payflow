from uuid import UUID

from app.application.interfaces.payment_repo import PaymentRepository
from app.domain.entities import Payment
from app.domain.exceptions import PaymentNotFound


class GetPaymentUseCase:
    def __init__(self, repo: PaymentRepository) -> None:
        self._repo = repo

    async def execute(self, payment_id: UUID) -> Payment:
        payment = await self._repo.get_by_id(payment_id)

        if payment is None:
            raise PaymentNotFound(f"Payment {payment_id} not found")

        return payment
