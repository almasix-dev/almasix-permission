# Publishing almasix-permission

Trusted Publishing (OIDC) is configured in `.github/workflows/publish.yml`.
Before the first upload, register a **pending publisher** while logged in as the
PyPI owner:

1. Open https://pypi.org/manage/account/publishing/
2. Under **Pending publishers**, add:

| Field | Value |
|-------|-------|
| PyPI Project Name | `almasix-permission` |
| Owner | `almasix-dev` |
| Repository name | `almasix-permission` |
| Workflow name | `publish.yml` |
| Environment name | `pypi` |

3. Optionally add a TestPyPI pending publisher with Environment `testpypi`.
4. Cut a GitHub Release on a matching `vX.Y.Z` tag (must equal `project.version`
   in `pyproject.toml`).
