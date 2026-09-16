"""Smith commands for roles and permissions."""

from __future__ import annotations

from typing import Any

from almasix.console.command import Command

from almasix.permission.helpers import (
    get_default_guard_name,
    get_permission_class,
    get_role_class,
    teams_enabled,
)
from almasix.permission.registrar import get_permission_registrar
from almasix.permission.teams import get_permissions_team_id, set_permissions_team_id

_SHOW_STYLES = frozenset({"default", "borderless", "compact", "box"})


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
    signature = "permission:create-role {name} {guard?} {permissions?*} {--team-id=}"
    description = "Create a role (optionally with permissions)"

    def handle(self) -> int:
        team_id = self.option("team-id")
        if team_id is not None and team_id != "" and not teams_enabled():
            self.warn(
                "Teams feature disabled, argument --team-id has no effect. "
                "Either enable it in permission config or remove --team-id."
            )
            return self.SUCCESS

        previous_team = get_permissions_team_id()
        if team_id is not None and team_id != "":
            set_permissions_team_id(team_id)

        try:
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
        finally:
            set_permissions_team_id(previous_team)


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
        guard, style = _resolve_show_args(self.argument("guard"), self.argument("style"))
        role_cls = get_role_class()
        permission_cls = get_permission_class()
        roles = list(_run(role_cls.query().get()))
        permissions = list(_run(permission_cls.query().get()))
        if guard:
            roles = [r for r in roles if r.guard_name == guard]
            permissions = [p for p in permissions if p.guard_name == guard]

        guards = sorted({*(r.guard_name for r in roles), *(p.guard_name for p in permissions)})
        if not guards and guard:
            guards = [str(guard)]
        if not guards:
            self.info("No roles or permissions.")
            return self.SUCCESS

        for guard_name in guards:
            self.info(f"Guard: {guard_name}")
            g_roles = [r for r in roles if r.guard_name == guard_name]
            g_perms = [p for p in permissions if p.guard_name == guard_name]
            role_names = [r.name for r in sorted(g_roles, key=lambda r: r.name)]
            perm_names = [p.name for p in sorted(g_perms, key=lambda p: p.name)]
            role_perm_ids: dict[str, set[Any]] = {}
            for role in g_roles:
                perms = list(_run(role.permissions().get()))
                role_perm_ids[role.name] = {p.get_key() for p in perms}
            perm_id_by_name = {p.name: p.get_key() for p in g_perms}
            rows: list[list[str]] = []
            for pname in perm_names:
                pid = perm_id_by_name[pname]
                cells = [pname]
                for rname in role_names:
                    cells.append(" ✔" if pid in role_perm_ids.get(rname, set()) else " ·")
                rows.append(cells)
            headers = [""] + role_names
            for line in _render_table(headers, rows, style):
                self.line(line)
            if not perm_names and role_names:
                self.line("  (no permissions)")
            elif not role_names and not perm_names:
                self.line("  (empty)")
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


def _resolve_show_args(guard: Any, style: Any) -> tuple[str | None, str]:
    """Accept ``show compact`` (style as first arg) or ``show web compact``."""
    g = str(guard).strip() if guard not in (None, "") else None
    s = str(style).strip() if style not in (None, "") else None
    if s is None and g is not None and g.lower() in _SHOW_STYLES:
        return None, g.lower()
    if s is not None and s.lower() in _SHOW_STYLES:
        return g, s.lower()
    if s is not None and g is None:
        # Unknown second token treated as style fallback to default
        return None, "default"
    return g, (s.lower() if s else "default")


def _render_table(headers: list[str], rows: list[list[str]], style: str) -> list[str]:
    cols = list(headers)
    width = len(cols)
    data = [cols, *rows]
    widths = [max(len(str(row[i])) for row in data) for i in range(width)] if data else []

    def pad(row: list[str]) -> list[str]:
        return [str(row[i]).ljust(widths[i]) for i in range(width)]

    if style == "borderless":
        return ["  ".join(pad(row)) for row in data]
    if style == "compact":
        lines = [" ".join(pad(cols))]
        lines.extend(" ".join(pad(row)) for row in rows)
        return lines

    h_line = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    if style == "box":
        h_line = "+" + "+".join("=" * (w + 2) for w in widths) + "+"

    def fmt(row: list[str]) -> str:
        return "| " + " | ".join(pad(row)) + " |"

    out = [h_line, fmt(cols), h_line]
    for row in rows:
        out.append(fmt(row))
    out.append(h_line)
    return out
