# Changelog

## 0.2.0 — 2026-04-11

### dockerfile

- Configurable uv install method (`copy`, `curl`, `pip`) and version pinning
- Configurable Poetry install method (`curl`, `pip`, `pipx`) and version pinning
- `pipefail` option for stricter shell error handling
- `extra_instructions` blocks for injecting custom Dockerfile directives

### html_report

- `null-display` argument to control rendering of null/missing values
- `timestamp` argument for footer generation timestamp
- Handle heterogeneous rows (missing keys filled with null)

### poetry_migrate

- Bare version constraints converted to `==` pins
- `secondary` and `primary` source priority mapping
- Warning on unmigrated `packages` config
- Fix: `editable` path deps now emit `true` instead of the path

### download

- Detect filename from `Content-Disposition` header
- Fail on HTTP 4xx/5xx responses

### gh_latest

- Validate that the redirect URL points to a GitHub releases page
- Use `removeprefix` instead of `lstrip` for version parsing

### skylos_to_gitlab

- `min-confidence` filter argument
- Additional test cases (confidence filtering, dead files, empty reports)

### Other

- License updated to Apache 2.0
- Removed stale TODO.md

## 0.1.0 — 2026-03-29

Initial release.

### dockerfile

- Generate production Dockerfiles from JSON/YAML descriptors (Python + Node.js, multistage builds)

### html_report

- Convert JSON/CSV data to standalone HTML reports with sortable tables

### poetry_migrate

- Migrate Poetry pyproject.toml to Poetry 2 or uv (PEP 621)

### download

- Download files from URLs (wget-like, uses HTTP input format)

### gh_latest

- Get latest GitHub release tag or download URL

### skylos_to_gitlab

- Convert Skylos dead code reports to GitLab Code Quality format
