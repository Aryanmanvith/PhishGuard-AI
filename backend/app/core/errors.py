"""Application errors and the JSON error envelope.

Every error the API returns looks like:
    {"error": {"code": "invalid_url", "message": "Human readable text"}}
so the frontend only needs one error-handling path.
"""
from __future__ import annotations


class AppError(Exception):
    """An error we expect and can explain to the user."""

    def __init__(self, message: str, *, code: str = "bad_request", status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, message: str = "Not found."):
        super().__init__(message, code="not_found", status_code=404)


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}
