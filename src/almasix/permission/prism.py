"""Prism ``@role`` / ``@haspermission`` style directives."""

from __future__ import annotations

from typing import Any


def _auth_user() -> Any:
    try:
        from almasix.auth.guard import auth

        return auth().user()
    except Exception:  # pragma: no cover - auth may be unbound outside HTTP
        return None


def permission_has_role(role: Any, guard: str | None = None) -> bool:
    user = _auth_user()
    if user is None or not hasattr(user, "has_role"):
        return False
    return bool(user.has_role(role, guard))


def permission_has_any_role(*roles: Any) -> bool:
    user = _auth_user()
    if user is None or not hasattr(user, "has_any_role"):
        return False
    return bool(user.has_any_role(*roles))


def permission_has_all_roles(*roles: Any) -> bool:
    user = _auth_user()
    if user is None or not hasattr(user, "has_all_roles"):
        return False
    return bool(user.has_all_roles(*roles))


def permission_has_exact_roles(*roles: Any) -> bool:
    user = _auth_user()
    if user is None or not hasattr(user, "has_exact_roles"):
        return False
    return bool(user.has_exact_roles(*roles))


def permission_has_permission(permission: Any, guard: str | None = None) -> bool:
    user = _auth_user()
    if user is None or not hasattr(user, "check_permission_to"):
        return False
    return bool(user.check_permission_to(permission, guard))


def _gate_open(check: str) -> str:
    """Emit code that gates subsequent ``__w`` output until a matching end directive."""
    return (
        f"context.setdefault('__permission_gates', []).append("
        f"bool(__eval({check!r})))\n"
        "def __w(s):\n"
        "    if all(context.get('__permission_gates', [True])):\n"
        "        __b.append(s)"
    )


def _gate_close(_expr: str = "") -> str:
    return (
        "(_gates := context.get('__permission_gates')) and _gates.pop()\n"
        "def __w(s):\n"
        "    if all(context.get('__permission_gates', [True])):\n"
        "        __b.append(s)"
    )


def register_prism_directives(engine: Any) -> None:
    """Register role/permission Prism directives on ``engine``."""

    def inject(ctx: dict[str, Any]) -> None:
        ctx["permission_has_role"] = permission_has_role
        ctx["permission_has_any_role"] = permission_has_any_role
        ctx["permission_has_all_roles"] = permission_has_all_roles
        ctx["permission_has_exact_roles"] = permission_has_exact_roles
        ctx["permission_has_permission"] = permission_has_permission

    if hasattr(engine, "composer"):
        engine.composer("*", inject)

    pairs = {
        "role": "permission_has_role({expr})",
        "hasrole": "permission_has_role({expr})",
        "hasanyrole": "permission_has_any_role({expr})",
        "hasallroles": "permission_has_all_roles({expr})",
        "hasexactroles": "permission_has_exact_roles({expr})",
        "unlessrole": "not permission_has_role({expr})",
        "haspermission": "permission_has_permission({expr})",
    }
    for name, template in pairs.items():
        engine.directive(
            name,
            lambda expr, t=template: _gate_open(t.format(expr=expr)),
        )
        engine.directive(f"end{name}", _gate_close)
