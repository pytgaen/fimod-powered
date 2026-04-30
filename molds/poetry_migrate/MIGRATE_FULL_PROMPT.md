# Poetry Migrate — LLM workflow prompt

> Feed this prompt to an LLM agent to get the most out of the `poetry_migrate` mold.
> The agent audits your `pyproject.toml`, builds the right `fimod` command, runs it,
> and handles complementary steps only when needed.

---

## Phase 1 — Audit

Read `pyproject.toml`. Confirm `[tool.poetry]` is present — if not, stop. This mold is for Poetry projects only.

Determine the following before proposing any command:

### 1. Target

Ask if not stated:

- **`poetry2`** — stay on Poetry, update to v2 format (default)
- **`uv`** — migrate to uv + PEP 621

### 2. Backend (uv target only)

- **`hatchling`** — default, no extra arg needed, recommended for most projects
- **`uv-build`** — uv-native; propose only if the user explicitly wants it. Warn that it is limited (no entry-points, no namespace packages).

### 3. Index strategy (uv target, only if multiple `[[tool.poetry.source]]` entries)

Poetry searches all sources and picks the best version. uv defaults to `first-index` (safer, prevents dependency confusion). Ask:

> *"Multiple sources detected. Do you want to preserve Poetry's 'search every index' behaviour (`--arg index_strategy=unsafe-best-match`), or keep uv's safer default (`first-index`)?"*

### 4. Known Limitations scan

Scan `pyproject.toml` and warn **before running** if any of these are present:

| Pattern | Impact |
| :--- | :--- |
| `allow-prereleases` on a dependency | Not converted — manual action needed |
| `markers` / `python` key on a dependency | Not converted |
| Version list e.g. `["^1.0", "^2.0"]` | Converted to AND (not OR) — review result |
| `package-mode = false` | Warning emitted for uv target |
| `{url = "..."}` dependency | Not converted |

Report findings and confirm the command before running.

---

## Phase 2 — Run the mold

Always dry-run first (stdout only):

```bash
fimod s -i pyproject.toml -m @poetry_migrate [--arg target=uv] [--arg build=uv] [--arg index_strategy=unsafe-best-match]
```

Read stderr warnings and surface them to the user. If the output looks good, write in place:

```bash
fimod s -i pyproject.toml -m @poetry_migrate [options] -o pyproject.toml -i
```

---

## Phase 3 — Complements (only if needed)

### Src layout

Converting to src-layout is **optional and orthogonal** to the migration. Only propose it if the user asks or there is a concrete packaging issue (e.g. test shadowing the installed package).

```bash
mkdir -p src
git mv {pkg_name} src/{pkg_name}
```

If hatchling does not auto-detect the package, add to `pyproject.toml`:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/{pkg_name}"]
```

### Lockfile

Use the command matching the target chosen in Phase 1:

- **uv target** — regenerate `uv.lock`, then install:
  ```bash
  uv lock
  uv sync          # install from the new lockfile
  uv sync -U       # alternatively: upgrade all deps to latest allowed versions
  ```

- **poetry2 target** — regenerate `poetry.lock`:
  ```bash
  poetry lock
  ```

### CI

| Old (Poetry) | New (uv) |
| :--- | :--- |
| `pip install poetry` | `pip install uv` or `astral-sh/setup-uv@v3` |
| `poetry install` | `uv sync --frozen` |
| `poetry run <cmd>` | `uv run <cmd>` |
| `poetry build` | `uv build` |
| Cache key on `poetry.lock` | Cache key on `uv.lock` |

### Dockerfile

If a `Dockerfile` exists, handle it separately using `molds/dockerfile/CONVERT_PROMPT.md`.
