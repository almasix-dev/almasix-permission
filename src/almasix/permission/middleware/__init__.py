"""HTTP middleware: role, permission, role_or_permission."""

from __future__ import annotations

from typing import Any

from starlette.responses import Response as StarletteResponse

from almasix.http.middleware import Middleware, NextCall
from almasix.permission.exceptions import UnauthorizedException
from almasix.permission.helpers import collect_names, permission_config


def _current_user(request: Any) -> Any:
    user = getattr(request, "user", None)
    if user is not None and not isinstance(user, (str, bytes)):
        return user
    try:  # pragma: no cover - request without user falls back to auth()
        from almasix.auth.guard import auth

        return auth().user()
    except Exception:  # pragma: no cover
        return None


def _split_roles(value: str) -> list[str]:
    return collect_names(value)


class RoleMiddleware(Middleware):
    """Require the user to have any of the given roles (``role:admin|editor``)."""

    def __init__(self, role: str = "") -> None:
        self.roles = _split_roles(role)

    @classmethod
    def using(cls, roles: str | list[str]) -> str:
        if isinstance(roles, list):
            roles = "|".join(roles)
        return f"role:{roles}"

    async def handle(self, request: Any, call_next: NextCall) -> StarletteResponse:
        user = _current_user(request)
        if user is None or not hasattr(user, "has_any_role"):
            raise _unauthorized(roles=self.roles).to_http()
        if not user.has_any_role(*self.roles):
            raise _unauthorized(roles=self.roles).to_http()
        return await call_next(request)


class PermissionMiddleware(Middleware):
    """Require any of the given permissions (``permission:edit articles``)."""

    def __init__(self, permission: str = "") -> None:
        self.permissions = _split_roles(permission)

    @classmethod
    def using(cls, permissions: str | list[str]) -> str:
        if isinstance(permissions, list):
            permissions = "|".join(permissions)
        return f"permission:{permissions}"

    async def handle(self, request: Any, call_next: NextCall) -> StarletteResponse:
        user = _current_user(request)
        if user is None or not hasattr(user, "check_permission_to"):
            raise _unauthorized(permissions=self.permissions).to_http()
        if not any(user.check_permission_to(p) for p in self.permissions):
            raise _unauthorized(permissions=self.permissions).to_http()
        return await call_next(request)


class RoleOrPermissionMiddleware(Middleware):
    """Pass if the user has any listed role or permission."""

    def __init__(self, role_or_permission: str = "") -> None:
        self.names = _split_roles(role_or_permission)

    @classmethod
    def using(cls, values: str | list[str]) -> str:
        if isinstance(values, list):
            values = "|".join(values)
        return f"role_or_permission:{values}"

    async def handle(self, request: Any, call_next: NextCall) -> StarletteResponse:
        user = _current_user(request)
        if user is None:
            raise _unauthorized(roles=self.names, permissions=self.names).to_http()
        if hasattr(user, "has_any_role") and user.has_any_role(*self.names):
            return await call_next(request)
        if hasattr(user, "check_permission_to") and any(
            user.check_permission_to(name) for name in self.names
        ):
            return await call_next(request)
        raise _unauthorized(roles=self.names, permissions=self.names).to_http()


def _unauthorized(
    *,
    roles: list[str] | None = None,
    permissions: list[str] | None = None,
) -> UnauthorizedException:
    message = "User does not have the right roles or permissions."
    show_roles = permission_config("display_role_in_exception", False)
    show_perms = permission_config("display_permission_in_exception", False)
    parts: list[str] = []
    if show_roles and roles:
        parts.append("roles: " + ", ".join(roles))
    if show_perms and permissions:
        parts.append("permissions: " + ", ".join(permissions))
    if parts:
        message = f"{message} ({'; '.join(parts)})"
    return UnauthorizedException(message, required_roles=roles, required_permissions=permissions)
