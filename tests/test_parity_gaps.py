"""Tests for remaining Spatie-surface gaps."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from almasix.http import ForbiddenHttpException

from almasix.permission.console import (
    CreateRoleCommand,
    ShowCommand,
    _render_table,
    _resolve_show_args,
)
from almasix.permission.middleware import (
    PermissionMiddleware,
    RoleMiddleware,
    RoleOrPermissionMiddleware,
    _parse_names_and_guard,
)
from almasix.permission.models.permission import Permission
from almasix.permission.models.role import Role
from almasix.permission.teams import set_permissions_team_id
from tests.support import make_user


def test_parse_names_and_guard() -> None:
    names, guard = _parse_names_and_guard("admin|editor,api")
    assert names == ["admin", "editor"]
    assert guard == "api"
    assert _parse_names_and_guard("solo") == (["solo"], None)
    assert _parse_names_and_guard("") == ([], None)


def test_middleware_using_with_guard() -> None:
    assert RoleMiddleware.using("admin", "api") == "role:admin,api"
    assert PermissionMiddleware.using(["a", "b"], "api") == "permission:a|b,api"
    assert RoleOrPermissionMiddleware.using("x", "web") == "role_or_permission:x,web"


@pytest.mark.asyncio
async def test_middleware_guard_filters_roles(migrated) -> None:
    await Role.create(name="admin", guard_name="web")
    user = await make_user()
    await user.assign_role("admin")
    await user._load_role_names()

    class Req:
        def __init__(self, user: object) -> None:
            self.user = user

    async def ok(request: object) -> str:
        return "ok"

    mw = RoleMiddleware("admin,web")
    assert mw.guard == "web"
    assert await mw.handle(Req(user), ok) == "ok"

    with pytest.raises(ForbiddenHttpException):
        await RoleMiddleware("admin,api").handle(Req(user), ok)


@pytest.mark.asyncio
async def test_permission_middleware_with_guard(migrated) -> None:
    await Permission.create(name="edit articles", guard_name="web")
    user = await make_user()
    await user.give_permission_to("edit articles")
    await user.get_all_permissions()

    class Req:
        def __init__(self, user: object) -> None:
            self.user = user

    async def ok(request: object) -> str:
        return "ok"

    assert await PermissionMiddleware("edit articles,web").handle(Req(user), ok) == "ok"
    assert await RoleOrPermissionMiddleware("edit articles,web").handle(Req(user), ok) == "ok"


@pytest.mark.asyncio
async def test_role_or_permission_middleware_role_path(migrated) -> None:
    await Role.create(name="admin")
    user = await make_user()
    await user.assign_role("admin")
    await user._load_role_names()

    class Req:
        def __init__(self, user: object) -> None:
            self.user = user

    async def ok(request: object) -> str:
        return "ok"

    assert await RoleOrPermissionMiddleware("admin,web").handle(Req(user), ok) == "ok"


@pytest.mark.asyncio
async def test_assign_to_models_by_id(migrated, app) -> None:
    app.config.set("permission.models.default_model", "tests.support.User")
    role = await Role.create(name="writer")
    user = await make_user()
    await role.assign_to_models(user.get_key())
    await user._load_role_names()
    assert user.has_role("writer")
    await role.remove_from_models(user.get_key())
    user.forget_cached_roles()
    await user._load_role_names()
    assert not user.has_role("writer")


@pytest.mark.asyncio
async def test_assign_to_models_by_id_requires_default(migrated, app) -> None:
    app.config.set("permission.models.default_model", None)
    role = await Role.create(name="writer")
    with pytest.raises(TypeError, match="default_model"):
        await role.assign_to_models(1)


@pytest.mark.asyncio
async def test_assign_to_models_explicit_model_class(migrated) -> None:
    from tests.support import User

    role = await Role.create(name="writer")
    user = await make_user()
    await role.assign_to_models(user.get_key(), model_class=User)
    await user._load_role_names()
    assert user.has_role("writer")
    await role.sync_models(user.get_key(), model_class="tests.support.User")
    await user._load_role_names()
    assert user.has_role("writer")


@pytest.mark.asyncio
async def test_assign_to_models_missing_id_still_attaches(migrated, app) -> None:
    app.config.set("permission.models.default_model", "tests.support.User")
    role = await Role.create(name="ghost")
    await role.assign_to_models(99999)
    users = await role.users()
    assert users == []


def test_create_role_team_id_disabled_warns(migrated, app) -> None:
    cmd = CreateRoleCommand()
    cmd.app = app
    cmd._arguments = {"name": "writer", "guard": "web", "permissions": []}
    cmd._options = {"team-id": "1"}
    with patch.object(cmd, "warn") as warn:
        assert cmd.handle() == 0
        warn.assert_called_once()


def test_create_role_with_team_id(memory_db, app) -> None:
    from almasix.permission.console import _run
    from tests.test_teams_coverage import _migrate_teams

    _run(_migrate_teams(app))

    cmd = CreateRoleCommand()
    cmd.app = app
    cmd._arguments = {"name": "writer", "guard": "web", "permissions": []}
    cmd._options = {"team-id": "7"}
    assert cmd.handle() == 0
    set_permissions_team_id(7)
    role = _run(Role.find_by_name("writer", "web"))
    assert getattr(role, "team_id", None) == 7


def test_resolve_show_args() -> None:
    assert _resolve_show_args("compact", None) == (None, "compact")
    assert _resolve_show_args("web", "box") == ("web", "box")
    assert _resolve_show_args(None, None) == (None, "default")
    assert _resolve_show_args("web", None) == ("web", "default")
    assert _resolve_show_args(None, "weird") == (None, "default")


def test_render_table_styles() -> None:
    headers = ["", "admin"]
    rows = [["edit", " ✔"]]
    default = _render_table(headers, rows, "default")
    assert any("+" in line for line in default)
    assert any("admin" in line for line in default)
    compact = _render_table(headers, rows, "compact")
    assert not any(line.startswith("+") for line in compact)
    borderless = _render_table(headers, rows, "borderless")
    assert "admin" in borderless[0]
    boxed = _render_table(headers, rows, "box")
    assert any("=" in line for line in boxed)


def test_show_matrix_styles(migrated, app) -> None:
    from almasix.permission.console import _run

    _run(Permission.find_or_create("edit articles", "web"))
    _run(Role.find_or_create("writer", "web"))
    role = _run(Role.find_by_name("writer", "web"))
    _run(role.give_permission_to("edit articles"))

    for style in ("default", "compact", "borderless", "box"):
        cmd = ShowCommand()
        cmd.app = app
        cmd._arguments = {"guard": "web", "style": style}
        cmd._options = {}
        assert cmd.handle() == 0

    cmd = ShowCommand()
    cmd.app = app
    cmd._arguments = {"guard": "compact", "style": None}
    cmd._options = {}
    assert cmd.handle() == 0

    empty = ShowCommand()
    empty.app = app
    empty._arguments = {"guard": "missing-guard", "style": "default"}
    empty._options = {}
    assert empty.handle() == 0
