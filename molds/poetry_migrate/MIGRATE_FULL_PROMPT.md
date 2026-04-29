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

### Step 3 — Source layout: decide, then act

`uv init --package` defaults to src-layout, but hatchling (and most modern
backends) supports **both flat and src layouts equally well**. Converting is
**not** a prerequisite of the Poetry→uv migration — it's an orthogonal project
convention choice. Make the decision explicitly before doing anything.

#### Step 3a — Decide

Reasons to convert to `src/`:
- Greenfield-ish project where modern conventions matter.
- You want test runs to fail loudly if the package isn't installed (anti-shadowing).
- Build backend struggles with auto-detection in flat (e.g. namespace package, mismatched names).

Reasons to stay flat:
- Many hardcoded references to `{pkg_name}/` in CI, `Makefile`, docs, `MANIFEST.in` (high churn).
- Project is published, stable, and downstream tooling expects the current layout.
- Namespace package (PEP 420, multi-repo) already wired up.

**To check whether shadowing is masking real bugs** (the strongest technical
argument for `src/`), run the wheel-install smoke test from outside the repo:
```bash
uv build --wheel
uv pip install --force-reinstall dist/*.whl
cd /tmp && uv run --no-project python -c "import {pkg_name}; print({pkg_name}.__file__)"
```
If the printed path is inside the repo (not `.venv/`), or imports break when
run from `/tmp`, the flat layout is hiding packaging bugs — convert to `src/`.

**Output of Step 3a:** state the choice (stay flat / convert) and the reason.
Ask the user to confirm before continuing.

#### Step 3b — Path A: Stay flat (audit hatchling)

Hatchling auto-detects a package matching the normalized project name
(`name = "my-tool"` → looks for `my_tool/`). If your project fits that mold,
nothing to configure. Otherwise, watch for these pitfalls:

1. **Directory name doesn't match `name`** (e.g. `name = "mytool"` but folder
   `MyTool/`): add explicit packages.
   ```toml
   [tool.hatch.build.targets.wheel]
   packages = ["MyTool"]
   ```

2. **Wheel pollution**: in flat layout, hatchling can sweep up `tests/`,
   `examples/`, `scripts/`, `docs/` if auto-detection misfires. Verify with:
   ```bash
   uv build --wheel
   python -m zipfile -l dist/*.whl
   ```
   If unwanted directories appear, pin packages explicitly (as above) or
   exclude them:
   ```toml
   [tool.hatch.build.targets.wheel]
   packages = ["{pkg_name}"]
   exclude = ["tests", "examples", "scripts"]
   ```

3. **Namespace packages (PEP 420, no `__init__.py`)**: not auto-detected.
   Declare them:
   ```toml
   [tool.hatch.build.targets.wheel]
   packages = ["myorg/sub_namespace"]
   ```

4. **Single top-level module** (`mymod.py` file, no package directory):
   ```toml
   [tool.hatch.build.targets.wheel]
   only-include = ["mymod.py"]
   ```

5. **Tool configs that assume src-layout**: remove or adjust if present —
   `[tool.ruff] src = ["src", "tests"]`, `pythonpath = ["src"]`, etc.

#### Step 3c — Path B: Convert to src-layout

1. Move the package:
   ```bash
   mkdir -p src
   git mv {pkg_name} src/{pkg_name}
   ```
2. Update the build backend config in `pyproject.toml`:
   - **hatchling** (default): usually auto-detects `src/{pkg_name}` when the
     name matches. To be explicit:
     ```toml
     [tool.hatch.build.targets.wheel]
     packages = ["src/{pkg_name}"]
     ```
   - **setuptools**:
     ```toml
     [tool.setuptools.packages.find]
     where = ["src"]
     ```
   - **flit**: add `[tool.flit.module] name = "{pkg_name}"` (auto-detects `src/`).
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

#### Step 4a — Decide

Default recommendation: **Path B (regenerate via `molds/dockerfile`)** — you
get a canonical, normalized 2-stage uv build. **Switch the recommendation to
Path A** if the existing Dockerfile shows any of these signals (the mold's
field set can't preserve them faithfully):

- `RUN --mount=type=secret` or `RUN --mount=type=cache` (BuildKit features).
- `ADD <url>`, `ADD <tar>`, or multi-source `COPY a b c /dest/`.
- 3+ build stages where intermediate stages produce artifacts consumed at
  runtime (not just test/lint).
- Heavy native compilation (Rust extensions, C deps with custom flags) tied
  to a precise step order.
- Internal pre-baked base image (org-hardened) where regenerating apt-get /
  user creation would be redundant or forbidden.
- Multi-arch / cross-compilation logic (`BUILDPLATFORM`/`TARGETPLATFORM`).

If any apply → recommend Path A and explain which signal triggered it.
Otherwise → recommend Path B.

**Ask the user explicitly** before doing anything:

> *"Do you want to migrate the Dockerfile now?*
> *— **Path A** (quick patch): keep the current shape, swap `poetry install` → `uv sync`, fix COPY paths.*
> *— **Path B** (default; regenerate via `dockerfile` mold): canonical 2-stage uv build from a YAML descriptor.*
> *— **Defer**: leave the Dockerfile alone for now."*

If deferred → skip to Step 5 and list the Dockerfile in the final report's
*Manual review required* section.

#### Step 4b — Path A: Quick patch

1. Parse the Dockerfile. Identify every `COPY` / `ADD` referencing:
   - `pyproject.toml`, `poetry.lock` → replace `poetry.lock` with `uv.lock`.
   - The package directory (`COPY {pkg_name}/ ...` or `COPY . .`).
2. Identify the install command:
   - `poetry install [--no-dev|--only main]` → `uv sync --frozen [--no-dev]`.
   - `pip install poetry && poetry install` → drop the poetry bootstrap, install uv as below.
3. Propose the patched Dockerfile:
   ```dockerfile
   COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

   COPY pyproject.toml uv.lock ./
   COPY src/ ./src/           # was: COPY {pkg_name}/ ./{pkg_name}/  (adjust if Step 3 kept flat)
   RUN uv sync --frozen --no-dev
   ```
4. Update `.dockerignore`: add `.venv/`, keep `uv.lock` (don't ignore), remove Poetry-specific entries.
5. Multi-stage builds: copy `uv.lock` and `pyproject.toml` *before* the source tree to maximize layer cache reuse.

**Do not write the Dockerfile yet.** Show the diff, let the user approve, then write.

#### Step 4c — Path B: Regenerate via `molds/dockerfile`

The `dockerfile` mold ships a dedicated conversion prompt that turns an
existing Dockerfile into a YAML descriptor, then regenerates a canonical
multistage uv build.

1. **Convert Dockerfile → descriptor.** Hand the existing Dockerfile to the
   conversion prompt at `molds/dockerfile/CONVERT_PROMPT.md`. It produces a
   YAML descriptor with normalized stages, `package_manager: uv`,
   healthcheck/user/expose extracted, etc. Save it as `container.yaml`.

2. **Regenerate the Dockerfile from the descriptor:**
   ```bash
   fimod s -i container.yaml -m @dockerfile -o Dockerfile.new
   ```

3. **Diff `Dockerfile.new` vs `Dockerfile`** and surface every divergence to
   the user — especially:
   - Intermediate stages dropped (test/lint → fine; real build stage → flag).
   - System packages added or removed.
   - Healthcheck / non-root user / `EXPOSE` changes.
   - Private-registry credentials handling (ARG/ENV placement may differ).

4. On approval: replace `Dockerfile` with `Dockerfile.new`. Ask the user
   whether they want to **commit `container.yaml` alongside** — useful if they
   plan to re-run the mold later when bumping uv versions or base images.
   Otherwise it can be discarded.

5. Update `.dockerignore` (same as Path A step 4).

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
 Layout:          flat (kept) | flat → src/ ({pkg_name}/ → src/{pkg_name}/)
 Dockerfile:      patched (Path A) | regenerated via dockerfile mold (Path B) | deferred
 CI:              .github/workflows/test.yml updated
 Lockfile:        uv.lock regenerated, poetry.lock deleted
 Validation:      uv sync OK, pytest OK (42 passed), docker build OK

 Warnings from poetry_migrate mold:
  - {warning 1}
  - {warning 2}

 Manual review required:
  - {anything the agent couldn't safely convert}
```
