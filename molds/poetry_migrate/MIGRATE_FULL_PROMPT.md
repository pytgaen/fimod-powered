# Full Poetry → uv Migration Prompt

> **Purpose:** Guide an LLM agent (Claude Code, Cursor, etc.) through a complete
> Poetry-to-uv migration of a Python project, beyond the `pyproject.toml` rewrite
> handled by the `poetry_migrate` mold. Covers src-layout conversion, Dockerfile
> impact, and CI adjustments.
>
> **Scope:** This is a workflow prompt, not an executable mold. Feed it to an
> agent and let it drive the migration end-to-end, stopping for human review at
> each destructive step.

---

## Agent instructions

You are migrating a Python project from Poetry to uv. Follow the steps below in
order. After each step, report what you changed and wait for approval before
proceeding to the next destructive action (`git mv`, file writes, etc.).

---

### Step 1 — Audit

Before touching anything, gather facts.

1. Read `pyproject.toml`. Confirm `[tool.poetry]` is present. Extract:
   - Package `name` (normalized: dashes → underscores for the import name).
   - `packages` entry if declared (tells you the current layout explicitly).
   - Build backend in `[build-system]`.
2. Detect current source layout:
   - **Flat-layout**: `./{pkg_name}/__init__.py` exists at repo root.
   - **Src-layout**: `./src/{pkg_name}/__init__.py` exists.
   - **Other**: report and stop — needs manual decision.
3. Enumerate files that will be impacted:
   - `Dockerfile`, `.dockerignore`
   - `.github/workflows/*.yml`, `.gitlab-ci.yml`, `.circleci/config.yml`
   - `tox.ini`, `noxfile.py`, `Makefile`
   - `mkdocs.yml` (if docs reference the package path)
4. Check for a `poetry.lock`. Note it will be discarded.

**Output of Step 1:** a short report listing pkg_name, current layout, and the
files you'll need to touch. Ask the user to confirm before proceeding.

---

### Step 2 — Migrate `pyproject.toml`

Run the `poetry_migrate` mold. Default to `target=uv` with `build=hatchling`
unless the user specified otherwise.

```bash
# Preview first (stdout)
fimod s -i pyproject.toml -m @poetry_migrate --arg target=uv

# If the preview is clean, write in place
fimod s -i pyproject.toml -m @poetry_migrate --arg target=uv -i
```

Review stderr warnings from the mold — some Poetry features aren't converted
(see `molds/poetry_migrate/README.md` § Known Limitations). Surface these to the
user before continuing.

---

### Step 3 — Convert to src-layout (if currently flat)

Skip this step if the project already uses `src/`.

`uv init --package` defaults to src-layout and it's the modern convention.
Converting is low-risk but touches many files.

1. Move the package:
   ```bash
   mkdir -p src
   git mv {pkg_name} src/{pkg_name}
   ```
2. Update the build backend config in `pyproject.toml`:
   - **hatchling** (default):
     ```toml
     [tool.hatch.build.targets.wheel]
     packages = ["src/{pkg_name}"]
     ```
   - **setuptools**:
     ```toml
     [tool.setuptools.packages.find]
     where = ["src"]
     ```
   - **flit**: add `[tool.flit.module] name = "{pkg_name}"` (flit auto-detects `src/`).
   - **pdm**: `[tool.pdm.build] package-dir = "src"`.
   - **uv-build**: auto-detects `src/{pkg_name}`, no config needed.
3. Update tool configs that reference the old path:
   - `[tool.ruff]` `src = ["src", "tests"]`
   - `[tool.pytest.ini_options]` `pythonpath = ["src"]` (if tests import directly)
   - `[tool.coverage.run]` `source = ["src"]`
   - `[tool.mypy]` `mypy_path = "src"`
4. Scan for hardcoded path references:
   ```bash
   rg -l "{pkg_name}/" --glob '!src/**' --glob '!.git/**'
   ```
   Common hits: `Makefile`, CI scripts, docs, `MANIFEST.in`. Fix each.
5. Imports inside the package (`from {pkg_name}.foo import ...`) don't change —
   only the filesystem location moves.

---

### Step 4 — Dockerfile impact

Only if a `Dockerfile` exists at the repo root (or in common locations:
`docker/`, `deploy/`).

1. Parse the Dockerfile. Identify every `COPY` / `ADD` that references:
   - `pyproject.toml`, `poetry.lock` → replace `poetry.lock` with `uv.lock`.
   - The package directory (`COPY {pkg_name}/ ...` or `COPY . .`).
2. Identify the install command:
   - `poetry install [--no-dev|--only main]` → replace with `uv sync --frozen [--no-dev]`.
   - `pip install poetry && poetry install` → replace the poetry bootstrap with
     a uv install (see below).
3. Propose the patched Dockerfile. Two idiomatic shapes:

   **Option A — minimal patch (keep existing base image):**
   ```dockerfile
   # Install uv (replaces poetry bootstrap)
   COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

   COPY pyproject.toml uv.lock ./
   COPY src/ ./src/           # was: COPY {pkg_name}/ ./{pkg_name}/
   RUN uv sync --frozen --no-dev
   ```

   **Option B — regenerate via `dockerfile` mold:** if the project has (or can
   produce) a JSON/YAML descriptor, run:
   ```bash
   fimod s -i descriptor.json -m @dockerfile -o Dockerfile
   ```

4. Update `.dockerignore`: add `.venv/`, `uv.lock` is usually kept (not ignored),
   remove any Poetry-specific entries.
5. Flag to the user: multi-stage builds usually benefit from copying `uv.lock`
   and `pyproject.toml` *before* the source tree to maximize layer cache reuse.
   Preserve that ordering.

**Do not write the Dockerfile yet.** Show the diff, let the user approve, then
write.

---

### Step 5 — CI adjustments

Scan CI config files found in Step 1. Apply these rewrites:

| Old (Poetry) | New (uv) |
| :--- | :--- |
| `pip install poetry` | `pip install uv` (or use `astral-sh/setup-uv` action) |
| `poetry install` | `uv sync --frozen` |
| `poetry install --no-dev` | `uv sync --frozen --no-dev` |
| `poetry run <cmd>` | `uv run <cmd>` |
| `poetry build` | `uv build` |
| Cache key on `poetry.lock` | Cache key on `uv.lock` |

GitHub Actions: prefer the official `astral-sh/setup-uv@v3` action — it handles
caching automatically.

---

### Step 6 — Validate

Run, in order:

```bash
uv lock                          # generate uv.lock
uv sync                          # install deps
uv run python -c "import {pkg_name}"   # import smoke test
uv run pytest                    # if tests exist
docker build -t migration-check . # if Dockerfile was touched
```

Any failure → stop and report. Do not paper over errors.

---

### Step 7 — Cleanup

Only after validation succeeds:

- Delete `poetry.lock`.
- Remove Poetry from any bootstrap scripts or README install instructions.
- Update README install/dev sections to use `uv sync` / `uv run`.

---

## Reporting format

At the end of the run, produce a summary:

```
Migration summary
─────────────────
 pyproject.toml:  migrated (target=uv, build=hatchling)
 Layout:          flat → src/  ({pkg_name}/ → src/{pkg_name}/)
 Dockerfile:      patched (install command + COPY paths)
 CI:              .github/workflows/test.yml updated
 Lockfile:        uv.lock regenerated, poetry.lock deleted
 Validation:      uv sync OK, pytest OK (42 passed), docker build OK

 Warnings from poetry_migrate mold:
  - {warning 1}
  - {warning 2}

 Manual review required:
  - {anything the agent couldn't safely convert}
```
