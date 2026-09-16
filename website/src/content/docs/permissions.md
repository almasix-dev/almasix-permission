---
title: Permissions
description: Create permissions, grant them directly or via roles, and check with has_permission_to and can.
---

Permissions can be assigned **directly** on a model or **via roles**. Direct
and role-derived abilities both feed `has_permission_to` and, when
`register_permission_check_method` is enabled (default), `user.can(…)`.

## Create and grant

```python title="examples/permission.py"
from almasix.permission import Permission, Role

await Permission.create(name="edit articles")
await Permission.create(name="delete articles")

role = await Role.find_by_name("writer")
await role.give_permission_to("edit articles")

await user.assign_role("writer")
await user.give_permission_to("delete articles")  # direct
```

## API on HasPermissions / HasRoles

| Method | Meaning |
| --- | --- |
| `give_permission_to(*permissions)` | Attach permissions |
| `revoke_permission_to(*permissions)` | Detach permissions |
| `sync_permissions(*permissions)` | Replace the set |
| `has_permission_to(permission, guard=None)` | Async check (direct or via roles) |
| `check_permission_to(permission, guard=None)` | Sync check (used by middleware) |
| `has_direct_permission(permission)` | Direct only |
| `has_any_permission` / `has_all_permissions` | Multiple names |
| `get_all_permissions()` | Direct ∪ via roles |
| `get_direct_permissions()` / `get_permissions_via_roles()` | Split views |

```python title="examples/permission.py"
assert await user.has_permission_to("edit articles")  # via role
assert await user.has_permission_to("delete articles")  # direct
assert user.can("edit articles")  # Gate.before
```

## Query scopes

```python title="examples/permission.py"
await User.query().permission("edit articles").get()
await User.query().without_permission("delete articles").get()
```

## Gate integration

With `permission.register_permission_check_method` true, the provider registers
`Gate.before` so framework `can` checks, `@can`, and `can` middleware resolve
permission names. Model-specific rules still belong in
[Policies](https://docs.almasix.com/authorization/).

## Optional features

- **Wildcards** — `permission.enable_wildcard_permission`
- **Enums** — pass `Enum` / `StrEnum` members as names
- **Cache** — registrar cache; flush with `smith permission:cache-reset`
- **Events** — opt in with `permission.events_enabled`
- **Custom models** — `permission.models.permission` / `permission.models.role`
