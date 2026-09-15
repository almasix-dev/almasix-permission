"""Team context for scoped roles/permissions."""

from __future__ import annotations

from typing import Any

_team_id: Any | None = None


def set_permissions_team_id(team_id: Any) -> None:
    """Set the active team id for subsequent role/permission lookups."""
    global _team_id
    _team_id = team_id


def get_permissions_team_id() -> Any | None:
    """Return the active team id (or the configured resolver's value)."""
    global _team_id
    if _team_id is not None:
        return _team_id
    from almasix.permission.helpers import import_string, permission_config

    path = permission_config("team_resolver", "almasix.permission.teams.DefaultTeamResolver")
    resolver_cls = import_string(str(path)) if isinstance(path, str) else path
    resolver = resolver_cls() if isinstance(resolver_cls, type) else resolver_cls
    return resolver.resolve()


class DefaultTeamResolver:
    """Returns the process-local team id set via ``set_permissions_team_id``."""

    def resolve(self) -> Any | None:
        return _team_id


def clear_permissions_team_id() -> None:
    """Forget the process-local team id (tests / request teardown)."""
    global _team_id
    _team_id = None
