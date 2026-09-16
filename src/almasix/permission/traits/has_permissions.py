"""HasPermissions — direct permissions on a model (or on a Role)."""

from __future__ import annotations

from typing import Any

from almasix.orm import relation
from almasix.orm.morph import morph_alias

from almasix.permission.events import (
    PermissionAttachedEvent,
    PermissionDetachedEvent,
    dispatch_event,
)
from almasix.permission.exceptions import GuardDoesNotMatch
from almasix.permission.helpers import (
    collect_names,
    get_permission_class,
    guard_name_for,
    model_morph_key,
    normalize_name,
    permission_config,
    permission_pivot_key,
    table_names,
    team_foreign_key,
    teams_enabled,
)
from almasix.permission.registrar import get_permission_registrar
from almasix.permission.teams import get_permissions_team_id
from almasix.permission.wildcard import wildcard_implies


def _run(coro: Any) -> Any:
    import asyncio

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    def _in_thread() -> Any:  # pragma: no cover
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()

    return _in_thread()


class HasPermissions:
    """Assign and check direct permissions."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._permission_name_cache: set[str] | None = None

    @relation
    def permissions(self) -> Any:
        """Direct permissions via ``model_has_permissions`` (Role overrides)."""
        permission_cls = get_permission_class()
        table = table_names().get("model_has_permissions") or "model_has_permissions"
        rel = self.morph_to_many(permission_cls, "model", table=table)
        morph_key = model_morph_key()
        if morph_key != "model_id":  # pragma: no cover - custom morph key
            rel.foreign_pivot_key = morph_key
        pivot_key = permission_pivot_key()
        if pivot_key != "permission_id":  # pragma: no cover - custom pivot key
            rel.related_pivot_key = pivot_key
        if teams_enabled():
            rel = rel.where_pivot_in(team_foreign_key(), [get_permissions_team_id()])
        return rel

    def forget_cached_permissions(self) -> None:
        self._permission_name_cache = None
        get_permission_registrar().forget_cached_permissions()

    def _remember_permissions(self, names: set[str]) -> None:
        self._permission_name_cache = set(names)

    def _ensure_same_guard(self, permission: Any) -> None:
        expected = guard_name_for(self)
        given = getattr(permission, "guard_name", None) or expected
        if str(given) != str(expected):
            raise GuardDoesNotMatch(str(given), str(expected))

    async def _resolve_permission(self, permission: Any, guard: str | None = None) -> Any:
        from enum import Enum

        permission_cls = get_permission_class()
        if isinstance(permission, permission_cls):
            self._ensure_same_guard(permission)
            return permission
        if isinstance(permission, Enum):
            name = normalize_name(permission)
        else:
            name = normalize_name(permission)
        guard_name = guard or guard_name_for(self)
        return await permission_cls.find_by_name(name, guard_name)

    async def give_permission_to(self, *permissions: Any) -> Any:
        items = [await self._resolve_permission(p) for p in _flatten(permissions)]
        if not items:
            return self
        attrs: dict[str, Any] = {}
        if teams_enabled() and not self._uses_role_permission_pivot():
            attrs[team_foreign_key()] = get_permissions_team_id()
        await self.permissions().attach([p.get_key() for p in items], attrs or None)
        self.forget_cached_permissions()
        dispatch_event(
            PermissionAttachedEvent(
                self, items, get_permissions_team_id() if teams_enabled() else None
            )
        )
        return self

    def _uses_role_permission_pivot(self) -> bool:
        table = getattr(self, "table", None) or type(self).get_table()
        return table == (table_names().get("roles") or "roles")

    async def revoke_permission_to(self, *permissions: Any) -> Any:
        items = [await self._resolve_permission(p) for p in _flatten(permissions)]
        if items:
            await self.permissions().detach([p.get_key() for p in items])
        self.forget_cached_permissions()
        dispatch_event(
            PermissionDetachedEvent(
                self, items, get_permissions_team_id() if teams_enabled() else None
            )
        )
        return self

    async def sync_permissions(self, *permissions: Any) -> Any:
        items = [await self._resolve_permission(p) for p in _flatten(permissions)]
        ids = [p.get_key() for p in items]
        if self._uses_role_permission_pivot():
            await self.permissions().sync(ids)
        else:
            await self._sync_morph_permissions(ids)
        self.forget_cached_permissions()
        return self

    async def _sync_morph_permissions(self, ids: list[Any]) -> None:
        from almasix.orm import QueryBuilder

        table = table_names().get("model_has_permissions") or "model_has_permissions"
        morph_type = morph_alias(type(self))
        morph_key = model_morph_key()
        builder = (
            QueryBuilder.for_table(table)
            .where(morph_key, "=", self.get_key())
            .where("model_type", "=", morph_type)
        )
        if teams_enabled():
            builder = builder.where(team_foreign_key(), "=", get_permissions_team_id())
        await builder.delete()
        if not ids:
            return
        attrs = {}
        if teams_enabled():
            attrs[team_foreign_key()] = get_permissions_team_id()
        await self.permissions().attach(ids, attrs)

    async def has_permission_to(self, permission: Any, guard_name: str | None = None) -> bool:
        return self.check_permission_to(permission, guard_name)

    def check_permission_to(self, permission: Any, guard_name: str | None = None) -> bool:
        """Sync check used by Gate.before — prefers in-memory caches."""
        from enum import Enum

        if isinstance(permission, Enum):
            name = normalize_name(permission)
        elif isinstance(permission, (str, int)):
            name = normalize_name(permission)
        else:
            name = normalize_name(getattr(permission, "name", permission))
        if guard_name is not None:
            try:
                names = set(_run(self._load_permission_names(guard_name)))
            except Exception:  # pragma: no cover - async loop + memory DB
                return False
        else:
            names = self._permission_name_cache
            if names is None:
                try:
                    names = set(_run(self._load_permission_names(guard_name)))
                    self._permission_name_cache = names
                except Exception:  # pragma: no cover - async loop + memory DB
                    return False
        if name in names:
            return True
        if permission_config("enable_wildcard_permission", False):
            return any(wildcard_implies(owned, name) for owned in names)
        return False

    async def _load_permission_names(self, guard_name: str | None = None) -> set[str]:
        all_perms = await self.get_all_permissions()
        guard = guard_name or guard_name_for(self)
        names = {
            normalize_name(p.name) for p in all_perms if getattr(p, "guard_name", guard) == guard
        }
        if guard_name is None:
            self._permission_name_cache = names
        return names

    async def has_direct_permission(self, permission: Any) -> bool:
        name = normalize_name(getattr(permission, "name", permission))
        direct = await self.get_direct_permissions()
        return any(normalize_name(p.name) == name for p in direct)

    async def has_any_permission(self, *permissions: Any) -> bool:
        for permission in _flatten(permissions):
            if await self.has_permission_to(permission):
                return True
        return False

    async def has_all_permissions(self, *permissions: Any) -> bool:
        for permission in _flatten(permissions):
            if not await self.has_permission_to(permission):
                return False
        return True

    async def get_direct_permissions(self) -> list[Any]:
        return list(await self.permissions().get())

    async def get_permissions_via_roles(self) -> list[Any]:
        if not hasattr(self, "roles"):
            return []
        roles = await self.roles().get()
        collected: dict[Any, Any] = {}
        for role in roles:
            for permission in await role.permissions().get():
                collected[permission.get_key()] = permission
        return list(collected.values())

    async def get_all_permissions(self) -> list[Any]:
        direct = await self.get_direct_permissions()
        via_roles = await self.get_permissions_via_roles()
        merged: dict[Any, Any] = {}
        for permission in [*direct, *via_roles]:
            merged[permission.get_key()] = permission
        result = list(merged.values())
        self._permission_name_cache = {normalize_name(p.name) for p in result}
        return result

    @classmethod
    def scope_permission(cls, query: Any, *permissions: Any) -> Any:
        names = collect_names(*permissions)
        return query.where_has(
            "permissions",
            lambda q: q.where_in("name", names),
        )

    @classmethod
    def scope_without_permission(cls, query: Any, *permissions: Any) -> Any:
        names = collect_names(*permissions)
        return query.where_doesnt_have(
            "permissions",
            lambda q: q.where_in("name", names),
        )


def _flatten(values: Any) -> list[Any]:
    if values is None:
        return []
    if isinstance(values, (list, tuple, set)) and not hasattr(values, "name"):
        out: list[Any] = []
        for item in values:
            out.extend(_flatten(item))
        return out
    # Single pipe-separated string
    if isinstance(values, str) and "|" in values:
        return [part.strip() for part in values.split("|") if part.strip()]
    return [values]
