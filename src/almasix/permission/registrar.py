"""PermissionRegistrar — cache + Gate.before registration."""

from __future__ import annotations

from typing import Any

from almasix.permission.helpers import (
    get_permission_class,
    permission_config,
    teams_enabled,
)
from almasix.permission.teams import get_permissions_team_id


class PermissionRegistrar:
    """Loads all permissions (optionally cached) and answers Gate checks."""

    def __init__(self) -> None:
        self._permissions: list[Any] | None = None

    def cache_key(self) -> str:
        base = str((permission_config("cache") or {}).get("key") or "almasix.permission.cache")
        if teams_enabled():
            team = get_permissions_team_id()
            return f"{base}.team.{team}"
        return base

    def expiration(self) -> int:
        cache = permission_config("cache") or {}
        return int(cache.get("expiration_time") or 86400)

    def store_name(self) -> str | None:
        cache = permission_config("cache") or {}
        name = cache.get("store") or "default"
        return None if name in (None, "default") else str(name)

    def _cache(self) -> Any:
        from almasix.cache import Cache

        return Cache.store(self.store_name())

    async def get_permissions(self) -> list[Any]:
        if self._permissions is not None:
            return self._permissions
        cached = self._cache().get(self.cache_key())
        if cached is not None:
            self._permissions = list(cached)
            return self._permissions
        permission_cls = get_permission_class()
        rows = await permission_cls.query().get()
        self._permissions = list(rows)
        self._cache().put(self.cache_key(), self._permissions, self.expiration())
        return self._permissions

    def forget_cached_permissions(self) -> None:
        self._permissions = None
        try:
            self._cache().forget(self.cache_key())
        except Exception:  # pragma: no cover - cache may be unbound in unit slices
            pass

    async def clear_class_permission_cache(self) -> None:
        self.forget_cached_permissions()

    def check_permission(self, user: Any, ability: str, *arguments: Any) -> bool | None:
        """Gate.before callback — ``True`` to allow, ``None`` to continue."""
        if user is None or not hasattr(user, "check_permission_to"):
            return None
        guard = arguments[0] if arguments and isinstance(arguments[0], str) else None
        try:
            if user.check_permission_to(ability, guard):
                return True
        except Exception:  # pragma: no cover
            return None
        return None


_registrar: PermissionRegistrar | None = None


def get_permission_registrar() -> PermissionRegistrar:
    global _registrar
    if _registrar is None:
        _registrar = PermissionRegistrar()
    return _registrar


def set_permission_registrar(registrar: PermissionRegistrar | None) -> None:
    global _registrar
    _registrar = registrar
