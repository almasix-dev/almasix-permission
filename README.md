# almasix-permission

Roles and permissions for [Almasix](https://github.com/almasix-dev/almasix).

Install as `almasix.permission`:

```bash
pip install almasix-permission
# or from the framework extras:
pip install "almasix[permission]"
```

```python
from almasix.permission import HasRoles, Permission, Role
```

## Install (editable)

```bash
pip install -e ".[dev]"
smith vendor:publish --tag=permission-config
smith vendor:publish --tag=permission-migrations
# Enable teams / UUID *before* migrating if you need them
smith migrate
```

Mix `HasRoles` onto your user model:

```python
from almasix.auth import AuthenticatableMixin
from almasix.orm import Model
from almasix.permission import HasRoles

class User(HasRoles, AuthenticatableMixin, Model):
    fillable = ("email", "name", "password")
```

## Quick usage

```python
from almasix.permission import Permission, Role

await Permission.create(name="edit articles")
await Role.create(name="writer")
role = await Role.find_by_name("writer")
await role.give_permission_to("edit articles")

await user.assign_role("writer")
await user.give_permission_to("delete articles")

assert await user.has_permission_to("edit articles")
assert user.can("edit articles")  # via Gate.before
```

## API surface

| Area | Methods / tools |
| --- | --- |
| Permissions | `give_permission_to`, `revoke_permission_to`, `sync_permissions`, `has_permission_to`, `check_permission_to`, `has_direct_permission`, `get_all_permissions` |
| Roles | `assign_role`, `remove_role`, `sync_roles`, `has_role`, `has_any_role`, `has_all_roles`, `has_exact_roles` |
| Teams | `set_permissions_team_id` / `get_permissions_team_id` |
| Prism | `@role`, `@hasrole`, `@haspermission`, … |
| Middleware | `role:`, `permission:`, `role_or_permission:` |
| Commands | `smith permission:create-role`, `create-permission`, `show`, `assign-role`, `cache-reset`, `setup-teams` |

## Features

- Roles and permissions (direct or via roles), polymorphic assignment
- `Gate.before` so `user.can(…)`, `@can`, and `can` middleware work
- Multi-guard namespacing
- Teams (`permission.teams` + `set_permissions_team_id`)
- Wildcard permissions (`permission.enable_wildcard_permission`)
- Enum names (`enum.Enum` / `StrEnum`)
- Cache + `permission:cache-reset`
- Opt-in events (`permission.events_enabled`)
- UUID/ULID via `permission.key_type` before migrate
- Extending models through `permission.models.*`

## Tests

```bash
make test
make test-cov   # fail_under=98 on almasix.permission
```

## Discovery

```toml
[project.entry-points."almasix.providers"]
permission = "almasix.permission.provider:PermissionServiceProvider"
```

Or list the provider explicitly in `config/app.py`.
