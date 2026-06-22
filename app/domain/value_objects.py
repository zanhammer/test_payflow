from enum import StrEnum


class Currency(StrEnum):
    USD = "USD"
    EUR = "EUR"
    RUB = "RUB"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
