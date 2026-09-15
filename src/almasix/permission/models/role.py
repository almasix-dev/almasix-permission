"""Role model."""

from __future__ import annotations

from typing import Any

from almasix.orm import Model, relation

from almasix.permission.exceptions import RoleAlreadyExists, RoleDoesNotExist
from almasix.permission.helpers import (
    get_default_guard_name,
    get_permission_class,
    normalize_name,
    table_names,
    team_foreign_key,
    teams_enabled,
)
from almasix.permission.registrar import get_permission_registrar
from almasix.permission.teams import get_permissions_team_id
from almasix.permission.traits.has_models import HasModels
from almasix.permission.traits.has_permissions import HasPermissions


class Role(HasPermissions, HasModels, Model):
    """A named group of permissions, optionally scoped to a team."""

    timestamps = True
    fillable = ("name", "guard_name", "team_id")

    @classmethod
    def get_table(cls) -> str:
        return str(table_names().get("roles") or "roles")

    @relation
    def permissions(self) -> Any:
        permission_cls = get_permission_class()
        pivot = table_names().get("role_has_permissions") or "role_has_permissions"
        return self.belongs_to_many(permission_cls, table=pivot)

    @classmethod
    async def create(cls, attributes: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        attrs = {**(attributes or {}), **kwargs}
        attrs["name"] = normalize_name(attrs.get("name"))
        attrs.setdefault("guard_name", get_default_guard_name())
        if teams_enabled():
            attrs.setdefault(team_foreign_key(), get_permissions_team_id())
        query = cls.query().where("name", attrs["name"]).where("guard_name", attrs["guard_name"])
        if teams_enabled():
            query = query.where(team_foreign_key(), attrs.get(team_foreign_key()))
        if await query.first() is not None:
            raise RoleAlreadyExists(attrs["name"], attrs["guard_name"])
        created = await super().create(attrs)
        get_permission_registrar().forget_cached_permissions()
        return created

    @classmethod
    async def find_by_name(cls, name: str, guard_name: str | None = None) -> Any:
        guard = guard_name or get_default_guard_name()
        query = cls.query().where("name", normalize_name(name)).where("guard_name", guard)
        if teams_enabled():
            query = query.where(team_foreign_key(), get_permissions_team_id())
        found = await query.first()
        if found is None:
            raise RoleDoesNotExist(normalize_name(name), guard)
        return found

    @classmethod
    async def find_by_id(cls, id_: Any, guard_name: str | None = None) -> Any:
        query = cls.query().where(cls.primary_key, id_)
        if guard_name is not None:
            query = query.where("guard_name", guard_name)
        if teams_enabled():
            query = query.where(team_foreign_key(), get_permissions_team_id())
        found = await query.first()
        if found is None:
            raise RoleDoesNotExist(str(id_), guard_name)
        return found

    @classmethod
    async def find_or_create(cls, name: str, guard_name: str | None = None) -> Any:
        guard = guard_name or get_default_guard_name()
        try:
            return await cls.find_by_name(name, guard)
        except RoleDoesNotExist:
            return await cls.create(name=name, guard_name=guard)

    async def delete(self) -> bool | int:
        result = await super().delete()
        get_permission_registrar().forget_cached_permissions()
        return result
