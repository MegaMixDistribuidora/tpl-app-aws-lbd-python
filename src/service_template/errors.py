class DomainError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class ValidationError(DomainError):
    pass


class ForbiddenError(DomainError):
    pass
