# Release notes — 0.3.0

> Source notes consumed by the release-workflow skill (Phase 2) to generate the
> `## 0.3.0` section of `CHANGELOG.md`. This file is expected to be deleted as
> part of the `chore(release): 0.3.0` commit.

## dockerfile

- **BREAKING**: `extra_instructions` restructured into `builder` / `runtime` stages with three hooks each (`before_install_pkgmgr`, `before_install_deps`, `finalize` for builder; `after_os_update`, `after_deps_install`, `finalize` for runtime). Old keys (`after_system`, `after_install`, `after_copy`) removed.
- New `builder_build_args` field: ARG declarations scoped to the builder stage (e.g. private-registry credentials).
- New `skip_copy_all` option: omit the runtime `COPY . .` for fully selective copy patterns.
- New `{cp: ...}` shorthand in hooks, auto-adds `--chown=user:user` when `user` is set.
- Refactored Jinja2 template: de-duplicated installer logic via `install_uv` / `install_poetry` macros.
- Updated `CONVERT_PROMPT.md` with hook placement rules, stage-normalization guidance, and private-registry recipes.

## poetry_migrate

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

## Other

- Fix over-quoted arg descriptions in `molds/catalog.toml`.
- Add `task test:all` to run fimod tests for every mold.
