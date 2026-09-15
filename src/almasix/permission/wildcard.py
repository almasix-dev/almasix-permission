"""Wildcard permission matching."""

from __future__ import annotations

from typing import Any


class WildcardPermission:
    """Interpret permission names with ``.`` parts and ``*`` wildcards.

    Examples: ``posts.*``, ``*.edit``, ``posts.*.publish``.
    """

    part_delimiter = "."
    wildcard_token = "*"

    def __init__(self, permission: str, wildcard_permission: str | None = None) -> None:
        self.permission = str(permission)
        self.wildcard = str(wildcard_permission) if wildcard_permission is not None else None

    def implies(self, permission: str) -> bool:
        """Return True when ``self.permission`` (possibly wildcard) covers ``permission``."""
        return self._implies(self.permission, str(permission))

    def matches(self, owned: str) -> bool:
        """Return True when owned permission (wildcard or exact) covers this instance."""
        return self._implies(str(owned), self.permission)

    def _implies(self, pattern: str, candidate: str) -> bool:
        if pattern == candidate:
            return True
        if self.wildcard_token not in pattern:
            return False
        pattern_parts = pattern.split(self.part_delimiter)
        candidate_parts = candidate.split(self.part_delimiter)
        return self._match_parts(pattern_parts, candidate_parts)

    def _match_parts(self, pattern: list[str], candidate: list[str]) -> bool:
        if not pattern:
            return not candidate
        head, *tail = pattern
        if head == self.wildcard_token:
            # '*' matches one or more remaining segments when alone at end,
            # or exactly one segment otherwise (part wildcards).
            if not tail:
                return True
            for i in range(len(candidate) + 1):
                if self._match_parts(tail, candidate[i:]):
                    return True
            return False
        if not candidate or candidate[0] != head:
            return False
        return self._match_parts(tail, candidate[1:])


def wildcard_implies(owned: str, needed: str) -> bool:
    """Whether an owned permission name implies the needed ability."""
    from almasix.permission.helpers import import_string, permission_config

    path = permission_config(
        "wildcard_permission",
        "almasix.permission.wildcard.WildcardPermission",
    )
    cls: Any = import_string(str(path)) if isinstance(path, str) else path
    return bool(cls(owned).implies(needed) or cls(needed).matches(owned))
