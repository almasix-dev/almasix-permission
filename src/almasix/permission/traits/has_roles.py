"""HasRoles — roles + permissions on authenticatable models."""

from __future__ import annotations

from typing import Any

from almasix.orm import relation
from almasix.orm.morph import morph_alias

from almasix.permission.events import RoleAttachedEvent, RoleDetachedEvent, dispatch_event
from almasix.permission.exceptions import GuardDoesNotMatch, RoleDoesNotExist
from almasix.permission.helpers import (
    collect_names,
    get_role_class,
    guard_name_for,
    model_morph_key,
    normalize_name,
    role_pivot_key,
    table_names,
    team_foreign_key,
    teams_enabled,
)
from almasix.permission.teams import get_permissions_team_id
from almasix.permission.traits.has_permissions import HasPermissions, _flatten


class HasRoles(HasPermissions):
    """Roles mixin — includes ``HasPermissions``."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._role_name_cache: set[str] | None = None

    @relation
    def roles(self) -> Any:
        role_cls = get_role_class()
        table = table_names().get("model_has_roles") or "model_has_roles"
        rel = self.morph_to_many(role_cls, "model", table=table)
        morph_key = model_morph_key()
        if morph_key != "model_id":  # pragma: no cover - custom morph key
            rel.foreign_pivot_key = morph_key
        pivot_key = role_pivot_key()
        if pivot_key != "role_id":  # pragma: no cover - custom pivot key
            rel.related_pivot_key = pivot_key
        if teams_enabled():
            rel = rel.where_pivot_in(team_foreign_key(), [get_permissions_team_id()])
        return rel

    def forget_cached_roles(self) -> None:
        self._role_name_cache = None
        self.forget_cached_permissions()

    def _ensure_same_role_guard(self, role: Any) -> None:
        expected = guard_name_for(self)
        given = getattr(role, "guard_name", None) or expected
        if str(given) != str(expected):
            raise GuardDoesNotMatch(str(given), str(expected))

    async def _resolve_role(self, role: Any, guard: str | None = None) -> Any:
        from enum import Enum

        role_cls = get_role_class()
        if isinstance(role, role_cls):
            self._ensure_same_role_guard(role)
            return role
        if isinstance(role, Enum):
            name = normalize_name(role)
        elif isinstance(role, (str, int)):
            name = normalize_name(role)
        else:
            name = normalize_name(getattr(role, "name", role))
        return await role_cls.find_by_name(name, guard or guard_name_for(self))

    async def assign_role(self, *roles: Any) -> Any:
        items = [await self._resolve_role(r) for r in _flatten(roles)]
        if not items:
            return self
        attrs = {}
        if teams_enabled():
            attrs[team_foreign_key()] = get_permissions_team_id()
        await self.roles().attach([r.get_key() for r in items], attrs)
        self.forget_cached_roles()
        dispatch_event(
            RoleAttachedEvent(
                self, items, get_permissions_team_id() if teams_enabled() else None
            )
        )
        return self

    async def remove_role(self, *roles: Any) -> Any:
        items = [await self._resolve_role(r) for r in _flatten(roles)]
        if items:
            await self.roles().detach([r.get_key() for r in items])
        self.forget_cached_roles()
        dispatch_event(
            RoleDetachedEvent(
                self, items, get_permissions_team_id() if teams_enabled() else None
            )
        )
        return self

    async def sync_roles(self, *roles: Any) -> Any:
        items = [await self._resolve_role(r) for r in _flatten(roles)]
        ids = [r.get_key() for r in items]
        await self._sync_morph_roles(ids)
        self.forget_cached_roles()
        return self

    async def _sync_morph_roles(self, ids: list[Any]) -> None:
        from almasix.orm import QueryBuilder

        table = table_names().get("model_has_roles") or "model_has_roles"
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
        if ids:
            attrs = {}
            if teams_enabled():
                attrs[team_foreign_key()] = get_permissions_team_id()
            await self.roles().attach(ids, attrs)

    def has_role(self, role: Any, guard: str | None = None) -> bool:
        names = collect_names(role)
        cached = self._role_name_cache
        if cached is None:
            try:
                from almasix.permission.traits.has_permissions import _run

                cached = set(_run(self._load_role_names(guard)))
                self._role_name_cache = cached
            except Exception:  # pragma: no cover
                return False
        return any(name in cached for name in names)

    async def _load_role_names(self, guard: str | None = None) -> set[str]:
        roles = await self.roles().get()
        expected = guard or guard_name_for(self)
        names = {
            normalize_name(r.name)
            for r in roles
            if getattr(r, "guard_name", expected) == expected
        }
        self._role_name_cache = names
        return names

    def has_any_role(self, *roles: Any) -> bool:
        return any(self.has_role(r) for r in _flatten(roles))

    def has_all_roles(self, *roles: Any) -> bool:
        return all(self.has_role(r) for r in _flatten(roles))

    def has_exact_roles(self, *roles: Any) -> bool:
        wanted = set(collect_names(*roles))
        cached = self._role_name_cache
        if cached is None:
            try:
                from almasix.permission.traits.has_permissions import _run

                cached = set(_run(self._load_role_names()))
                self._role_name_cache = cached
            except Exception:  # pragma: no cover
                return False
        return cached == wanted

    async def get_role_names(self) -> list[str]:
        return sorted(await self._load_role_names())

    @classmethod
    def scope_role(cls, query: Any, *roles: Any) -> Any:
        names = collect_names(*roles)
        return query.where_has("roles", lambda q: q.where_in("name", names))

    @classmethod
    def scope_without_role(cls, query: Any, *roles: Any) -> Any:
        names = collect_names(*roles)
        return query.where_doesnt_have("roles", lambda q: q.where_in("name", names))
