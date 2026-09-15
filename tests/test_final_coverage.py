"""Final coverage push."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from almasix.prism.engine import Engine
from almasix.permission.helpers import (
    get_default_guard_name,
    guard_name_for,
    resolve_model_class,
)
from almasix.permission.models.permission import Permission
from almasix.permission.models.role import Role
from almasix.permission.provider import PermissionServiceProvider
from almasix.permission.registrar import PermissionRegistrar
from almasix.permission.wildcard import WildcardPermission
from tests.support import User, make_user


def test_resolve_model_class_accepts_type(app) -> None:
    app.config.set("permission.models.permission", Permission)
    assert resolve_model_class("permission") is Permission


def test_default_guard_when_config_raises(app) -> None:
    with patch("almasix.config.config", side_effect=RuntimeError("boom")):
        assert get_default_guard_name() == "web"


def test_guard_name_falsy_method() -> None:
    class M:
        def guard_name(self) -> str:
            return ""

    assert guard_name_for(M()) == get_default_guard_name()


def test_provider_registers_prism_when_engine_bound(app, tmp_path: Path) -> None:
    views = tmp_path / "views"
    views.mkdir()
    engine = Engine(paths=[views], cache_enabled=False)
    app.container.instance(Engine, engine)
    PermissionServiceProvider(app).boot()
    assert "role" in engine._directives


@pytest.mark.asyncio
async def test_registrar_reads_cache_store(migrated) -> None:
    await Permission.create(name="edit articles")
    reg = PermissionRegistrar()
    await reg.get_permissions()
    reg._permissions = None
    # Second call should hit cache store
    again = await reg.get_permissions()
    assert again


@pytest.mark.asyncio
async def test_role_find_by_id_teams(memory_db, app) -> None:
    from tests.test_teams_coverage import _migrate_teams
    from almasix.permission.teams import set_permissions_team_id

    await _migrate_teams(app)
    set_permissions_team_id(1)
    role = await Role.create(name="writer")
    found = await Role.find_by_id(role.get_key(), "web")
    assert found.name == "writer"


@pytest.mark.asyncio
async def test_users_wrong_morph_returns_empty(migrated, app) -> None:
    app.config.set("permission.models.default_model", "tests.support.User")
    role = await Role.create(name="writer")
    # Attach a bare model morph type that won't match User
    class Bare:
        def get_key(self) -> int:
            return 99

    await role._attach_model(Bare())
    assert await role.users() == []


def test_wildcard_star_exhaust() -> None:
    assert WildcardPermission("a.*")._match_parts(["*"], ["x", "y"])
    assert not WildcardPermission("a")._match_parts(["a", "b"], ["a"])


@pytest.mark.asyncio
async def test_check_permission_enum_and_wildcard(migrated, app) -> None:
    from enum import Enum

    class P(str, Enum):
        EDIT = "edit articles"

    app.config.set("permission.enable_wildcard_permission", True)
    await Permission.create(name="posts.*")
    user = await make_user()
    await user.give_permission_to("posts.*")
    await user.get_all_permissions()
    assert user.check_permission_to("posts.edit")
    await Permission.create(name="edit articles")
    await user.give_permission_to("edit articles")
    await user.get_all_permissions()
    assert user.check_permission_to(P.EDIT)


@pytest.mark.asyncio
async def test_gate_before_none_user(migrated) -> None:
    from almasix.auth.access.facade import Gate

    assert Gate.for_user(None).denies("edit articles")


@pytest.mark.asyncio
async def test_role_guard_mismatch(migrated) -> None:
    from almasix.permission.exceptions import GuardDoesNotMatch

    await Role.create(name="writer", guard_name="api")
    user = await make_user()
    with pytest.raises(GuardDoesNotMatch):
        await user.assign_role(await Role.find_by_name("writer", "api"))
