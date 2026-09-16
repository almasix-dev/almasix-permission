---
title: Roles
description: Create roles, assign them with HasRoles, and check role membership.
---

`HasRoles` (which includes `HasPermissions`) is the mixin for authenticatable
models. Roles are named groups of permissions, optionally scoped by guard and
team.

## Create and find

```python title="examples/permission.py"
from almasix.permission import Role

await Role.create(name="writer")
role = await Role.find_by_name("writer")
await role.give_permission_to("edit articles")
```

`Role.find_or_create(name, guard_name=None)` creates when missing.
`Role.find_by_id` looks up by primary key.

## Assign on a model

```python title="examples/permission.py"
await user.assign_role("writer")
await user.assign_role("editor", "publisher")
await user.remove_role("writer")
await user.sync_roles("editor")  # replace all roles for the current team/guard
```

Names, enums (`Enum` / `StrEnum`), ids, and `Role` instances are accepted.

## Checks

| Method | Meaning |
| --- | --- |
| `has_role(role, guard=None)` | Any of the given role names |
| `has_any_role(*roles)` | At least one |
| `has_all_roles(*roles)` | Every listed role |
| `has_exact_roles(*roles)` | Exactly that set (no extras) |
| `get_role_names()` | Sorted list of current role names |

```python title="examples/permission.py"
assert user.has_role("writer")
assert user.has_any_role("writer", "admin")
assert user.has_all_roles("writer", "editor")
```

## Query scopes

```python title="examples/permission.py"
await User.query().role("writer").get()
await User.query().without_role("banned").get()
```

Guards must match the model's default guard; mismatched roles raise
`GuardDoesNotMatch`.
