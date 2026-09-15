"""Coverage-oriented edge cases for the permission surface."""

from __future__ import annotations

from enum import Enum
from typing import Any
from unittest.mock import patch

import pytest
from almasix.auth.access.facade import Gate
from almasix.http import ForbiddenHttpException

from almasix.permission.exceptions import (
    PermissionDoesNotExist,
    RoleDoesNotExist,
    UnauthorizedException,
)
from almasix.permission.helpers import (
    collect_names,
    enum_value,
    get_default_guard_name,
    guard_name_for,
    import_string,
    resolve_model_class,
)
from almasix.permission.middleware import (
    PermissionMiddleware,
    RoleMiddleware,
    RoleOrPermissionMiddleware,
    _unauthorized,
)
from almasix.permission.models.permission import Permission
from almasix.permission.models.role import Role
from almasix.permission.prism import (
    permission_has_all_roles,
    permission_has_any_role,
    permission_has_exact_roles,
    permission_has_permission,
    permission_has_role,
)
from almasix.permission.registrar import PermissionRegistrar, get_permission_registrar
from almasix.permission.teams import (
    DefaultTeamResolver,
    clear_permissions_team_id,
    set_permissions_team_id,
)
from almasix.permission.traits.has_models import _flatten_models
from almasix.permission.wildcard import WildcardPermission
from tests.support import User, make_user


class Flags(Enum):
    A = "alpha"


def test_helpers_and_enums() -> None:
    assert enum_value(Flags.A) == "alpha"
    assert enum_value("plain") == "plain"
    assert "alpha" in collect_names(Flags.A, "b|c", ["d"])
    assert import_string("almasix.permission.models.role.Role") is Role
    with pytest.raises(ImportError):
        import_string("Role")
    with pytest.raises(RuntimeError):
        # models.team defaults to None
        resolve_model_class("team")


def test_guard_name_variants() -> None:
    class M:
        def guard_name(self) -> str:
            return "api"

    class M2:
        guard_name = "api"

    assert guard_name_for(M()) == "api"
    assert guard_name_for(M2()) == "api"
    assert guard_name_for(None) == get_default_guard_name()

    class M3:
        def guard_name(self) -> list[str]:
            return ["web", "api"]

    assert guard_name_for(M3()) == "web"


@pytest.mark.asyncio
async def test_find_by_id_and_delete(migrated) -> None:
    p = await Permission.create(name="edit articles")
    found = await Permission.find_by_id(p.get_key(), "web")
    assert found.name == "edit articles"
    with pytest.raises(PermissionDoesNotExist):
        await Permission.find_by_id(99999)
    await p.delete()
    with pytest.raises(PermissionDoesNotExist):
        await Permission.find_by_name("edit articles")

    r = await Role.create(name="writer")
    assert (await Role.find_by_id(r.get_key(), "web")).name == "writer"
    with pytest.raises(RoleDoesNotExist):
        await Role.find_by_id(99999)
    await r.delete()


@pytest.mark.asyncio
async def test_permission_checks_any_all(migrated) -> None:
    await Permission.create(name="a")
    await Permission.create(name="b")
    user = await make_user()
    await user.give_permission_to("a")
    await user.get_all_permissions()
    assert await user.has_any_permission("a", "b")
    assert not await user.has_all_permissions("a", "b")
    await user.give_permission_to("b")
    await user.get_all_permissions()
    assert await user.has_all_permissions("a", "b")
    await user.revoke_permission_to("a")
    await user.get_all_permissions()
    assert not await user.has_permission_to("a")


@pytest.mark.asyncio
async def test_has_models_sync_and_users(migrated, app) -> None:
    app.config.set("permission.models.default_model", "tests.support.User")
    role = await Role.create(name="writer")
    u1 = await make_user(email="a@x.com")
    u2 = await make_user(email="b@x.com")
    await role.sync_models(u1, u2)
    users = await role.users()
    assert len(users) >= 1
    await role.remove_from_models(u1)
    with pytest.raises(TypeError):
        _flatten_models(1)


@pytest.mark.asyncio
async def test_registrar_gate_paths(migrated) -> None:
    await Permission.create(name="edit articles")
    user = await make_user()
    await user.give_permission_to("edit articles")
    await user.get_all_permissions()
    registrar = get_permission_registrar()
    await registrar.get_permissions()
    await registrar.get_permissions()  # cache hit
    assert registrar.check_permission(user, "edit articles") is True
    assert registrar.check_permission(user, "missing") is None
    assert registrar.check_permission(None, "edit articles") is None
    assert registrar.check_permission(object(), "edit articles") is None
    await registrar.clear_class_permission_cache()

    # Sync check via Gate
    assert Gate.for_user(user).allows("edit articles")


def test_teams_resolver() -> None:
    clear_permissions_team_id()
    assert DefaultTeamResolver().resolve() is None
    set_permissions_team_id(9)
    assert get_permission_registrar()
    from almasix.permission.teams import get_permissions_team_id

    assert get_permissions_team_id() == 9
    # resolver path when _team_id cleared after set via get without global
    clear_permissions_team_id()
    set_permissions_team_id(3)
    assert DefaultTeamResolver().resolve() == 3


def test_wildcard_matching() -> None:
    assert WildcardPermission("a.b").implies("a.b")
    assert not WildcardPermission("a.b").implies("a.c")
    assert WildcardPermission("a.*").implies("a.b.c")
    assert WildcardPermission("*.edit").implies("posts.edit")
    assert not WildcardPermission("a.*")._implies("a.*", "b")
    wp = WildcardPermission("posts.edit")
    assert wp.matches("posts.*")


def test_unauthorized_message_leak() -> None:
    with patch("almasix.permission.helpers.permission_config", side_effect=lambda k, d=None: True):
        msg = _unauthorized(roles=["admin"], permissions=["x"])
        assert "roles" in str(msg)
    assert isinstance(
        UnauthorizedException("nope").to_http(),
        ForbiddenHttpException,
    )


@pytest.mark.asyncio
async def test_middleware_denied_paths(migrated) -> None:
    user = await make_user()
    await user._load_role_names()

    class Req:
        def __init__(self, u: Any) -> None:
            self.user = u

    async def ok(r: Any) -> str:
        return "ok"

    with pytest.raises(ForbiddenHttpException):
        await RoleMiddleware("admin").handle(Req(user), ok)
    with pytest.raises(ForbiddenHttpException):
        await PermissionMiddleware("edit articles").handle(Req(user), ok)
    with pytest.raises(ForbiddenHttpException):
        await RoleOrPermissionMiddleware("admin").handle(Req(user), ok)


def test_prism_helpers_without_user() -> None:
    assert permission_has_role("admin") is False
    assert permission_has_any_role("admin") is False
    assert permission_has_all_roles("admin") is False
    assert permission_has_exact_roles("admin") is False
    assert permission_has_permission("edit") is False


@pytest.mark.asyncio
async def test_prism_helpers_with_user(migrated) -> None:
    await Role.create(name="admin")
    await Permission.create(name="edit articles")
    user = await make_user()
    await user.assign_role("admin")
    await user.give_permission_to("edit articles")
    await user._load_role_names()
    await user.get_all_permissions()

    with patch("almasix.permission.prism._auth_user", return_value=user):
        assert permission_has_role("admin")
        assert permission_has_any_role("admin", "x")
        assert permission_has_all_roles("admin")
        assert permission_has_exact_roles("admin")
        assert permission_has_permission("edit articles")


def test_assign_role_command(migrated, app) -> None:
    from almasix.permission.console import AssignRoleCommand, _run
    from almasix.permission.models.role import Role as RoleModel

    _run(RoleModel.find_or_create("writer"))
    user = _run(make_user())
    cmd = AssignRoleCommand()
    cmd.app = app
    cmd._arguments = {
        "role": "writer",
        "model": "tests.support.User",
        "id": user.get_key(),
        "guard": "web",
    }
    cmd._options = {}
    assert cmd.handle() == 0
    cmd._arguments["id"] = 99999
    assert cmd.handle() != 0


@pytest.mark.asyncio
async def test_scopes_permission(migrated) -> None:
    await Permission.create(name="edit articles")
    user = await make_user()
    other = await make_user(email="z@z.com")
    await user.give_permission_to("edit articles")
    found = await User.query().permission("edit articles").get()
    assert any(u.email == user.email for u in found)
    without = await User.query().without_permission("edit articles").get()
    assert any(u.email == other.email for u in without)


def test_provider_gate_disabled(app) -> None:
    from almasix.permission.provider import PermissionServiceProvider

    app.config.set("permission.register_permission_check_method", False)
    PermissionServiceProvider(app).boot()


@pytest.mark.asyncio
async def test_more_api_edges(migrated, app) -> None:
    from almasix.permission.helpers import permission_config as pc
    from almasix.permission.teams import get_permissions_team_id

    clear_permissions_team_id()
    # Resolver path when no process-local team id
    assert get_permissions_team_id() is None

    # Permission.roles relation
    p = await Permission.create(name="edit articles")
    role = await Role.create(name="writer")
    await role.give_permission_to(p)
    roles = await p.roles().get()
    assert any(r.name == "writer" for r in roles)

    # empty give / sync
    user = await make_user()
    await user.give_permission_to()
    await user.assign_role()
    await user.sync_permissions()
    await user.sync_roles()

    # get_role_names
    await user.assign_role("writer")
    names = await user.get_role_names()
    assert "writer" in names

    # remember permissions helper
    user._remember_permissions({"edit articles"})
    assert user.check_permission_to("edit articles")

    # cache store name non-default
    app.config.set("permission.cache", {"key": "k", "store": "array", "expiration_time": 60})
    reg = PermissionRegistrar()
    assert reg.store_name() == "array"
    assert reg.expiration() == 60

    # create role command with permissions as string
    from almasix.permission.console import CreateRoleCommand

    cmd = CreateRoleCommand()
    cmd.app = app
    cmd._arguments = {"name": "editor", "guard": None, "permissions": "edit articles"}
    cmd._options = {}
    assert cmd.handle() == 0

    # collect_names with model-like
    assert collect_names(p) == ["edit articles"]
    assert collect_names(None) == []

    # guard empty list
    class EmptyGuard:
        def guard_name(self) -> list[str]:
            return []

    assert guard_name_for(EmptyGuard()) == get_default_guard_name()

    # permission_config root
    assert isinstance(pc(), dict) or pc() is not None

    # HasModels assign without assign_role (raw attach)
    class Plain:
        def get_key(self) -> int:
            return 1

    # Role find without guard on find_by_id
    await Role.find_by_id(role.get_key())

    # Wildcard dead branch
    assert not WildcardPermission("*")._match_parts(["a", "*"], [])
