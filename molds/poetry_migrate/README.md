# Poetry Migrate

Migrate a Poetry `pyproject.toml` to **Poetry 2** or **uv** format, with full PEP 621 compliance.

```bash
# Poetry 1 → Poetry 2 (default)
fimod s -i pyproject.toml -m @poetry_migrate -o pyproject.toml -i

# Poetry → uv (hatchling backend)
fimod s -i pyproject.toml -m @poetry_migrate --arg target=uv -o pyproject.toml -i

# Poetry → uv (setuptools backend)
fimod s -i pyproject.toml -m @poetry_migrate --arg target=uv --arg build=setuptools -o pyproject.toml -i
```

## Why This Mold?

There is no built-in migration command in Poetry, uv, or pip. Existing third-party tools (`pdm import`, `migrate-to-uv`) are either targeting a different ecosystem or handle only basic cases. None of them convert plugins, offer build backend choice, or support dual targets.

This mold does:

- **Dual target** — Poetry 2 and uv from the same tool
- **Plugins → entry-points** — no other migration tool does this
- **5 build backends** — hatchling, setuptools, flit, pdm, uv-build
- **Git + path deps** with full ref support (branch/tag/rev, editable)
- **Poetry sources → `[[tool.uv.index]]`**
- **Preserves `[tool.ruff]`, `[tool.pytest]`, etc.** — non-Poetry sections are kept as-is
- **Dry run** — preview on stdout before writing in place

## What It Converts

| Source (Poetry) | Target (PEP 621) | Notes |
| :--- | :--- | :--- |
| `[tool.poetry]` metadata | `[project]` | `name`, `version`, `description`, `license`, `readme`, `keywords`, `classifiers`, `urls`. Authors/maintainers parsed from `"Name <email>"` format. |
| `[tool.poetry.dependencies]` | `[project.dependencies]` | Caret/tilde/wildcard → PEP 440. `python` constraint → `requires-python`. |
| `[tool.poetry.extras]` | `[project.optional-dependencies]` | Direct mapping. |
| `[tool.poetry.plugins]` | `[project.entry-points]` | Direct mapping. No other migration tool does this. |
| `[tool.poetry.scripts]` | `[project.scripts]` | Direct copy. |
| `[tool.poetry.dev-dependencies]` | `[dependency-groups.dev]` | Legacy format merged into `dev` group. |
| `[tool.poetry.group.*.dependencies]` | `[dependency-groups.*]` | All named groups preserved. |
| Git deps (`git`, `branch`, `tag`, `rev`) | PEP 508 (poetry2) or `[tool.uv.sources]` (uv) | Full ref support. |
| Path deps (`path`, `develop`) | `[tool.uv.sources]` (uv) | Editable flag preserved. |
| `[[tool.poetry.source]]` | `[[tool.uv.index]]` (uv) | Name, URL, default flag. |
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

## Known Limitations

These Poetry features are not converted (manual review needed):

- **`allow-prereleases`** per dependency — no PEP 621 equivalent.
- **`source` per dependency** — association of a specific dep with a specific index is lost.
- **`packages` / `include` / `exclude`** — build-backend-specific config, not portable.
- **Platform markers** — `python` markers on deps (e.g., `{version = "^1.0", python = "^3.8"}`) are not converted.
- **OR constraints** (version lists like `["^1.0", "^2.0"]`) — PEP 440 has no OR; converted to AND with a stderr warning.
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
