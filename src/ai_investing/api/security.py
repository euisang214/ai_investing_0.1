"""API security: key-based authentication and role-based authorization.

Provides:
- ``parse_api_keys`` — parses ``key:role`` comma-separated env var format
- ``ApiKeyMiddleware`` — Starlette middleware enforcing ``X-API-Key`` header
- ``require_role`` — FastAPI dependency for endpoint-level authorization
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp


def parse_api_keys(raw: str) -> dict[str, str]:
    """Parse ``key:role`` comma-separated string into ``{key: role}`` dict.

    Examples
    --------
    >>> parse_api_keys("sk-a:operator,sk-b:readonly")
    {'sk-a': 'operator', 'sk-b': 'readonly'}
    >>> parse_api_keys("")
    {}
    """
    if not raw or not raw.strip():
        return {}
    result: dict[str, str] = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if ":" not in entry:
            continue
        key, role = entry.rsplit(":", 1)
        key = key.strip()
        role = role.strip()
        if key and role:
            result[key] = role
    return result


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Middleware that validates ``X-API-Key`` header on every request.

    When ``auth_enabled`` is ``False`` **or** no keys are configured,
    the middleware passes all requests through with ``role="operator"``
    (full access).  This keeps existing tests and local-dev workflows
    working without modification.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        auth_enabled: bool = True,
        api_keys: dict[str, str] | None = None,
    ) -> None:
        super().__init__(app)
        self._auth_enabled = auth_enabled
        self._api_keys = api_keys or {}
        # If no keys are configured, auth is effectively disabled
        self._active = auth_enabled and bool(self._api_keys)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Any:
        if not self._active:
            request.state.role = "operator"
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key not in self._api_keys:
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "unauthorized",
                        "message": "Missing or invalid API key",
                    }
                },
            )

        request.state.role = self._api_keys[api_key]
        return await call_next(request)


class RoleDeniedError(Exception):
    """Raised when a request lacks the required role."""

    def __init__(self, required_role: str) -> None:
        self.required_role = required_role
        super().__init__(f"This endpoint requires {required_role} role")


def require_role(required_role: str):
    """Return a FastAPI ``Depends`` that enforces a minimum role.

    Usage::

        @app.post("/coverage")
        def create_coverage(..., _=Depends(require_role("operator"))):
            ...

    Raises ``RoleDeniedError`` which should be caught by an exception
    handler that returns a 403 JSON response.
    """

    def _check(request: Request) -> None:
        role = getattr(request.state, "role", None)
        if role != required_role:
            raise RoleDeniedError(required_role)

    return Depends(_check)
