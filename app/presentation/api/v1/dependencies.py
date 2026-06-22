import secrets
from typing import AsyncIterator

from fastapi import Depends, Header, HTTPException

from app.application.use_cases.create_payment import CreatePaymentUseCase
from app.application.use_cases.get_payment import GetPaymentUseCase
from app.core.config import settings
from app.infrastructure.db.database import AsyncSessionFactory
from app.infrastructure.db.unit_of_work import SQLAlchemyUnitOfWork


# TODO: use secrets.compare_digest for timing-attack safety
async def verify_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> None:
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


async def get_uow() -> AsyncIterator[SQLAlchemyUnitOfWork]:
    async with SQLAlchemyUnitOfWork(AsyncSessionFactory) as uow:
        yield uow


async def get_create_payment_use_case(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> CreatePaymentUseCase:
    return CreatePaymentUseCase(uow)


async def get_payment_use_case(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> GetPaymentUseCase:
    return GetPaymentUseCase(uow.payments)
