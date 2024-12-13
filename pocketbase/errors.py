from typing import Any


class BaseError(Exception):
    pass


class ResponseError(BaseError):
    def __init__(self, message: str, status_code: int, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class NotFound(ResponseError):
    pass


class ValidationNotUnique(ResponseError):
    pass
