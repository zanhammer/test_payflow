from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, Field

from app.domain.value_objects import Currency, PaymentStatus


class CreatePaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2, description="Payment amount")
    currency: Currency
    description: str = Field(max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)
    webhook_url: AnyHttpUrl


class CreatePaymentResponse(BaseModel):
    payment_id: UUID
    status: PaymentStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentDetailResponse(BaseModel):
    payment_id: UUID
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any]
    status: PaymentStatus
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None

    model_config = {"from_attributes": True}
