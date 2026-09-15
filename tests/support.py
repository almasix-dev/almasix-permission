"""Test user model and helpers."""

from __future__ import annotations

from almasix.auth import AuthenticatableMixin
from almasix.orm import Model

from almasix.permission.traits.has_roles import HasRoles


class User(HasRoles, AuthenticatableMixin, Model):
    table = "users"
    timestamps = False
    fillable = ("email", "name")
    guard_name = "web"


async def make_user(email: str = "ada@example.com", name: str = "Ada") -> User:
    return await User.create(email=email, name=name)
