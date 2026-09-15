"""Teams, wildcards, events, middleware, Prism, commands."""

from __future__ import annotations

from pathlib import Path

import pytest

from almasix.events import Event
from almasix.http.request import Request
from almasix.prism.engine import Engine
from almasix.permission.console import (
    CacheResetCommand,
    CreatePermissionCommand,
    CreateRoleCommand,
    SetupTeamsCommand,
    ShowCommand,
)
from almasix.permission.events import PermissionAttachedEvent, RoleAttachedEvent
from almasix.permission.helpers import permission_config
from almasix.permission.middleware import (
    PermissionMiddleware,
    RoleMiddleware,
    RoleOrPermissionMiddleware,
)
from almasix.permission.models.permission import Permission
from almasix.permission.models.role import Role
from almasix.permission.prism import register_prism_directives
from almasix.permission.teams import get_permissions_team_id, set_permissions_team_id
from almasix.permission.wildcard import WildcardPermission, wildcard_implies
from tests.support import make_user


@pytest.mark.asyncio
async def test_teams_scope_roles(memory_db, app) -> None:
    app.config.set("permission.teams", True)
    provider = __import__("almasix.permission.provider", fromlist=["PermissionServiceProvider"]).PermissionServiceProvider
    provider(app).register()
    provider(app).boot()

    import importlib.util
    from pathlib import Path

    mig_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "almasix"
        / "permission"
        / "database"
        / "migrations"
        / "create_permission_tables.py"
    )
    spec = importlib.util.spec_from_file_location("create_permission_tables_teams", mig_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    await module.CreatePermissionTables().up()

    set_permissions_team_id(1)
    await Role.create(name="writer")
    set_permissions_team_id(2)
    await Role.create(name="writer")
    set_permissions_team_id(1)
    role = await Role.find_by_name("writer")
    assert getattr(role, "team_id", None) == 1
    assert get_permissions_team_id() == 1


@pytest.mark.asyncio
async def test_wildcard_permissions(migrated, app) -> None:
    app.config.set("permission.enable_wildcard_permission", True)
    await Permission.create(name="posts.*")
    user = await make_user()
    await user.give_permission_to("posts.*")
    await user.get_all_permissions()
    assert user.check_permission_to("posts.edit")
    assert user.check_permission_to("posts.delete")
    assert not user.check_permission_to("comments.edit")
    assert WildcardPermission("posts.*").implies("posts.edit")
    assert wildcard_implies("posts.*", "posts.publish")


@pytest.mark.asyncio
async def test_events_fire_when_enabled(migrated, app) -> None:
    app.config.set("permission.events_enabled", True)
    seen: list[object] = []

    def capture(event: object) -> None:
        seen.append(event)

    Event.listen(RoleAttachedEvent, capture)
    Event.listen(PermissionAttachedEvent, capture)
    await Permission.create(name="edit articles")
    await Role.create(name="writer")
    user = await make_user()
    await user.assign_role("writer")
    await user.give_permission_to("edit articles")
    assert any(isinstance(e, RoleAttachedEvent) for e in seen)
    assert any(isinstance(e, PermissionAttachedEvent) for e in seen)


@pytest.mark.asyncio
async def test_role_middleware(migrated) -> None:
    await Role.create(name="admin")
    user = await make_user()
    await user.assign_role("admin")
    await user._load_role_names()

    class Req:
        def __init__(self, user: object) -> None:
            self.user = user

    async def ok(request: object) -> str:
        return "ok"

    mw = RoleMiddleware("admin|editor")
    assert await mw.handle(Req(user), ok) == "ok"

    with pytest.raises(Exception):
        await mw.handle(Req(None), ok)

    assert RoleMiddleware.using(["admin", "editor"]) == "role:admin|editor"
    assert PermissionMiddleware.using("edit articles") == "permission:edit articles"
    assert RoleOrPermissionMiddleware.using(["admin"]) == "role_or_permission:admin"


@pytest.mark.asyncio
async def test_permission_and_combo_middleware(migrated) -> None:
    await Permission.create(name="edit articles")
    user = await make_user()
    await user.give_permission_to("edit articles")
    await user.get_all_permissions()

    class Req:
        def __init__(self, user: object) -> None:
            self.user = user

    async def ok(request: object) -> str:
        return "ok"

    assert await PermissionMiddleware("edit articles").handle(Req(user), ok) == "ok"
    assert await RoleOrPermissionMiddleware("edit articles").handle(Req(user), ok) == "ok"


def test_prism_directives(tmp_path: Path, migrated) -> None:
    views = tmp_path / "views"
    views.mkdir()
    (views / "page.prism.html").write_text(
        "@role('admin')SECRET@endrole@haspermission('edit articles')EDIT@endhaspermission",
        encoding="utf-8",
    )
    engine = Engine(paths=[views], cache_enabled=False)
    register_prism_directives(engine)
    # Without auth user → gates false → empty
    assert "SECRET" not in engine.render("page")


def test_commands_create_and_show(migrated, app) -> None:
    cmd = CreatePermissionCommand()
    cmd.app = app
    cmd._arguments = {"name": "edit articles", "guard": "web"}
    cmd._options = {}
    assert cmd.handle() == 0

    role_cmd = CreateRoleCommand()
    role_cmd.app = app
    role_cmd._arguments = {"name": "writer", "guard": "web", "permissions": ["edit articles"]}
    role_cmd._options = {}
    assert role_cmd.handle() == 0

    show = ShowCommand()
    show.app = app
    show._arguments = {}
    show._options = {}
    assert show.handle() == 0

    assert CacheResetCommand().handle() == 0
    assert SetupTeamsCommand().handle() == 0


def test_provider_publishes_and_aliases(app) -> None:
    from almasix.providers.provider import ServiceProvider
    from almasix.permission.provider import PermissionServiceProvider

    ServiceProvider.forget_publishes()
    provider = PermissionServiceProvider(app)
    provider.register()
    provider.boot()
    aliases = app.config.get("http.middleware_aliases") or {}
    assert aliases["role"].endswith("RoleMiddleware")
    assert permission_config("cache.key")


@pytest.mark.asyncio
async def test_sync_permissions_on_user(migrated) -> None:
    await Permission.create(name="a")
    await Permission.create(name="b")
    user = await make_user()
    await user.sync_permissions("a", "b")
    assert len(await user.get_direct_permissions()) == 2
    await user.sync_permissions("a")
    assert len(await user.get_direct_permissions()) == 1
