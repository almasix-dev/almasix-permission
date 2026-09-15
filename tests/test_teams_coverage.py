"""Extra coverage for teams branches and HasModels attach paths."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest
from almasix.orm import Schema

from almasix.permission.models.permission import Permission
from almasix.permission.models.role import Role
from almasix.permission.provider import PermissionServiceProvider
from almasix.permission.teams import set_permissions_team_id
from almasix.permission.traits.has_models import _flatten_models
from tests.support import make_user


async def _migrate_teams(app: Any) -> None:
    app.config.set("permission.teams", True)
    PermissionServiceProvider(app).register()
    PermissionServiceProvider(app).boot()
    mig_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "almasix"
        / "permission"
        / "database"
        / "migrations"
        / "create_permission_tables.py"
    )
    spec = importlib.util.spec_from_file_location("perm_teams_mig", mig_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    await module.CreatePermissionTables().up()

    def users(table: Any) -> None:
        table.id()
        table.string("email")
        table.string("name").nullable()

    await Schema.create("users", users)


@pytest.mark.asyncio
async def test_teams_assign_permissions_and_roles(memory_db, app) -> None:
    await _migrate_teams(app)
    set_permissions_team_id(1)
    await Permission.create(name="edit articles")
    role = await Role.create(name="writer")
    await role.give_permission_to("edit articles")

    user = await make_user()
    await user.assign_role("writer")
    await user.give_permission_to("edit articles")
    await user.sync_roles("writer")
    await user.sync_permissions("edit articles")
    await user._load_role_names()
    await user.get_all_permissions()
    assert user.has_role("writer")
    assert user.check_permission_to("edit articles")

    # HasModels without assign_role / remove_role
    class Bare:
        def get_key(self) -> int:
            return 42

    await role.assign_to_models(Bare())
    await role.remove_from_models(Bare())
    await role.sync_models(Bare())

    assert _flatten_models(None) == []
    assert _flatten_models([Bare()])  # nested list


@pytest.mark.asyncio
async def test_users_empty_without_default_model(memory_db, app) -> None:
    await _migrate_teams(app)
    set_permissions_team_id(1)
    role = await Role.create(name="writer")
    assert await role.users() == []


@pytest.mark.asyncio
async def test_middleware_permission_warm_cache_false_path(migrated) -> None:
    from almasix.http import ForbiddenHttpException

    from almasix.permission.middleware import PermissionMiddleware

    user = await make_user()
    # warm empty cache
    user._permission_name_cache = set()

    class Req:
        def __init__(self) -> None:
            self.user = user

    async def ok(r: Any) -> str:
        return "ok"

    with pytest.raises(ForbiddenHttpException):
        await PermissionMiddleware("nope").handle(Req(), ok)


def test_helpers_class_guard_and_config_root(app) -> None:
    from almasix.permission.helpers import (
        get_default_guard_name,
        guard_name_for,
        permission_config,
    )

    class OnlyClassGuard:
        pass

    OnlyClassGuard.guard_name = "api"
    assert guard_name_for(OnlyClassGuard()) == "api"

    # No auth.guards → web
    app.config.set("auth", {})
    assert get_default_guard_name() == "web"
    assert permission_config("") is not None or permission_config() is not None
