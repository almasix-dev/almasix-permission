"""Permission package service provider."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from almasix.providers import ServiceProvider

_HERE = Path(__file__).resolve().parent


class PermissionServiceProvider(ServiceProvider):
    """Registers RBAC config, migrations, Gate.before, middleware, Prism, commands."""

    def register(self) -> None:
        self.merge_config_from(_HERE / "config" / "permission.py", "permission")
        self.app.container.singleton(
            "permission.registrar",
            lambda: __import__(
                "almasix.permission.registrar", fromlist=["get_permission_registrar"]
            ).get_permission_registrar(),
        )

    def boot(self) -> None:
        self.publishes(
            {_HERE / "config" / "permission.py": self.app.path("config", "permission.py")},
            "permission-config",
        )
        migrations = _HERE / "database" / "migrations"
        self.load_migrations_from(migrations)
        self.publishes_migrations(
            {
                migrations / "create_permission_tables.py": (
                    "database/migrations/create_permission_tables.py"
                ),
                migrations / "upgrade_add_teams_fields.py": (
                    "database/migrations/upgrade_add_teams_fields.py"
                ),
            },
            "permission-migrations",
        )
        self._register_middleware_aliases()
        self._register_gate()
        self._register_prism()
        from almasix.permission.console import (
            AssignRoleCommand,
            CacheResetCommand,
            CreatePermissionCommand,
            CreateRoleCommand,
            SetupTeamsCommand,
            ShowCommand,
        )

        self.commands(
            [
                CreateRoleCommand,
                CreatePermissionCommand,
                ShowCommand,
                AssignRoleCommand,
                CacheResetCommand,
                SetupTeamsCommand,
            ]
        )

    def _register_middleware_aliases(self) -> None:
        aliases = dict(self.app.config.get("http.middleware_aliases") or {})
        aliases.update(
            {
                "role": "almasix.permission.middleware.RoleMiddleware",
                "permission": "almasix.permission.middleware.PermissionMiddleware",
                "role_or_permission": "almasix.permission.middleware.RoleOrPermissionMiddleware",
            }
        )
        self.app.config.set("http.middleware_aliases", aliases)

    def _register_gate(self) -> None:
        from almasix.permission.helpers import permission_config

        if not permission_config("register_permission_check_method", True):
            return
        from almasix.auth.access.facade import Gate

        from almasix.permission.registrar import get_permission_registrar

        registrar = get_permission_registrar()

        def before(user: Any, ability: str, *arguments: Any) -> bool | None:
            if user is None or not hasattr(user, "check_permission_to"):
                return None
            guard = None
            if arguments and isinstance(arguments[0], str):
                guard = arguments[0]
            try:
                if user.check_permission_to(ability, guard):
                    return True
            except Exception:  # pragma: no cover
                return None
            return None

        Gate.before(before)
        _ = registrar

    def _register_prism(self) -> None:
        try:
            from almasix.prism.engine import Engine

            from almasix.permission.prism import register_prism_directives

            if self.app.container.bound(Engine):
                register_prism_directives(self.app.make(Engine))
        except Exception:  # pragma: no cover - Prism optional at boot
            pass
