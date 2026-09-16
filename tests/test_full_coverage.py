"""Drive remaining branches to 100% coverage (gate stays at 98)."""

from __future__ import annotations

from enum import Enum
from unittest.mock import patch

import pytest

from almasix.permission.console import ShowCommand, _run
from almasix.permission.middleware import _current_user
from almasix.permission.models.permission import Permission
from almasix.permission.models.role import Role
from almasix.permission.prism import register_prism_directives
from almasix.permission.teams import set_permissions_team_id
from almasix.permission.traits.has_permissions import _flatten
from tests.support import User, make_user


def test_show_completely_empty(migrated, app) -> None:
    cmd = ShowCommand()
    cmd.app = app
    cmd._arguments = {"guard": None, "style": None}
    cmd._options = {}
    assert cmd.handle() == 0


def test_show_roles_without_permissions(migrated, app) -> None:
    _run(Role.find_or_create("lonely", "web"))
    cmd = ShowCommand()
    cmd.app = app
    cmd._arguments = {"guard": "web", "style": "default"}
    cmd._options = {}
    assert cmd.handle() == 0


def test_current_user_prefers_auth_guard_user() -> None:
    class Req:
        user = object()

    guarded = object()

    class Guard:
        def user(self) -> object:
            return guarded

    class Auth:
        def guard(self, name: str) -> Guard:
            assert name == "api"
            return Guard()

    with patch("almasix.auth.guard.auth", return_value=Auth()):
        assert _current_user(Req(), "api") is guarded


def test_prism_without_composer() -> None:
    class Bare:
        def directive(self, *args: object, **kwargs: object) -> None:
            return None

    bare = Bare()
    assert not hasattr(bare, "composer")
    register_prism_directives(bare)


@pytest.mark.asyncio
async def test_default_model_as_type(migrated, app) -> None:
    app.config.set("permission.models.default_model", User)
    role = await Role.create(name="writer")
    user = await make_user()
    await role.assign_to_models(user.get_key())
    await user._load_role_names()
    assert user.has_role("writer")


@pytest.mark.asyncio
async def test_detach_model_without_teams(migrated) -> None:
    role = await Role.create(name="writer")

    class Bare:
        def get_key(self) -> int:
            return 55

    bare = Bare()
    await role.assign_to_models(bare)
    await role.remove_from_models(bare)


@pytest.mark.asyncio
async def test_detach_model_with_teams(memory_db, app) -> None:
    from tests.test_teams_coverage import _migrate_teams

    await _migrate_teams(app)
    set_permissions_team_id(1)
    role = await Role.create(name="writer")

    class Bare:
        def get_key(self) -> int:
            return 77

    bare = Bare()
    await role.assign_to_models(bare)
    await role.remove_from_models(bare)


@pytest.mark.asyncio
async def test_empty_revoke_and_remove(migrated) -> None:
    user = await make_user()
    await user.revoke_permission_to()
    await user.remove_role()


@pytest.mark.asyncio
async def test_check_permission_object_with_name(migrated) -> None:
    await Permission.create(name="edit articles")
    user = await make_user()
    await user.give_permission_to("edit articles")
    await user.get_all_permissions()

    class Named:
        name = "edit articles"

    assert user.check_permission_to(Named())


@pytest.mark.asyncio
async def test_has_any_permission_none_match(migrated) -> None:
    await Permission.create(name="a")
    user = await make_user()
    await user.get_all_permissions()
    assert not await user.has_any_permission("a", "b")


@pytest.mark.asyncio
async def test_permissions_via_roles_without_roles_attr(migrated) -> None:
    role = await Role.create(name="writer")
    assert await role.get_permissions_via_roles() == []


def test_flatten_helpers() -> None:
    assert _flatten(None) == []
    assert _flatten("a|b|c") == ["a", "b", "c"]
    assert _flatten(["x", ["y", "z"]]) == ["x", "y", "z"]


@pytest.mark.asyncio
async def test_check_permission_enum(migrated) -> None:
    class Perms(str, Enum):
        EDIT = "edit articles"

    await Permission.create(name="edit articles")
    user = await make_user()
    await user.give_permission_to(Perms.EDIT)
    await user.get_all_permissions()
    assert user.check_permission_to(Perms.EDIT)
