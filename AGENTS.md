# AGENTS.md

Fimod-Powered is a registry of Python transformation scripts (molds) for Fimod,
executed in the embedded Monty runtime without system Python.

## Mold changes

- Keep `molds/<name>/<name>.py`, its README and `test-molds/<name>/` in sync.
- Export `transform(data, args, **_)`; declare `env` or `headers` when used.
  Keep `**_` to accept additional Fimod arguments such as `pipeline`.
- Monty provides Fimod built-ins without imports. Use `import re` for regex;
  new molds must run without `FIMOD_LEGACY_BUILTINS` and must not use deprecated
  `re_*`, `it_unique`, `it_unique_by` or `it_flatten` helpers. Preserve ordering
  and nested-value semantics when replacing deduplication or flattening.
- Use `msg_warn()` for non-fatal issues and `gk_fail()` for validation failures.
- After mold changes, regenerate `molds/catalog.toml` with
  `fimod registry build-catalog ./molds`.

## Verification commands

- One mold: `fimod mold test molds/<name>/<name>.py test-molds/<name>`.
- All fixtures: `task test:all`.
- HTTP molds also use local server tests (requires `uv`):
  `bash test-molds/download/test_e2e.sh` and
  `bash test-molds/gh_latest/test_e2e.sh`.

## Sources for the relevant task

- Mold layout, directives and fixtures: [CONTRIBUTING.md](CONTRIBUTING.md)
  and [authoring guide](docs-templates/authoring.md).
- Mold-specific behavior: the corresponding `molds/<name>/README.md`.
- Documentation: edit `docs-templates/` and mold READMEs; `docs/` and `site/`
  are generated. Build with `task docs:build`.
- Releases: use the local `release-workflow` or `prerelease-workflow` skill.
  Keep feature/fix release notes in `notes/release-vX.Y.Z.md`; update
  `CHANGELOG.md` only during a stable release.
