class DomainError(Exception):
    pass


class PaymentNotFound(DomainError):
    pass


class DuplicateIdempotencyKey(DomainError):
    pass


class IdempotencyConflict(DomainError):
    pass
