# Changelog

## 0.3.0 — 2026-04-18

### Highlights

- 🏗️ **Dockerfile hooks restructured** — explicit `builder` / `runtime` stages with 6 injection points, plus `{cp: ...}` shorthand.
- 📦 **Poetry → uv enriched** — PEP 508 markers, multi-constraints, URL / git deps, `index_strategy`, per-dep sources.
- 📖 **Release workflow documented** — `notes/release-workflow.md` captures the full cycle (phases, invariants, rc.N).

### dockerfile

- **BREAKING**: `extra_instructions` restructured into `builder` / `runtime` stages with three hooks each (`before_install_pkgmgr`, `before_install_deps`, `finalize` for builder; `after_os_update`, `after_deps_install`, `finalize` for runtime). Old keys (`after_system`, `after_install`, `after_copy`) removed.
- New `builder_build_args` field: ARG declarations scoped to the builder stage (e.g. private-registry credentials).
- New `skip_copy_all` option: omit the runtime `COPY . .` for fully selective copy patterns.
- New `{cp: ...}` shorthand in hooks, auto-adds `--chown=user:user` when `user` is set.
- Refactored Jinja2 template: de-duplicated installer logic via `install_uv` / `install_poetry` macros.
- Updated `CONVERT_PROMPT.md` with hook placement rules, stage-normalization guidance, and private-registry recipes.

### poetry_migrate

- New `index_strategy` argument for uv target — emits `[tool.uv] index-strategy`; warns when multiple indexes are declared without an explicit strategy.
- PEP 508 markers: `python`, `platform`, and raw `markers` fields are now converted on each dep.
- Multi-constraint deps (lists of dicts) expanded into multiple PEP 508 entries.
- URL deps (`{url = "..."}`) converted (`name @ url` for poetry2, `[tool.uv.sources]` for uv).
- Git deps: `subdirectory` and `develop` (editable) flags preserved.
- Per-dep `source = "name"` → `[tool.uv.sources] <dep> = { index = "name" }` for uv.
- Source priority normalized (`default`/`secondary`/`primary` → `priority`).
- `[tool.poetry]` keys without PEP 621 equivalent (`source`, `include`, `exclude`, `package-mode`) preserved for poetry2 target.
- `[tool.poetry.group.main.dependencies]` correctly merged into `[project.dependencies]`.
- Extras expand bare dep names to full PEP 508 strings.
- Python constraint simplified (`>=3.9.0` → `>=3.9`).
- Warnings on `allow-prereleases` and `package-mode = false` (uv target).
- New `MIGRATE_FULL_PROMPT.md` — workflow prompt for full project migrations (src-layout, Dockerfile, CI).

### Docs

- Add `notes/release-workflow.md` — reference documentation for the Fimod-Powered release cycle (phases, invariants, prerelease rc.N convention).

### Other

- Fix over-quoted arg descriptions in `molds/catalog.toml`.
- Add `task test:all` to run fimod tests for every mold.

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
