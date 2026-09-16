"""HasModels — assign a role to many models (role-side helpers)."""

from __future__ import annotations

from typing import Any

from almasix.orm.morph import morph_alias

from almasix.permission.helpers import (
    import_string,
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

    async def assign_to_models(self, *models: Any, model_class: Any = None) -> Any:
        for model in await self._resolve_models(models, model_class):
            if hasattr(model, "assign_role"):
                await model.assign_role(self)
            else:
                await self._attach_model(model)
        return self

    async def remove_from_models(self, *models: Any, model_class: Any = None) -> Any:
        for model in await self._resolve_models(models, model_class):
            if hasattr(model, "remove_role"):
                await model.remove_role(self)
            else:
                await self._detach_model(model)
        return self

    async def sync_models(self, *models: Any, model_class: Any = None) -> Any:
        resolved = await self._resolve_models(models, model_class)
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
        rows = await QueryBuilder.for_table(table).where(pivot_key, "=", self.get_key()).get_raw()
        default_path = permission_config("models.default_model")
        if not default_path or not rows:
            return []
        model_cls = (
            import_string(str(default_path)) if isinstance(default_path, str) else default_path
        )
        ids = [row[morph_key] for row in rows if row.get("model_type") == morph_alias(model_cls)]
        if not ids:
            return []
        return list(await model_cls.query().where_in(model_cls.primary_key, ids).get())

    async def _resolve_models(self, values: Any, model_class: Any = None) -> list[Any]:
        """Expand nested lists; resolve raw IDs via ``default_model`` / ``model_class``."""
        out: list[Any] = []
        pending_ids: list[Any] = []
        for item in _flatten_models(values):
            if _is_model_instance(item):
                out.append(item)
            else:
                pending_ids.append(item)
        if not pending_ids:
            return out
        cls = self._resolve_default_model_class(model_class)
        if cls is None:
            raise TypeError(
                "Pass model instances, or set permission.models.default_model / model_class"
            )
        for id_ in pending_ids:
            model = await cls.query().where(cls.primary_key, id_).first()
            if model is None:
                # Attach by id even if the row is missing (Spatie-style).
                out.append(_IdModel(cls, id_))
            else:
                out.append(model)
        return out

    def _resolve_default_model_class(self, model_class: Any = None) -> type | None:
        if model_class is not None:
            if isinstance(model_class, type):
                return model_class
            return import_string(str(model_class))
        path = permission_config("models.default_model")
        if path is None:
            return None
        if isinstance(path, type):
            return path
        return import_string(str(path))

    async def _attach_model(self, model: Any) -> None:
        from almasix.orm import QueryBuilder

        table = table_names().get("model_has_roles") or "model_has_roles"
        model_type = morph_alias(model.cls if isinstance(model, _IdModel) else type(model))
        row = {
            role_pivot_key(): self.get_key(),
            model_morph_key(): model.get_key(),
            "model_type": model_type,
        }
        if teams_enabled():
            row[team_foreign_key()] = get_permissions_team_id()
        await QueryBuilder.for_table(table).insert([row])

    async def _detach_model(self, model: Any) -> None:
        from almasix.orm import QueryBuilder

        model_type = morph_alias(model.cls if isinstance(model, _IdModel) else type(model))
        table = table_names().get("model_has_roles") or "model_has_roles"
        builder = (
            QueryBuilder.for_table(table)
            .where(role_pivot_key(), "=", self.get_key())
            .where(model_morph_key(), "=", model.get_key())
            .where("model_type", "=", model_type)
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


class _IdModel:
    """Stand-in when assigning by primary key without a loaded instance."""

    __slots__ = ("cls", "id")

    def __init__(self, cls: type, id_: Any) -> None:
        self.cls = cls
        self.id = id_

    def get_key(self) -> Any:
        return self.id


def _is_model_instance(value: Any) -> bool:
    return hasattr(value, "get_key") and not isinstance(value, (int, str, bytes))


def _flatten_models(values: Any) -> list[Any]:
    if values is None:
        return []
    if isinstance(values, (list, tuple, set)):
        out: list[Any] = []
        for item in values:
            out.extend(_flatten_models(item))
        return out
    return [values]
