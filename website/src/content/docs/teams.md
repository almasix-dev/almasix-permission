---
title: Teams
description: Scope roles and permissions to a team with permission.teams and set_permissions_team_id.
---

Enable teams in published config **before** migrating:

```python title="config/permission.py"
# …
"teams": True,
# …
```

Then publish migrations (includes the teams upgrade) and migrate:

```bash title="terminal"
smith vendor:publish --tag=permission-migrations
smith migrate
# or: smith permission:setup-teams  # prints the same checklist
```

## Team context

Lookups and assignments use the active team id:

```python title="examples/permission.py"
from almasix.permission import set_permissions_team_id, get_permissions_team_id

set_permissions_team_id(team.id)
assert get_permissions_team_id() == team.id

await user.assign_role("writer")  # pivot includes team_id
role = await Role.find_by_name("writer")  # scoped to current team
```

Clear with `clear_permissions_team_id()` (tests / request teardown).

## Resolver

When no process-local id is set, `get_permissions_team_id` calls
`permission.team_resolver` (default `DefaultTeamResolver`, which returns the
value from `set_permissions_team_id`). Swap in a custom resolver for
request-scoped teams.

## CLI

`smith permission:create-role … --team-id=…` temporarily sets the team context
while creating the role. The flag is ignored (with a warning) when teams are
disabled.
