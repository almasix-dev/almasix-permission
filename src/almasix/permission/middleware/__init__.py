"""HTTP middleware: role, permission, role_or_permission."""

from __future__ import annotations

from typing import Any

from almasix.http.middleware import Middleware, NextCall
from starlette.responses import Response as StarletteResponse

from almasix.permission.exceptions import UnauthorizedException
from almasix.permission.helpers import collect_names, permission_config


def _current_user(request: Any, guard: str | None = None) -> Any:
    if guard is not None:
        try:
            from almasix.auth.guard import auth

            guarded = auth().guard(guard).user()
            if guarded is not None:
                return guarded
        except Exception:  # pragma: no cover - auth unbound outside HTTP
            pass
    user = getattr(request, "user", None)
    if user is not None and not isinstance(user, (str, bytes)):
        return user
    try:  # pragma: no cover - request without user falls back to auth()
        from almasix.auth.guard import auth

        return auth().user() if guard is None else auth().guard(guard).user()
    except Exception:  # pragma: no cover
        return None


def _parse_names_and_guard(value: str) -> tuple[list[str], str | None]:
    """Split ``admin|editor,api`` into names + optional guard (Spatie-style)."""
    text = (value or "").strip()
    if not text:
        return [], None
    if "," in text:
        names_part, _, guard = text.rpartition(",")
        guard = guard.strip() or None
        return collect_names(names_part.strip()), guard
    return collect_names(text), None


def _format_using(alias: str, names: str | list[str], guard: str | None = None) -> str:
    if isinstance(names, list):
        names = "|".join(names)
    args = names if guard is None else f"{names},{guard}"
    return f"{alias}:{args}"


class RoleMiddleware(Middleware):
    """Require the user to have any of the given roles (``role:admin|editor``).

    Optional guard: ``role:admin,api`` or ``RoleMiddleware.using('admin', 'api')``.
    """

    def __init__(self, role: str = "") -> None:
        self.roles, self.guard = _parse_names_and_guard(role)

    @classmethod
    def using(cls, roles: str | list[str], guard: str | None = None) -> str:
        return _format_using("role", roles, guard)

    async def handle(self, request: Any, call_next: NextCall) -> StarletteResponse:
        user = _current_user(request, self.guard)
        if user is None or not hasattr(user, "has_role"):
            raise _unauthorized(roles=self.roles).to_http()
        if not any(user.has_role(role, self.guard) for role in self.roles):
            raise _unauthorized(roles=self.roles).to_http()
        return await call_next(request)


class PermissionMiddleware(Middleware):
    """Require any of the given permissions (``permission:edit articles``).

    Optional guard: ``permission:edit articles,api``.
    """

    def __init__(self, permission: str = "") -> None:
        self.permissions, self.guard = _parse_names_and_guard(permission)

    @classmethod
    def using(cls, permissions: str | list[str], guard: str | None = None) -> str:
        return _format_using("permission", permissions, guard)

    async def handle(self, request: Any, call_next: NextCall) -> StarletteResponse:
        user = _current_user(request, self.guard)
        if user is None or not hasattr(user, "check_permission_to"):
            raise _unauthorized(permissions=self.permissions).to_http()
        if not any(user.check_permission_to(p, self.guard) for p in self.permissions):
            raise _unauthorized(permissions=self.permissions).to_http()
        return await call_next(request)


class RoleOrPermissionMiddleware(Middleware):
    """Pass if the user has any listed role or permission.

    Optional guard: ``role_or_permission:admin|edit articles,api``.
    """

    def __init__(self, role_or_permission: str = "") -> None:
        self.names, self.guard = _parse_names_and_guard(role_or_permission)

    @classmethod
    def using(cls, values: str | list[str], guard: str | None = None) -> str:
        return _format_using("role_or_permission", values, guard)

    async def handle(self, request: Any, call_next: NextCall) -> StarletteResponse:
        user = _current_user(request, self.guard)
        if user is None:
            raise _unauthorized(roles=self.names, permissions=self.names).to_http()
        if hasattr(user, "has_role") and any(
            user.has_role(name, self.guard) for name in self.names
        ):
            return await call_next(request)
        if hasattr(user, "check_permission_to") and any(
            user.check_permission_to(name, self.guard) for name in self.names
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
