"""Role / Permission contracts."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Permission(Protocol):
    name: str
    guard_name: str

    @classmethod
    async def find_by_name(cls, name: str, guard_name: str | None = None) -> Any: ...

    @classmethod
    async def find_by_id(cls, id_: Any, guard_name: str | None = None) -> Any: ...

    @classmethod
    async def find_or_create(cls, name: str, guard_name: str | None = None) -> Any: ...


@runtime_checkable
class Role(Protocol):
    name: str
    guard_name: str

    @classmethod
    async def find_by_name(cls, name: str, guard_name: str | None = None) -> Any: ...

    @classmethod
    async def find_by_id(cls, id_: Any, guard_name: str | None = None) -> Any: ...

    @classmethod
    async def find_or_create(cls, name: str, guard_name: str | None = None) -> Any: ...
