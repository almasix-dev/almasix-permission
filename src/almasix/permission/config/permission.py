"""Default permission package configuration."""

from __future__ import annotations

config = {
    "models": {
        "permission": "almasix.permission.models.permission.Permission",
        "role": "almasix.permission.models.role.Role",
        "team": None,
        "default_model": None,
    },
    "table_names": {
        "roles": "roles",
        "permissions": "permissions",
        "model_has_permissions": "model_has_permissions",
        "model_has_roles": "model_has_roles",
        "role_has_permissions": "role_has_permissions",
    },
    "column_names": {
        "role_pivot_key": None,  # default role_id
        "permission_pivot_key": None,  # default permission_id
        "model_morph_key": "model_id",
        "team_foreign_key": "team_id",
    },
    "register_permission_check_method": True,
    "events_enabled": False,
    "teams": False,
    "team_resolver": "almasix.permission.teams.DefaultTeamResolver",
    "use_passport_client_credentials": False,  # N/A — no Passport equivalent
    "display_permission_in_exception": False,
    "display_role_in_exception": False,
    "enable_wildcard_permission": False,
    "wildcard_permission": "almasix.permission.wildcard.WildcardPermission",
    # Primary key type for published migrations: "int" | "uuid" | "ulid"
    "key_type": "int",
    "cache": {
        "expiration_time": 24 * 60 * 60,  # seconds
        "key": "almasix.permission.cache",
        "store": "default",
    },
}
