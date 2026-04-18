# Poetry Migrate

Migrate a Poetry `pyproject.toml` to **Poetry 2** or **uv** format, with full PEP 621 compliance.

```bash
# Poetry 1 → Poetry 2 (default)
fimod s -i pyproject.toml -m @poetry_migrate -o pyproject.toml -i

# Poetry → uv (hatchling backend)
fimod s -i pyproject.toml -m @poetry_migrate --arg target=uv -o pyproject.toml -i

# Poetry → uv (setuptools backend)
fimod s -i pyproject.toml -m @poetry_migrate --arg target=uv --arg build=setuptools -o pyproject.toml -i

# Poetry → uv, preserving Poetry's "search every index" semantics
fimod s -i pyproject.toml -m @poetry_migrate --arg target=uv --arg index_strategy=unsafe-best-match -o pyproject.toml -i
```

## Why This Mold?

There is no built-in migration command in Poetry, uv, or pip. Existing third-party tools (`pdm import`, `migrate-to-uv`) are either targeting a different ecosystem or handle only basic cases. None of them convert plugins, offer build backend choice, or support dual targets.

This mold does:

- **Dual target** — Poetry 2 and uv from the same tool
- **Plugins → entry-points** — no other migration tool does this
- **5 build backends** — hatchling, setuptools, flit, pdm, uv-build
- **Git + path deps** with full ref support (branch/tag/rev, editable)
- **Sources** — preserved as `[[tool.poetry.source]]` (poetry2) or `[[tool.uv.index]]` (uv), with `default`/`secondary`/`primary` normalized to `priority`
- **Preserves `[tool.ruff]`, `[tool.pytest]`, etc.** — non-Poetry sections are kept as-is
- **Dry run** — preview on stdout before writing in place

## What It Converts

| Source (Poetry) | Target (PEP 621) | Notes |
| :--- | :--- | :--- |
| `[tool.poetry]` metadata | `[project]` | `name`, `version`, `description`, `license`, `readme`, `keywords`, `classifiers`, `urls`. Authors/maintainers parsed from `"Name <email>"` format. |
| `[tool.poetry.dependencies]` | `[project.dependencies]` | Caret/tilde/wildcard → PEP 440. `python` constraint → `requires-python`. |
| `[tool.poetry.extras]` | `[project.optional-dependencies]` | Bare dep names are expanded to full PEP 508 strings using version/extras from `[tool.poetry.dependencies]`. |
| `[tool.poetry.plugins]` | `[project.entry-points]` | Direct mapping. No other migration tool does this. |
| `[tool.poetry.scripts]` | `[project.scripts]` | Direct copy. |
| `[tool.poetry.dev-dependencies]` | `[dependency-groups.dev]` | Legacy format merged into `dev` group. |
| `[tool.poetry.group.*.dependencies]` | `[dependency-groups.*]` | All named groups preserved. |
| Git deps (`git`, `branch`, `tag`, `rev`, `subdirectory`) | PEP 508 + `#subdirectory=` (poetry2) or `[tool.uv.sources]` (uv) | Full ref support. |
| Path deps (`path`, `develop`) | `[tool.uv.sources]` (uv) | Editable flag preserved. |
| Per-dep `source = "name"` (uv) | `[tool.uv.sources] <dep> = { index = "name" }` | Associates a dep with a specific index. |
| `[[tool.poetry.source]]` | `[[tool.poetry.source]]` (poetry2) or `[[tool.uv.index]]` (uv) | Poetry 1 flags (`default`/`secondary`/`primary`) normalized to `priority`. For uv: `default → default=true`, `explicit → explicit=true`; supplemental/primary have no direct uv equivalent (declaration order applies). |
| `[build-system]` | Updated | `poetry-core>=2.0.0` (poetry2) or chosen backend (uv). |
| Other `[tool.*]` sections | Preserved | `[tool.ruff]`, `[tool.pytest.ini_options]`, etc. are kept as-is. |

### Version Constraint Translation

| Poetry | PEP 440 | Example |
| :--- | :--- | :--- |
| `^1.2.3` (caret) | `>=1.2.3,<2.0.0` | Major-bounded range |
| `^0.2.3` | `>=0.2.3,<0.3.0` | Minor-bounded for 0.x |
| `~1.2.3` (tilde) | `>=1.2.3,<1.3.0` | Minor-bounded range |
| `*` (wildcard) | `>=0.0.0` | Any version |
| `>=1.0,<2.0` | `>=1.0,<2.0` | PEP 440 passed through |

## Build Backends (uv target)

Use `--arg build=<backend>` to choose:

| Backend | `build-system.requires` | When to use |
| :--- | :--- | :--- |
| `hatchling` (default) | `hatchling` | Pure Python, most projects |
| `setuptools` | `setuptools>=61.0` | Legacy C extensions, existing `setup.cfg` |
| `flit` | `flit_core>=3.4` | Minimal pure Python libraries |
| `pdm` | `pdm-backend` | PDM ecosystem |
| `uv` | `uv-build>=0.7` | Bleeding edge, uv-native |

## Index Resolution (uv target)

Poetry consults every declared source and picks the best version. uv defaults to `index-strategy = "first-index"` (only the first index where a package exists is used) to prevent dependency-confusion attacks. When multiple indexes are declared and `index_strategy` is not set, the mold emits a warning.

Use `--arg index_strategy=<value>`:

| Value | Behavior |
| :--- | :--- |
| `first-index` | uv default. Safer; only the first index is consulted per package. |
| `unsafe-best-match` | Closest to Poetry. Searches every index, picks the best version. |
| `unsafe-first-match` | Searches every index, picks the first match. |

For tighter control, set `explicit = true` on private indexes and pin specific deps to them via `[tool.uv.sources]`.

## Known Limitations

These Poetry features are not converted (manual review needed):

- **`allow-prereleases`** per dependency — no PEP 621 equivalent.
- **`packages`** — build-backend-specific config, not portable (warning emitted).
- **`include` / `exclude`** — preserved under `[tool.poetry]` for poetry2 target; dropped for uv target.
- **`package-mode = false`** — preserved for poetry2; for uv, a warning is emitted (remove `[build-system]` manually or set `[tool.uv] package = false` in uv 0.5+).
- **URL deps** (`{url = "..."}`) — not converted.
- **Platform / Python markers per dep** (`{version = "^1.0", python = "^3.8"}`, `markers = "..."`) — not converted.
- **OR constraints** (version lists like `["^1.0", "^2.0"]`) — PEP 440 has no OR; converted to AND with a stderr warning.
- **Platform markers** — `python` markers on deps (e.g., `{version = "^1.0", python = "^3.8"}`) are not converted.
- **Lockfile** — `poetry.lock` is not migrated. Run `uv lock` or `poetry lock` after conversion.
- **Comments** — TOML comments from the original file are not preserved (inherent to parse/serialize).

## Recommended Workflow

```bash
# 1. Preview the conversion (stdout only)
fimod s -i pyproject.toml -m @poetry_migrate --arg target=uv

# 2. If it looks good, write in place
fimod s -i pyproject.toml -m @poetry_migrate --arg target=uv -i

# 3. Regenerate lockfile
uv lock

# 4. Verify
uv run python -c "import my_package"
```

## Full Project Migration

This mold only rewrites `pyproject.toml`. A complete Poetry → uv migration often
involves more: converting to src-layout, patching the `Dockerfile`, and updating
CI. See [`MIGRATE_FULL_PROMPT.md`](./MIGRATE_FULL_PROMPT.md) — a workflow prompt
you can feed to an LLM agent to drive the full migration end-to-end.
