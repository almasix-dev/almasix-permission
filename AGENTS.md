# almasix-permission — agent memory

This repo is the **standalone** first-party RBAC package for Almasix.
Open **this** directory as the Cursor workspace for package work (not the
almasix monorepo).

## Locked decisions

- **Full Spatie Laravel Permission v8 feature parity** (not a stub). Do **not**
  brand docs/comments as “Spatie parity” — it is an Almasix package; Spatie was
  the design target only.
- **Not an Almasix milestone.** Never edit `docs/PLAN.md`, `docs/SMOKE.md`, or
  `examples/progress` for this package.
- **Own tests + coverage.** Gate is `make test-cov` with `fail_under = 98` on
  `almasix.permission` (aim higher). Core Almasix suite does not own this coverage.
- **Out of scope / N/A:** Passport Client Credentials Grant, Octane reset
  listener, PhpStorm/UI Options.

## Naming (current — Conduit style)

| Layer | Value |
| --- | --- |
| Local path | `/home/smaosa/Projects/almasix-permission` (renamed from `permission`) |
| GitHub | https://github.com/almasix-dev/almasix-permission |
| Dist / PyPI | `almasix-permission` |
| Import | `almasix.permission` (PEP 420 under `src/almasix/`; **no** `almasix/__init__.py`) |
| Provider entry | `permission = "almasix.permission.provider:PermissionServiceProvider"` |
| App config key | `permission.*` (merged as `"permission"`, not `almasix.permission.*`) |
| Framework extra | `almasix[permission]` → `almasix-permission>=0.1.0` |

**Do not** rewrite config lookups to `config("almasix.permission…")`. Helpers
must use `config("permission")` / `config(f"permission.{key}")`. Model class
paths in config **are** import strings like
`almasix.permission.models.role.Role`.

## Layout

```text
src/almasix/permission/
  provider.py
  config/permission.py
  contracts/
  models/                 # Permission, Role
  traits/                 # HasRoles, HasPermissions, HasModels
  middleware/
  exceptions/
  events/
  registrar.py            # cache + Gate ability registration
  teams.py
  wildcard.py
  helpers.py
  prism.py
  console/
  database/migrations/    # slug-only filenames (no timestamp prefixes)
tests/                    # package-owned suite
.github/workflows/        # ci.yml, publish.yml, publish-token.yml
```

Migrations ship **without** timestamp prefixes; Almasix stamps them on
`vendor:publish` / load order.

## Architecture

- User mixes `HasRoles` → assignment via morph pivots + registrar cache.
- `PermissionServiceProvider` registers `Gate.before` (when
  `register_permission_check_method`), middleware aliases
  (`role`, `permission`, `role_or_permission`), Prism directives, smith
  commands, config merge, migration publish/load.
- App auth surfaces stay Almasix: `user.can`, Gate, `@can`, `can` middleware.
  Policies remain for model-specific rules.

## Feature surface (maintain parity)

Schema (configurable tables/columns + optional teams), models, traits
(snake_case Spatie equivalents), query scopes, Gate.before, multi-guard,
teams (`set_permissions_team_id`), wildcards, enums, cache +
`permission:cache-reset`, events (opt-in), exceptions, middleware, Prism
(`@role`, `@haspermission`, …), smith commands
(create-role/permission, show, assign-role, cache-reset, setup-teams),
UUID/ULID via `permission.key_type` before migrate, extend via
`permission.models.*`.

## Workflows

- **CI:** ruff + pytest (--cov fail_under=98) on 3.11–3.13.
- **Release:** GitHub Release on `vX.Y.Z` matching `project.version`; OIDC
  publish (see `PUBLISHING.md`). Token fallback: `publish-token.yml`.
- **Not yet on PyPI** until first publish; monorepo CI falls back to
  `git+https://github.com/almasix-dev/almasix-permission.git@main`.

## Monorepo coupling (almasix)

Already wired (may be uncommitted in the framework repo):

- `pyproject.toml` extra `permission = ["almasix-permission>=0.1.0"]`
- `.github/workflows/ci.yml` installs permission with conduit/inertia
- In-tree `packages/permission` **removed** (courier stays as M29 demo)

Do not re-add an in-tree copy of this package under almasix.

## Commands

```bash
pip install -e ".[dev]"          # needs almasix>=0.9.0
make test
make test-cov                    # ≥98% on almasix.permission
make lint
```

## Success criteria (still true)

- Feature surface matches the Spatie v8 checklist minus N/A items.
- `make test-cov` passes ≥98%.
- Installable as `almasix.permission`; auto-discovered via entry point.
- Separate repo with CI/release; framework consumes via extra / PyPI / git.
