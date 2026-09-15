"""Close remaining coverage gaps."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from almasix.auth.access.facade import Gate
from almasix.http import ForbiddenHttpException

from almasix.permission.helpers import guard_name_for
from almasix.permission.middleware import (
    PermissionMiddleware,
    RoleMiddleware,
    RoleOrPermissionMiddleware,
    _unauthorized,
)
from tests.support import User


def test_helpers_class_guard_via_none_instance() -> None:
    class M:
        guard_name = "api"

    m = M()
    m.guard_name = None  # type: ignore[assignment]
    assert guard_name_for(m) == "api"


def test_middleware_using_lists_and_leak_flags() -> None:
    assert RoleMiddleware.using(["a", "b"]) == "role:a|b"
    assert PermissionMiddleware.using(["x", "y"]) == "permission:x|y"
    assert RoleOrPermissionMiddleware.using("solo") == "role_or_permission:solo"

    with patch(
        "almasix.permission.middleware.permission_config",
        side_effect=lambda k, d=None: k.startswith("display"),
    ):
        msg = str(_unauthorized(roles=["r"], permissions=["p"]))
        assert "roles" in msg and "permissions" in msg


@pytest.mark.asyncio
async def test_middleware_user_without_role_helpers() -> None:
    class Plain:
        pass

    class Req:
        user = Plain()

    async def ok(r: object) -> str:
        return "ok"

    with pytest.raises(ForbiddenHttpException):
        await RoleMiddleware("admin").handle(Req(), ok)
    with pytest.raises(ForbiddenHttpException):
        await RoleOrPermissionMiddleware("admin").handle(Req(), ok)


def test_gate_before_callback_edges(migrated) -> None:
    gate = Gate.get_gate()
    for cb in list(gate._before):
        assert cb(None, "x") is None
        assert cb(object(), "x") is None


def test_has_exact_roles_sync_load() -> None:
    user = User()
    user._role_name_cache = None

    async def fake_load(guard: str | None = None) -> set[str]:
        return {"writer"}

    user._load_role_names = fake_load  # type: ignore[method-assign]
    assert user.has_exact_roles("writer")


@pytest.mark.asyncio
async def test_empty_assign_and_scopes(migrated) -> None:
    from almasix.permission.models.permission import Permission
    from almasix.permission.models.role import Role
    from tests.support import make_user

    await Role.create(name="writer")
    await Permission.create(name="edit articles")
    user = await make_user()
    await user.assign_role()
    await user.give_permission_to()
    rows = await User.query().without_permission("edit articles").get()
    assert rows


def test_wildcard_no_match_after_star() -> None:
    from almasix.permission.wildcard import WildcardPermission

    assert not WildcardPermission("*.edit").implies("posts")


def test_create_role_without_permissions(migrated, app) -> None:
    from almasix.permission.console import CreateRoleCommand

    cmd = CreateRoleCommand()
    cmd.app = app
    cmd._arguments = {"name": "guest", "guard": "web", "permissions": []}
    cmd._options = {}
    assert cmd.handle() == 0


@pytest.mark.asyncio
async def test_gate_before_guard_argument(migrated) -> None:
    from almasix.permission.models.permission import Permission
    from tests.support import make_user

    await Permission.create(name="edit articles")
    user = await make_user()
    await user.give_permission_to("edit articles")
    await user.get_all_permissions()
    gate = Gate.get_gate()
    for cb in list(gate._before):
        assert cb(user, "edit articles", "web") is True
        assert cb(user, "missing", "web") is None


@pytest.mark.asyncio
async def test_resolve_role_from_object_with_name(migrated) -> None:
    from almasix.permission.models.role import Role
    from tests.support import make_user

    await Role.create(name="writer")
    user = await make_user()

    class Named:
        name = "writer"

    await user.assign_role(Named())
    await user._load_role_names()
    assert user.has_role("writer")


@pytest.mark.asyncio
async def test_permission_middleware_plain_user() -> None:
    class Plain:
        pass

    class Req:
        user = Plain()

    async def ok(r: object) -> str:
        return "ok"

    with pytest.raises(ForbiddenHttpException):
        await PermissionMiddleware("edit").handle(Req(), ok)


@pytest.mark.asyncio
async def test_role_or_permission_none_user() -> None:
    class Req:
        user = None

    async def ok(r: object) -> str:
        return "ok"

    with pytest.raises(ForbiddenHttpException):
        await RoleOrPermissionMiddleware("admin").handle(Req(), ok)


def test_show_with_explicit_guard(migrated, app) -> None:
    from almasix.permission.console import ShowCommand, _run
    from almasix.permission.models.permission import Permission
    from almasix.permission.models.role import Role

    _run(Permission.find_or_create("edit articles", "web"))
    _run(Role.find_or_create("writer", "web"))
    cmd = ShowCommand()
    cmd.app = app
    cmd._arguments = {"guard": "web", "style": None}
    cmd._options = {}
    assert cmd.handle() == 0
