"""Add teams columns to an existing permission install."""

from __future__ import annotations

from almasix.orm import Blueprint, Migration, Schema

from almasix.permission.helpers import table_names, team_foreign_key


class AddTeamsFields(Migration):
    async def up(self) -> None:
        names = table_names()
        tfk = team_foreign_key()

        def roles(table: Blueprint) -> None:
            table.unsigned_big_integer(tfk).nullable().index()

        def model_has_permissions(table: Blueprint) -> None:
            table.unsigned_big_integer(tfk).index()

        def model_has_roles(table: Blueprint) -> None:
            table.unsigned_big_integer(tfk).index()

        await Schema.table(names.get("roles") or "roles", roles)
        await Schema.table(
            names.get("model_has_permissions") or "model_has_permissions",
            model_has_permissions,
        )
        await Schema.table(names.get("model_has_roles") or "model_has_roles", model_has_roles)

    async def down(self) -> None:
        names = table_names()
        tfk = team_foreign_key()

        def drop_col(table: Blueprint) -> None:
            table.drop_column(tfk)

        for key in ("roles", "model_has_permissions", "model_has_roles"):
            await Schema.table(names.get(key) or key, drop_col)
