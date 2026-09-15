"""Core roles / permissions / Gate tests."""

from __future__ import annotations

from enum import Enum

import pytest
from almasix.auth.access.facade import Gate

from almasix.permission.exceptions import (
    GuardDoesNotMatch,
    PermissionAlreadyExists,
    PermissionDoesNotExist,
    RoleAlreadyExists,
    RoleDoesNotExist,
)
from almasix.permission.models.permission import Permission
from almasix.permission.models.role import Role
from almasix.permission.registrar import get_permission_registrar
from tests.support import User, make_user


class Perm(str, Enum):
    EDIT = "edit articles"
    DELETE = "delete articles"


class Roles(str, Enum):
    WRITER = "writer"
    ADMIN = "admin"


@pytest.mark.asyncio
async def test_create_assign_and_gate(migrated) -> None:
    await Permission.create(name="edit articles")
    await Permission.create(name="delete articles")
    role = await Role.create(name="writer")
    await role.give_permission_to("edit articles")

    user = await make_user()
    await user.assign_role("writer")
    await user.give_permission_to("delete articles")
    await user.get_all_permissions()  # warm cache for Gate

    assert await user.has_permission_to("edit articles")
    assert await user.has_permission_to("delete articles")
    assert await user.has_direct_permission("delete articles")
    assert not await user.has_direct_permission("edit articles")
    assert user.has_role("writer")
    assert user.can("edit articles")
    assert user.can("delete articles")
    assert not user.can("publish articles")


@pytest.mark.asyncio
async def test_enums_sync_and_revoke(migrated) -> None:
    await Permission.create(name=Perm.EDIT)
    await Permission.create(name=Perm.DELETE)
    role = await Role.find_or_create(Roles.WRITER)
    await role.sync_permissions(Perm.EDIT, Perm.DELETE)
    assert len(await role.permissions().get()) == 2
    await role.revoke_permission_to(Perm.DELETE)
    assert len(await role.permissions().get()) == 1

    user = await make_user()
    await user.sync_roles(Roles.WRITER)
    await user.get_all_permissions()
    assert user.has_role(Roles.WRITER)
    await user.remove_role(Roles.WRITER)
    user.forget_cached_roles()
    await user._load_role_names()
    assert not user.has_role(Roles.WRITER)


@pytest.mark.asyncio
async def test_duplicates_and_missing(migrated) -> None:
    await Permission.create(name="edit articles")
    with pytest.raises(PermissionAlreadyExists):
        await Permission.create(name="edit articles")
    with pytest.raises(PermissionDoesNotExist):
        await Permission.find_by_name("missing")

    await Role.create(name="writer")
    with pytest.raises(RoleAlreadyExists):
        await Role.create(name="writer")
    with pytest.raises(RoleDoesNotExist):
        await Role.find_by_name("missing")


@pytest.mark.asyncio
async def test_guard_mismatch(migrated) -> None:
    await Permission.create(name="edit articles", guard_name="api")
    user = await make_user()
    with pytest.raises(GuardDoesNotMatch):
        await user.give_permission_to(await Permission.find_by_name("edit articles", "api"))


@pytest.mark.asyncio
async def test_has_any_all_exact_roles(migrated) -> None:
    await Role.create(name="writer")
    await Role.create(name="editor")
    user = await make_user()
    await user.assign_role("writer", "editor")
    await user._load_role_names()
    assert user.has_any_role("writer", "admin")
    assert user.has_all_roles("writer", "editor")
    assert user.has_exact_roles("writer", "editor")
    assert not user.has_exact_roles("writer")


@pytest.mark.asyncio
async def test_find_or_create_and_cache_reset(migrated) -> None:
    p = await Permission.find_or_create("edit articles")
    p2 = await Permission.find_or_create("edit articles")
    assert p.get_key() == p2.get_key()
    registrar = get_permission_registrar()
    await registrar.get_permissions()
    registrar.forget_cached_permissions()
    assert registrar._permissions is None


@pytest.mark.asyncio
async def test_gate_before_returns_none_for_unknown(migrated) -> None:
    user = await make_user()
    await user.get_all_permissions()
    Gate.define("custom", lambda u: True)
    assert Gate.for_user(user).allows("custom")
    assert Gate.for_user(user).denies("totally-missing-ability")


@pytest.mark.asyncio
async def test_role_assign_to_models(migrated) -> None:
    role = await Role.create(name="writer")
    user = await make_user()
    await role.assign_to_models(user)
    await user._load_role_names()
    assert user.has_role("writer")
    await role.remove_from_models(user)
    user.forget_cached_roles()
    await user._load_role_names()
    assert not user.has_role("writer")


@pytest.mark.asyncio
async def test_scopes(migrated) -> None:
    await Role.create(name="writer")
    await Permission.create(name="edit articles")
    user = await make_user()
    other = await make_user(email="other@example.com", name="Other")
    await user.assign_role("writer")
    await user.give_permission_to("edit articles")

    writers = await User.query().role("writer").get()
    assert any(u.email == user.email for u in writers)
    without = await User.query().without_role("writer").get()
    assert any(u.email == other.email for u in without)
