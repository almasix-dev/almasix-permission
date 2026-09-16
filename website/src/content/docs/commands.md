---
title: Commands
description: Smith CLI for creating roles and permissions, assigning roles, showing the matrix, and resetting cache.
---

All commands use the `permission:` prefix.

| Command | Purpose |
| --- | --- |
| `permission:create-role {name} {guard?} {permissions?*} {--team-id=}` | Create a role; optionally grant permissions and set team |
| `permission:create-permission {name} {guard?}` | Create a permission |
| `permission:show {guard?} {style?}` | Print a roles × permissions table |
| `permission:assign-role {role} {model} {id} {guard?}` | Assign a role by model class path and id |
| `permission:cache-reset` | Flush the permission registrar cache |
| `permission:setup-teams` | Print the teams enable + migrate checklist |

## Examples

```bash title="terminal"
smith permission:create-permission "edit articles"
smith permission:create-role writer web "edit articles" "publish articles"
smith permission:create-role editor --team-id=42

smith permission:assign-role writer app.models.user.User 1
smith permission:show
smith permission:show web compact
smith permission:cache-reset
```

`permission:show` styles: `default`, `borderless`, `compact`, `box`. You can
pass style as the only argument (`show compact`) or after a guard
(`show web compact`).
