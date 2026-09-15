"""Permission model."""

from __future__ import annotations

from typing import Any

from almasix.orm import Model, relation

from almasix.permission.exceptions import PermissionAlreadyExists, PermissionDoesNotExist
from almasix.permission.helpers import (
    get_default_guard_name,
    get_role_class,
    normalize_name,
    table_names,
)
from almasix.permission.registrar import get_permission_registrar


class Permission(Model):
    """A named ability scoped to a guard."""

    timestamps = True
    fillable = ("name", "guard_name")

    def __init_subclass__(cls, **kwargs: Any) -> None:  # pragma: no cover
        super().__init_subclass__(**kwargs)

    @classmethod
    def get_table(cls) -> str:
        return str(table_names().get("permissions") or "permissions")

    @relation
    def roles(self) -> Any:
        role_cls = get_role_class()
        pivot = table_names().get("role_has_permissions") or "role_has_permissions"
        return self.belongs_to_many(role_cls, table=pivot)

    @classmethod
    async def create(cls, attributes: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        attrs = {**(attributes or {}), **kwargs}
        attrs["name"] = normalize_name(attrs.get("name"))
        attrs.setdefault("guard_name", get_default_guard_name())
        existing = (
            await cls.query()
            .where("name", attrs["name"])
            .where("guard_name", attrs["guard_name"])
            .first()
        )
        if existing is not None:
            raise PermissionAlreadyExists(attrs["name"], attrs["guard_name"])
        created = await super().create(attrs)
        get_permission_registrar().forget_cached_permissions()
        return created

    @classmethod
    async def find_by_name(cls, name: str, guard_name: str | None = None) -> Any:
        guard = guard_name or get_default_guard_name()
        found = (
            await cls.query().where("name", normalize_name(name)).where("guard_name", guard).first()
        )
        if found is None:
            raise PermissionDoesNotExist(normalize_name(name), guard)
        return found

    @classmethod
    async def find_by_id(cls, id_: Any, guard_name: str | None = None) -> Any:
        query = cls.query().where(cls.primary_key, id_)
        if guard_name is not None:
            query = query.where("guard_name", guard_name)
        found = await query.first()
        if found is None:
            raise PermissionDoesNotExist(str(id_), guard_name)
        return found

    @classmethod
    async def find_or_create(cls, name: str, guard_name: str | None = None) -> Any:
        guard = guard_name or get_default_guard_name()
        try:
            return await cls.find_by_name(name, guard)
        except PermissionDoesNotExist:
            return await cls.create(name=name, guard_name=guard)

    async def delete(self) -> bool | int:
        result = await super().delete()
        get_permission_registrar().forget_cached_permissions()
        return result
