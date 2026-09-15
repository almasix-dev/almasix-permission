"""Shared fixtures for almasix-permission tests."""

from __future__ import annotations

import importlib.util
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from almasix.auth.access.facade import Gate
from almasix.cache import Cache
from almasix.cache.manager import CacheManager
from almasix.config import set_repository
from almasix.framework.application import Application
from almasix.orm import DatabaseManager, Schema, set_manager

from almasix.permission.config.permission import config as permission_defaults
from almasix.permission.provider import PermissionServiceProvider
from almasix.permission.registrar import set_permission_registrar
from almasix.permission.teams import clear_permissions_team_id


@pytest.fixture(autouse=True)
def _reset_globals() -> Any:
    Gate.set_gate(None)
    set_permission_registrar(None)
    clear_permissions_team_id()
    yield
    Gate.set_gate(None)
    set_permission_registrar(None)
    clear_permissions_team_id()


@pytest.fixture
async def memory_db() -> AsyncIterator[DatabaseManager]:
    manager = DatabaseManager(
        {
            "default": "sqlite",
            "connections": {"sqlite": {"driver": "sqlite", "database": ":memory:"}},
        }
    )
    set_manager(manager)
    try:
        yield manager
    finally:
        await manager.disconnect()
        set_manager(None)


@pytest.fixture
def app(tmp_path: Path) -> Application:
    application = Application(tmp_path)
    repo = application.config
    set_repository(repo)
    repo.set("permission", dict(permission_defaults))
    repo.set(
        "auth",
        {"guards": {"web": {"driver": "session"}, "api": {"driver": "token"}}},
    )
    repo.set("http", {"middleware_aliases": {}})
    cache = CacheManager(
        app=application,
        config={"default": "array", "stores": {"array": {"driver": "array"}}},
    )
    Cache.set_manager(cache)
    return application


@pytest.fixture
async def migrated(memory_db: DatabaseManager, app: Application) -> Application:
    """Boot provider + create schema."""
    provider = PermissionServiceProvider(app)
    provider.register()
    provider.boot()

    mig_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "almasix"
        / "permission"
        / "database"
        / "migrations"
        / "create_permission_tables.py"
    )
    spec = importlib.util.spec_from_file_location("create_permission_tables", mig_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    await module.CreatePermissionTables().up()

    def users(table: Any) -> None:
        table.id()
        table.string("email")
        table.string("name").nullable()

    await Schema.create("users", users)
    return app
