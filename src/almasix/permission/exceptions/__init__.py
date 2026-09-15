"""Permission package exceptions."""

from __future__ import annotations

from typing import Any


class PermissionError(Exception):
    """Base package error."""


class RoleDoesNotExist(PermissionError):
    def __init__(self, role_name: str = "", guard_name: str | None = None) -> None:
        self.role_name = role_name
        self.guard_name = guard_name
        guard = f" for guard `{guard_name}`" if guard_name else ""
        super().__init__(f"There is no role named `{role_name}`{guard}.")


class PermissionDoesNotExist(PermissionError):
    def __init__(self, permission_name: str = "", guard_name: str | None = None) -> None:
        self.permission_name = permission_name
        self.guard_name = guard_name
        guard = f" for guard `{guard_name}`" if guard_name else ""
        super().__init__(f"There is no permission named `{permission_name}`{guard}.")


class RoleAlreadyExists(PermissionError):
    def __init__(self, role_name: str = "", guard_name: str | None = None) -> None:
        super().__init__(
            f"A role `{role_name}` already exists"
            + (f" for guard `{guard_name}`." if guard_name else ".")
        )


class PermissionAlreadyExists(PermissionError):
    def __init__(self, permission_name: str = "", guard_name: str | None = None) -> None:
        super().__init__(
            f"A permission `{permission_name}` already exists"
            + (f" for guard `{guard_name}`." if guard_name else ".")
        )


class GuardDoesNotMatch(PermissionError):
    def __init__(self, given: str = "", expected: str = "") -> None:
        self.given = given
        self.expected = expected
        super().__init__(
            f"The given role or permission should use guard `{expected}` instead of `{given}`."
        )


class UnauthorizedException(PermissionError):
    """Raised by role/permission middleware when the user may not proceed."""

    def __init__(
        self,
        message: str = "User does not have the right roles or permissions.",
        *,
        required_roles: list[str] | None = None,
        required_permissions: list[str] | None = None,
    ) -> None:
        self.required_roles = list(required_roles or [])
        self.required_permissions = list(required_permissions or [])
        super().__init__(message)

    def to_http(self) -> Any:
        from almasix.http import ForbiddenHttpException

        return ForbiddenHttpException(str(self))
