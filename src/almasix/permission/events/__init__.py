"""Permission assignment events (opt-in via ``permission.events_enabled``)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RoleAttachedEvent:
    model: Any
    roles: list[Any]
    team_id: Any | None = None


@dataclass
class RoleDetachedEvent:
    model: Any
    roles: list[Any]
    team_id: Any | None = None


@dataclass
class PermissionAttachedEvent:
    model: Any
    permissions: list[Any]
    team_id: Any | None = None


@dataclass
class PermissionDetachedEvent:
    model: Any
    permissions: list[Any]
    team_id: Any | None = None


def dispatch_event(event: Any) -> None:
    from almasix.permission.helpers import permission_config

    if not permission_config("events_enabled", False):
        return
    from almasix.events import Event

    Event.dispatch(event)
