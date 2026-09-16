---
title: Middleware and Prism
description: Protect routes with role/permission middleware and gate Prism sections with @role and @haspermission.
---

The provider registers middleware aliases `role`, `permission`, and
`role_or_permission`, plus Prism directives for templates.

## Middleware

Require any listed role or permission. Separate names with `|`; append
`,guard` for a non-default auth guard.

```python title="routes/web.py"
# role:admin|editor
# permission:edit articles
# role_or_permission:admin|edit articles
# optional guard: role:admin,api
```

| Alias | Passes when the user… |
| --- | --- |
| `role:` | Has any of the roles |
| `permission:` | Has any of the permissions (`check_permission_to`) |
| `role_or_permission:` | Has any listed role **or** permission |

Helpers for programmatic middleware strings:

```python title="examples/permission.py"
from almasix.permission.middleware import RoleMiddleware, PermissionMiddleware

RoleMiddleware.using("admin|editor")
RoleMiddleware.using("admin", guard="api")
PermissionMiddleware.using(["edit articles", "publish articles"])
```

Failures raise `UnauthorizedException` (HTTP response). Optionally surface
required names via `permission.display_role_in_exception` /
`display_permission_in_exception`.

## Prism directives

Templates can gate blocks on the authenticated user:

| Directive | Check |
| --- | --- |
| `@role` / `@hasrole` | `has_role` |
| `@hasanyrole` | `has_any_role` |
| `@hasallroles` | `has_all_roles` |
| `@hasexactroles` | `has_exact_roles` |
| `@unlessrole` | not `has_role` |
| `@haspermission` | `check_permission_to` |

Each has a matching `@end…` closer (`@endrole`, `@endhaspermission`, …).

```html title="resources/views/articles/show.prism.html"
@role('writer')
  <a href="…">Edit</a>
@endrole

@haspermission('delete articles')
  <form method="post">…</form>
@endhaspermission
```

Framework `@can` remains available for Gate abilities; see
[authorization](https://docs.almasix.com/authorization/).
