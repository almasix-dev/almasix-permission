"""Shared helpers: config, guards, enums, model resolution."""

from __future__ import annotations

import importlib
from enum import Enum
from typing import Any


def permission_config(key: str | None = None, default: Any = None) -> Any:
    """Read ``permission.*`` config (dot key optional)."""
    from almasix.config import config

    if key is None or key == "":
        return config("permission", default if default is not None else {})
    return config(f"permission.{key}", default)


def table_names() -> dict[str, str]:
    return dict(permission_config("table_names") or {})


def column_names() -> dict[str, Any]:
    return dict(permission_config("column_names") or {})


def role_pivot_key() -> str:
    return str(column_names().get("role_pivot_key") or "role_id")


def permission_pivot_key() -> str:
    return str(column_names().get("permission_pivot_key") or "permission_id")


def model_morph_key() -> str:
    return str(column_names().get("model_morph_key") or "model_id")


def team_foreign_key() -> str:
    return str(column_names().get("team_foreign_key") or "team_id")


def teams_enabled() -> bool:
    return bool(permission_config("teams", False))


def enum_value(value: Any) -> Any:
    """Coerce backed / str enums to their value."""
    if isinstance(value, Enum):
        return value.value
    return value


def normalize_name(value: Any) -> str:
    return str(enum_value(value))


def import_string(path: str) -> Any:
    module_path, _, name = path.rpartition(".")
    if not module_path:
        raise ImportError(f"Invalid import path: {path!r}")
    module = importlib.import_module(module_path)
    return getattr(module, name)


def resolve_model_class(config_key: str) -> type:
    path = permission_config(f"models.{config_key}")
    if path is None:
        raise RuntimeError(f"permission.models.{config_key} is not configured")
    if isinstance(path, type):
        return path
    return import_string(str(path))


def get_permission_class() -> type:
    return resolve_model_class("permission")


def get_role_class() -> type:
    return resolve_model_class("role")


def get_default_guard_name() -> str:
    """First defined auth guard, or ``web``."""
    try:
        from almasix.config import config

        guards = config("auth.guards") or {}
        if isinstance(guards, dict) and guards:
            return str(next(iter(guards.keys())))
    except Exception:
        pass
    return "web"


def guard_name_for(model: Any) -> str:
    """Resolve a model's guard (``guard_name`` attr / method, else default)."""
    if model is None:
        return get_default_guard_name()
    method = getattr(model, "guard_name", None)
    if callable(method):
        result = method()
        if isinstance(result, (list, tuple)):
            return str(result[0]) if result else get_default_guard_name()
        if result:
            return str(result)
    attr = getattr(model, "guard_name", None)
    if isinstance(attr, str) and attr and not callable(getattr(type(model), "guard_name", None)):
        return attr
    # Class-level guard_name string on the model class
    cls_guard = getattr(type(model), "guard_name", None)
    if isinstance(cls_guard, str):
        return cls_guard
    return get_default_guard_name()


def collect_names(*values: Any) -> list[str]:
    """Flatten role/permission arguments into a list of string names."""
    names: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            for item in value:
                names.extend(collect_names(item))
            continue
        # Model instance with .name
        name_attr = getattr(value, "name", None)
        if name_attr is not None and not isinstance(value, (str, Enum, int)):
            names.append(normalize_name(name_attr))
            continue
        text = normalize_name(value)
        if "|" in text:
            names.extend(part.strip() for part in text.split("|") if part.strip())
        else:
            names.append(text)
    return names
