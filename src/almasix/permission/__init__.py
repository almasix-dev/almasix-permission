"""almasix-permission — roles and permissions for Almasix."""

from __future__ import annotations

from almasix.permission.helpers import enum_value
from almasix.permission.models.permission import Permission
from almasix.permission.models.role import Role
from almasix.permission.teams import (
    get_permissions_team_id,
    set_permissions_team_id,
)
from almasix.permission.traits.has_roles import HasRoles

__all__ = [
    "HasRoles",
    "Permission",
    "Role",
    "enum_value",
    "get_permissions_team_id",
    "set_permissions_team_id",
]

__version__ = "0.1.0"
