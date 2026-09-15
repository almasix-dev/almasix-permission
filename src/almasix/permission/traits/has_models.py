"""HasModels — assign a role to many models (role-side helpers)."""

from __future__ import annotations

from typing import Any

from almasix.orm.morph import morph_alias

from almasix.permission.helpers import (
    model_morph_key,
    permission_config,
    role_pivot_key,
    table_names,
    team_foreign_key,
    teams_enabled,
)
from almasix.permission.teams import get_permissions_team_id


class HasModels:
    """Inverse assignment helpers on ``Role`` (``assign_to_models``, etc.)."""

    async def assign_to_models(self, *models: Any) -> Any:
        for model in _flatten_models(models):
            if hasattr(model, "assign_role"):
                await model.assign_role(self)
            else:
                await self._attach_model(model)
        return self

    async def remove_from_models(self, *models: Any) -> Any:
        for model in _flatten_models(models):
            if hasattr(model, "remove_role"):
                await model.remove_role(self)
            else:
                await self._detach_model(model)
        return self

    async def sync_models(self, *models: Any) -> Any:
        resolved = list(_flatten_models(models))
        # Detach all current, then attach
        await self._detach_all_models()
        for model in resolved:
            await self._attach_model(model)
        return self

    async def users(self) -> list[Any]:
        """Return models currently assigned this role (default auth model when set)."""
        from almasix.orm import QueryBuilder

        table = table_names().get("model_has_roles") or "model_has_roles"
        morph_key = model_morph_key()
        pivot_key = role_pivot_key()
        rows = await (
            QueryBuilder.for_table(table)
            .where(pivot_key, "=", self.get_key())
            .get_raw()
        )
        default_path = permission_config("models.default_model")
        if not default_path or not rows:
            return []
        from almasix.permission.helpers import import_string

        model_cls = import_string(str(default_path)) if isinstance(default_path, str) else default_path
        ids = [row[morph_key] for row in rows if row.get("model_type") == morph_alias(model_cls)]
        if not ids:
            return []
        return list(await model_cls.query().where_in(model_cls.primary_key, ids).get())

    async def _attach_model(self, model: Any) -> None:
        from almasix.orm import QueryBuilder

        table = table_names().get("model_has_roles") or "model_has_roles"
        row = {
            role_pivot_key(): self.get_key(),
            model_morph_key(): model.get_key(),
            "model_type": morph_alias(type(model)),
        }
        if teams_enabled():
            row[team_foreign_key()] = get_permissions_team_id()
        await QueryBuilder.for_table(table).insert([row])

    async def _detach_model(self, model: Any) -> None:
        from almasix.orm import QueryBuilder

        table = table_names().get("model_has_roles") or "model_has_roles"
        builder = (
            QueryBuilder.for_table(table)
            .where(role_pivot_key(), "=", self.get_key())
            .where(model_morph_key(), "=", model.get_key())
            .where("model_type", "=", morph_alias(type(model)))
        )
        if teams_enabled():
            builder = builder.where(team_foreign_key(), "=", get_permissions_team_id())
        await builder.delete()

    async def _detach_all_models(self) -> None:
        from almasix.orm import QueryBuilder

        table = table_names().get("model_has_roles") or "model_has_roles"
        builder = QueryBuilder.for_table(table).where(role_pivot_key(), "=", self.get_key())
        if teams_enabled():
            builder = builder.where(team_foreign_key(), "=", get_permissions_team_id())
        await builder.delete()


def _flatten_models(values: Any) -> list[Any]:
    if values is None:
        return []
    if isinstance(values, (list, tuple, set)):
        out: list[Any] = []
        for item in values:
            out.extend(_flatten_models(item))
        return out
    if isinstance(values, (int, str)) and not hasattr(values, "get_key"):
        raise TypeError("Pass model instances to assign_to_models")
    return [values]
