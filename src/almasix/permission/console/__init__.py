"""Smith commands for roles and permissions."""

from __future__ import annotations

from typing import Any

from almasix.console.command import Command
from almasix.permission.helpers import get_default_guard_name, get_permission_class, get_role_class
from almasix.permission.registrar import get_permission_registrar


def _run(coro: Any) -> Any:
    import asyncio

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    def _in_thread() -> Any:  # pragma: no cover
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()

    return _in_thread()


class CreateRoleCommand(Command):
    signature = "permission:create-role {name} {guard?} {permissions?*}"
    description = "Create a role (optionally with permissions)"

    def handle(self) -> int:
        name = str(self.argument("name"))
        guard = self.argument("guard") or get_default_guard_name()
        role_cls = get_role_class()
        role = _run(role_cls.find_or_create(name, str(guard)))
        permissions = self.argument("permissions") or []
        if isinstance(permissions, str):
            permissions = [permissions]
        if permissions:
            _run(role.give_permission_to(*permissions))
        self.success(f"role `{role.name}` ready (guard={role.guard_name})")
        return self.SUCCESS


class CreatePermissionCommand(Command):
    signature = "permission:create-permission {name} {guard?}"
    description = "Create a permission"

    def handle(self) -> int:
        name = str(self.argument("name"))
        guard = self.argument("guard") or get_default_guard_name()
        permission_cls = get_permission_class()
        permission = _run(permission_cls.find_or_create(name, str(guard)))
        self.success(f"permission `{permission.name}` ready (guard={permission.guard_name})")
        return self.SUCCESS


class ShowCommand(Command):
    signature = "permission:show {guard?} {style?}"
    description = "Show a table of roles and permissions"

    def handle(self) -> int:
        guard = self.argument("guard")
        role_cls = get_role_class()
        permission_cls = get_permission_class()
        roles = list(_run(role_cls.query().get()))
        permissions = list(_run(permission_cls.query().get()))
        if guard:
            roles = [r for r in roles if r.guard_name == guard]
            permissions = [p for p in permissions if p.guard_name == guard]
        self.info(f"Roles ({len(roles)}):")
        for role in roles:
            perms = list(_run(role.permissions().get()))
            names = ", ".join(p.name for p in perms) or "—"
            self.line(f"  [{role.guard_name}] {role.name} → {names}")
        self.info(f"Permissions ({len(permissions)}):")
        for permission in permissions:
            self.line(f"  [{permission.guard_name}] {permission.name}")
        return self.SUCCESS


class AssignRoleCommand(Command):
    signature = "permission:assign-role {role} {model} {id} {guard?}"
    description = "Assign a role to a model by class path and id"

    def handle(self) -> int:
        from almasix.permission.helpers import import_string

        role_name = str(self.argument("role"))
        model_path = str(self.argument("model"))
        model_id = self.argument("id")
        guard = self.argument("guard") or get_default_guard_name()
        role = _run(get_role_class().find_by_name(role_name, str(guard)))
        model_cls = import_string(model_path)
        model = _run(model_cls.query().where(model_cls.primary_key, model_id).first())
        if model is None:
            self.error(f"model {model_path}#{model_id} not found")
            return self.FAILURE
        _run(model.assign_role(role))
        self.success(f"assigned `{role_name}` to {model_path}#{model_id}")
        return self.SUCCESS


class CacheResetCommand(Command):
    signature = "permission:cache-reset"
    description = "Reset the permission cache"

    def handle(self) -> int:
        get_permission_registrar().forget_cached_permissions()
        self.success("permission cache flushed")
        return self.SUCCESS


class SetupTeamsCommand(Command):
    signature = "permission:setup-teams"
    description = "Remind to enable teams and publish the teams migration"

    def handle(self) -> int:
        self.info(
            "Set permission.teams = True in config, publish permission-migrations "
            "(upgrade_add_teams_fields), then run smith migrate."
        )
        return self.SUCCESS
