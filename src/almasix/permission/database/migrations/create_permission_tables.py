"""Create permission tables."""

from __future__ import annotations

from almasix.orm import Blueprint, Migration, Schema

from almasix.permission.helpers import (
    model_morph_key,
    permission_config,
    permission_pivot_key,
    role_pivot_key,
    table_names,
    team_foreign_key,
    teams_enabled,
)


class CreatePermissionTables(Migration):
    async def up(self) -> None:
        names = table_names()
        teams = teams_enabled()
        key_type = str(permission_config("key_type") or "int")

        await Schema.create(names.get("permissions") or "permissions", self._permissions)
        await Schema.create(names.get("roles") or "roles", lambda t: self._roles(t, teams, key_type))
        await Schema.create(
            names.get("model_has_permissions") or "model_has_permissions",
            lambda t: self._model_has_permissions(t, teams, key_type),
        )
        await Schema.create(
            names.get("model_has_roles") or "model_has_roles",
            lambda t: self._model_has_roles(t, teams, key_type),
        )
        await Schema.create(
            names.get("role_has_permissions") or "role_has_permissions",
            lambda t: self._role_has_permissions(t, key_type),
        )

    async def down(self) -> None:
        names = table_names()
        for key in (
            "role_has_permissions",
            "model_has_roles",
            "model_has_permissions",
            "roles",
            "permissions",
        ):
            await Schema.drop_if_exists(names.get(key) or key)

    def _pk(self, table: Blueprint, key_type: str) -> None:
        if key_type == "uuid":
            table.uuid("id").primary()
        elif key_type == "ulid":
            table.ulid("id").primary()
        else:
            table.id()

    def _fk(self, table: Blueprint, name: str, key_type: str) -> None:
        if key_type == "uuid":
            table.foreign_uuid(name)
        elif key_type == "ulid":
            table.foreign_ulid(name)
        else:
            table.unsigned_big_integer(name)

    def _permissions(self, table: Blueprint) -> None:
        key_type = str(permission_config("key_type") or "int")
        self._pk(table, key_type)
        table.string("name")
        table.string("guard_name")
        table.timestamps()
        table.unique(["name", "guard_name"])

    def _roles(self, table: Blueprint, teams: bool, key_type: str) -> None:
        self._pk(table, key_type)
        if teams:
            table.unsigned_big_integer(team_foreign_key()).nullable().index()
        table.string("name")
        table.string("guard_name")
        table.timestamps()
        if teams:
            table.unique([team_foreign_key(), "name", "guard_name"])
        else:
            table.unique(["name", "guard_name"])

    def _model_has_permissions(self, table: Blueprint, teams: bool, key_type: str) -> None:
        pivot = permission_pivot_key()
        morph = model_morph_key()
        self._fk(table, pivot, key_type)
        table.string("model_type")
        table.unsigned_big_integer(morph)
        table.index([morph, "model_type"])
        if teams:
            table.unsigned_big_integer(team_foreign_key()).index()
            table.primary([team_foreign_key(), pivot, morph, "model_type"])
        else:
            table.primary([pivot, morph, "model_type"])

    def _model_has_roles(self, table: Blueprint, teams: bool, key_type: str) -> None:
        pivot = role_pivot_key()
        morph = model_morph_key()
        self._fk(table, pivot, key_type)
        table.string("model_type")
        table.unsigned_big_integer(morph)
        table.index([morph, "model_type"])
        if teams:
            table.unsigned_big_integer(team_foreign_key()).index()
            table.primary([team_foreign_key(), pivot, morph, "model_type"])
        else:
            table.primary([pivot, morph, "model_type"])

    def _role_has_permissions(self, table: Blueprint, key_type: str) -> None:
        self._fk(table, permission_pivot_key(), key_type)
        self._fk(table, role_pivot_key(), key_type)
        table.primary([permission_pivot_key(), role_pivot_key()])
