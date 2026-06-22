from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from app.application.use_cases.create_payment import CreatePaymentUseCase
from app.application.use_cases.get_payment import GetPaymentUseCase
from app.domain.exceptions import IdempotencyConflict
from app.presentation.api.v1.dependencies import (
    get_create_payment_use_case,
    get_payment_use_case,
    verify_api_key,
)
from app.presentation.schemas.payment import (
    CreatePaymentRequest,
    CreatePaymentResponse,
    PaymentDetailResponse,
)

router = APIRouter(prefix="/api/v1", tags=["payments"])


@router.post(
    "/payments",
    response_model=CreatePaymentResponse,
)
async def create_payment(
    body: CreatePaymentRequest,
    response: Response,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    _: None = Depends(verify_api_key),
    use_case: CreatePaymentUseCase = Depends(get_create_payment_use_case),
) -> CreatePaymentResponse:
    try:
        payment, created = await use_case.execute(
            amount=body.amount,
            currency=body.currency,
            description=body.description,
            metadata=body.metadata,
            webhook_url=str(body.webhook_url),
            idempotency_key=idempotency_key,
        )
    except IdempotencyConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    response.status_code = (
        status.HTTP_201_CREATED if created else status.HTTP_200_OK
    )

    return CreatePaymentResponse(
        payment_id=payment.id,
        status=payment.status,
        created_at=payment.created_at,
    )


@router.get(
    "/payments/{payment_id}",
    response_model=PaymentDetailResponse,
)
async def get_payment(
    payment_id: UUID,
    _: None = Depends(verify_api_key),
    use_case: GetPaymentUseCase = Depends(get_payment_use_case),
) -> PaymentDetailResponse:
    payment = await use_case.execute(payment_id)

    return PaymentDetailResponse(
        payment_id=payment.id,
        amount=payment.amount,
        currency=payment.currency,
        description=payment.description,
        metadata=payment.metadata,
        status=payment.status,
        webhook_url=payment.webhook_url,
        created_at=payment.created_at,
        processed_at=payment.processed_at,
    )
