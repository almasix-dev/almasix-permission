---
title: Installation
description: Install almasix-permission, publish config and migrations, and mix HasRoles onto your user.
---

```bash title="terminal"
pip install almasix-permission
# or
pip install "almasix[permission]"
```

For local package work:

```bash title="terminal"
pip install -e ".[dev]"
smith vendor:publish --tag=permission-config
smith vendor:publish --tag=permission-migrations
# Enable teams / UUID *before* migrating if you need them
smith migrate
```

Set `permission.teams` or `permission.key_type` (`int` | `uuid` | `ulid`) in
config **before** the first migrate when you need those options.

## User model

Mix `HasRoles` onto your authenticatable model:

```python title="app/models/user.py"
from almasix.auth import AuthenticatableMixin
from almasix.orm import Model
from almasix.permission import HasRoles

class User(HasRoles, AuthenticatableMixin, Model):
    fillable = ("email", "name", "password")
```

## Provider

The package advertises itself via the `almasix.providers` entry-point group:

```toml
[project.entry-points."almasix.providers"]
permission = "almasix.permission.provider:PermissionServiceProvider"
```

Or list the provider explicitly in `config/app.py`. Config merges under
`permission.*` (not `almasix.permission.*`).

Published on [PyPI](https://pypi.org/project/almasix-permission/) from
[`almasix-dev/almasix-permission`](https://github.com/almasix-dev/almasix-permission).
