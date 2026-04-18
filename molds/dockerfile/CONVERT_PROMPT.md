# Convert a Dockerfile to a fimod descriptor

You are converting an existing Dockerfile into a YAML (or JSON) descriptor for the `dockerfile` fimod mold. The mold generates production-ready Dockerfiles from declarative descriptors.

## Your task

Analyze the provided Dockerfile and produce a YAML descriptor that will regenerate an equivalent Dockerfile using `fimod s -i descriptor.yaml -m @dockerfile`.

## Available fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `package_manager` | string | auto-detected | `pip`, `poetry`, `uv`, `npm`, `yarn`, `pnpm` |
| `base_image` | string | `python:3.12-slim` / `node:22-slim` | Base Docker image |
| `multistage` | bool | `false` | Two-stage build |
| `workdir` | string | `/app` | Working directory |
| `system_packages` | list | — | APT packages to install |
| `labels` | dict | — | Docker labels |
| `build_args` | list | — | Build-time arguments |
| `env` | dict | — | Environment variables |
| `expose` | list | — | Ports to expose |
| `user` | string | — | Non-root user (created automatically) |
| `healthcheck` | object | — | `cmd`, `interval`, `timeout`, `start_period`, `retries` |
| `entrypoint` | list | — | Docker ENTRYPOINT |
| `cmd` | list | — | Docker CMD |
| `uv_version` | string | `latest` | uv version tag |
| `uv_install` | string | `copy` | `copy` (COPY --from), `curl`, `pip` |
| `poetry_version` | string | — | Poetry version to pin |
| `poetry_install` | string | `curl` | `curl` (official installer), `pipx`, `pip` |
| `pipefail` | bool | `false` | Add `SHELL ["/bin/bash", "-o", "pipefail", "-c"]` |
| `skip_copy_all` | bool | `false` | Omit the runtime `COPY . .`. Set to `true` when the original Dockerfile performs selective copies only |
| `builder_build_args` | list | — | Build-time ARG declarations for the **builder** stage (e.g. private-registry credentials) |
| `extra_instructions` | object | — | Custom instructions injected at hook points (see below) |

### Hook points (`extra_instructions`)

For anything the mold doesn't handle natively, use `extra_instructions`. The block is split by stage (`builder` / `runtime`), each with three hooks.

**Builder stage hooks** (`extra_instructions.builder.*`, only rendered when `multistage: true`):

- **`before_install_pkgmgr`** — start of the builder, right after `WORKDIR`, **before** the package manager tooling is installed (before `pip install poetry` / `curl uv` / `corepack enable`). Use for: `ENV` auth for private registries (`POETRY_HTTP_BASIC_*`, `NPM_TOKEN`, `PIP_INDEX_URL`), custom CA certs, proxy config — anything independent of the pm itself. ARG declarations go in `builder_build_args` (dedicated field), not here.
- **`before_install_deps`** — after pm tooling is installed, **before** `COPY <deps>` and `RUN <install deps>`. Use for: commands that need the pm binary (`RUN poetry config ...`, `RUN npm config set ...`, `RUN uv cache ...`).
- **`finalize`** — end of the builder, after dependency install and `COPY . .`. Use for: pre-compilation, ML model downloads, asset bundling whose output is part of the built venv / source tree copied over.

**Runtime stage hooks** (`extra_instructions.runtime.*`):

- **`after_os_update`** — after `apt-get install`, before user creation. Use for: custom certs, extra repos, system-level setup.
- **`after_deps_install`** — after dependency install (or after `COPY --from=builder .venv` in multistage), before `COPY . .`. Use for: downloading ML models, pre-compilation steps.
- **`finalize`** — after `COPY . .`, before `EXPOSE`/`CMD`. Use for: collectstatic, migrations, extra `COPY`, `VOLUME` declarations.

**Entry formats**

Each hook takes a list whose entries are one of:

- **Raw string** — inserted verbatim as a Dockerfile line: `"RUN ..."`, `"ENV ..."`, `"VOLUME /data"`, ...
- **`{cp: {src: dest}}`** — expands to `COPY src dest` (with `--chown=user:user` auto-added when `user` is set).
- **`{cp: "path/"}`** — shorthand expanding to `COPY path/ <workdir>/path/` (same-name inside the working directory).

Prefer the `cp` shorthand over raw `"COPY ..."` strings: it's shorter, avoids the `COPY`-bégaiement, and handles `--chown` automatically.

**Important — where do private-registry credentials go?**
- `ARG` declarations needed in the builder → `builder_build_args` (dedicated field, symmetric with runtime `build_args`).
- `ENV` bindings like `POETRY_HTTP_BASIC_*=${ARG}` → `builder.before_install_pkgmgr`.
- `RUN` commands that configure the pm (`poetry config http-basic ...`, `npm config set //registry...`) → `builder.before_install_deps` (after pm is installed).

`ARG` in Docker is scoped per stage: declaring it only in `build_args` (runtime) means the builder cannot read the flag value. Auth needed during `poetry install` / `uv sync` / `npm ci` must be declared in the **builder** via `builder_build_args`.

**If the same ARG is consumed in both stages** (rare, e.g. a version pin), declare it in **both** `build_args` and `builder_build_args`. Docker requires `ARG` to be re-declared per stage.

**Non-multistage + private auth**: the `builder.*` hooks only apply when `multistage: true`. For a mono-stage build with private-registry auth, put `ARG` in `build_args` and the matching `ENV POETRY_HTTP_BASIC_*=${ARG}` in `runtime.after_os_update` (which runs before dependency install in mono-stage). Less clean than multistage; prefer `multistage: true` when you need private registries.

**Private / mirror base images**
If the original Dockerfile uses a private or mirror registry image (e.g. `dockerproxy.mycorp/python:3.13-slim`, `internal-mirror.corp/node:22`), **preserve it as-is** in `base_image`. Do not replace it with the upstream default — the mirror is usually mandatory in the user's environment (corporate proxy, air-gapped build, compliance). Do not set `base_image` only when the Dockerfile uses the canonical default (`python:3.12-slim` or `node:22-slim`).

## Conversion rules

1. **Identify the package manager** from the Dockerfile:
   - `requirements.txt` / `pip install -r` → `pip`
   - `pyproject.toml` + `poetry` → `poetry`
   - `pyproject.toml` + `uv` → `uv`
   - `package.json` + `npm ci` → `npm`
   - `package.json` + `yarn` → `yarn`
   - `package.json` + `pnpm` → `pnpm`

2. **Detect multistage**: if there are multiple `FROM` instructions, set `multistage: true`.

3. **Omit defaults**: don't include fields that match the default values (`workdir: /app`, `base_image: python:3.12-slim` for Python, etc.).

4. **Map standard patterns to fields**:
   - `EXPOSE` → `expose`
   - `ENV` → `env`
   - `LABEL` → `labels`
   - `ARG` → `build_args`
   - `CMD` → `cmd`
   - `ENTRYPOINT` → `entrypoint`
   - `HEALTHCHECK` → `healthcheck` (parse `--interval`, `--timeout`, `--start-period`, `--retries`)
   - `USER` (when preceded by `groupadd`/`useradd`) → `user`
   - `apt-get install` → `system_packages`
   - `SHELL ["/bin/bash", "-o", "pipefail", "-c"]` → `pipefail: true`

5. **Detect install method**:
   - `COPY --from=ghcr.io/astral-sh/uv:VERSION` → `uv_install: copy`, extract `uv_version`
   - `curl ... astral.sh/uv` → `uv_install: curl`
   - `pip install uv` → `uv_install: pip`
   - `curl ... install.python-poetry.org` → `poetry_install: curl`
   - `pipx install poetry` → `poetry_install: pipx`
   - `pip install poetry` → `poetry_install: pip`
   - Extract version numbers when pinned.

6. **Custom instructions** — anything that doesn't map to a field goes into `extra_instructions`. The block is split into `builder` (only rendered when `multistage: true`) and `runtime` sub-blocks; place each instruction based on **which stage** it appears in and its position:

   Builder stage (`extra_instructions.builder.*`):
   - `ARG` in the builder → `builder_build_args` (dedicated field, not a hook)
   - `ENV` for auth / config that doesn't depend on the pm binary → `before_install_pkgmgr`
   - `RUN` commands using the pm (e.g. `poetry config`) → `before_install_deps`
   - Pre-compilation, model downloads, build-time side effects occurring after deps install → `finalize`

   Runtime stage (`extra_instructions.runtime.*`):
   - Between `apt-get` and user creation → `after_os_update`
   - Between dependency install and `COPY . .` → `after_deps_install`
   - After `COPY . .` and before `EXPOSE`/`CMD` → `finalize`

   Use the **`{cp: {src: dest}}`** form for `COPY` lines rather than raw `"COPY ..."` strings — it's shorter and auto-adds `--chown=user:user` when `user` is set.

7. **Selective vs generic source copy** — by default the mold emits `COPY . .` in the runtime stage. If the original Dockerfile performs **explicit, selective** `COPY dir/` instructions and has **no** generic `COPY . .`, this is an intentional pattern (often to avoid shipping tests/docs/secrets).
   - Set `skip_copy_all: true`.
   - Put every selective copy into `extra_instructions.runtime.finalize` using the `{cp: {src: dest}}` form, preserving original paths.
   - Recommend to the user (as a YAML comment at the top of the descriptor) to add a `.dockerignore` matching the original intent — this is the idiomatic Docker way to constrain what ends up in the build context, and is more maintainable than enumerating every copy.

8. **Normalize equivalent install patterns** — the mold only emits **2 stages** (`builder` + runtime). Dockerfiles using 3+ stages or non-standard install pipelines are almost always reducible to the canonical 2-stage build. **Normalize aggressively rather than trying to preserve structure.**

   Common normalizations:
   - `poetry export -f requirements.txt` + `pip wheel` + `pip install --no-index --find-links` → `package_manager: poetry` + `multistage: true`. The wheels pipeline produces the same installed packages as `poetry install` + `COPY --from=builder .venv`; drop the intermediate wheels.
   - `pip install` from a pre-built requirements lockfile committed to repo → `package_manager: pip`.
   - 3-stage pattern `base` → `builder` → `runtime` where `base` only defines a shared `FROM` → collapse: put the shared base image in `base_image`, drop the `base` stage.
   - 3-stage pattern `deps` → `build` → `runtime` where `build` just runs a one-shot command (asset compilation, code generation) → fold into the single `builder` stage via `extra_instructions.builder.finalize`.
   - Intermediate `test` / `lint` stages (stages that run checks but whose output isn't consumed by runtime) → **drop entirely**. They belong in CI, not in the production Dockerfile.

   Rule of thumb: if an intermediate stage's output ends up as a venv / site-packages / node_modules / compiled asset in the runtime, it's reducible. Only genuinely divergent pipelines (e.g., multi-platform cross-builds) cannot be collapsed.

9. **String fallback for unsupported Docker features** — some patterns have no dedicated field / shorthand. Use a **raw string** in the appropriate hook:
   - `COPY --from=<stage> <src> <dest>` (inter-stage copy other than the generated venv/node_modules) → raw string in the matching hook (typically `runtime.after_deps_install` or `runtime.finalize`).
   - `COPY --chmod=...`, `COPY --link`, `COPY` with multiple sources (`COPY a b c /dest/`), `ADD <url>`, `ADD <tar>` → raw string.
   - `RUN --mount=type=cache,...`, `RUN --mount=type=secret,...` → raw string.
   - Heredoc `RUN <<EOF ... EOF` → raw string (prefer single-line `RUN cmd1 && cmd2` rewrite when trivial).

   The `{cp: ...}` shorthand is only for plain `COPY src dest` from build context; every other `COPY`/`ADD` variant is a raw string.

10. **Hard limits — flag explicitly, don't fake it** — if normalization (rule 8) can't reduce the Dockerfile to 2 stages, or a pattern genuinely has no equivalent:
    - Emit the descriptor best-effort with the dropped / approximated parts,
    - Add a **top-of-file YAML comment** like `# NOTE: original Dockerfile has a 'test' stage dropped (move to CI). Runtime stage preserved.`
    - Do not invent hooks or fields that don't exist. Never silently omit critical behavior.

11. **Ignore generated patterns** — skip instructions that the mold generates automatically:
   - `RUN groupadd ... && useradd ...` (generated from `user`)
   - `WORKDIR /app` (default)
   - `COPY pyproject.toml ...`, `COPY requirements*.txt ...`, `COPY package.json ...` (generated from `package_manager`)
   - `RUN poetry config virtualenvs...` (generated)
   - `RUN uv sync ...` (generated)
   - `ENV PATH=".../\.venv/bin:$PATH"` in multistage runtime (generated)

## Example conversion

### Input Dockerfile

```dockerfile
FROM python:3.12-slim AS builder

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.6.12 /uv /uvx /usr/local/bin/
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

RUN uv sync --frozen --no-dev

FROM python:3.12-slim

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY custom.conf /etc/app/custom.conf

RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

ENV DATABASE_URL=postgresql://localhost/app
ENV LOG_LEVEL=info

COPY --chown=app:app . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000

USER app

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD ["curl", "-f", "http://localhost:8000/health"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

### Output descriptor

```yaml
package_manager: uv
multistage: true
uv_version: "0.6.12"
pipefail: true
system_packages:
  - curl
  - libpq-dev
user: app
env:
  DATABASE_URL: postgresql://localhost/app
  LOG_LEVEL: info
expose: [8000]
healthcheck:
  cmd: ["curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 5s
  start_period: 15s
extra_instructions:
  runtime:
    after_os_update:
      - cp: {custom.conf: /etc/app/custom.conf}
    finalize:
      - "RUN python manage.py collectstatic --noinput"
cmd: ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

### Example 2 — Private PyPI with Poetry

### Input Dockerfile

```dockerfile
FROM python:3.13-slim AS base

FROM base AS builder
RUN pip install --no-cache-dir poetry==1.8.5 wheel poetry-plugin-export

ARG PYPI_USERNAME
ARG PYPI_PASSWORD

ENV POETRY_HTTP_BASIC_PRIVATE_USERNAME="${PYPI_USERNAME}"
ENV POETRY_HTTP_BASIC_PRIVATE_PASSWORD="${PYPI_PASSWORD}"

WORKDIR /app
COPY pyproject.toml poetry.lock /app/

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN mkdir -p /tmp/pypi/wheels
RUN poetry export -f requirements.txt -o /tmp/pypi/requirements.txt --without-hashes --with-credentials
RUN pip wheel --no-deps --wheel-dir /tmp/pypi/wheels -r /tmp/pypi/requirements.txt

FROM base AS app
ENV TZ=Europe/Paris

RUN apt-get -y --no-install-recommends install tzdata

WORKDIR /app

COPY --from=builder /tmp/pypi /tmp/pypi
COPY --from=builder /app/ /app/
RUN pip install --no-cache-dir --no-index --find-links /tmp/pypi/wheels -r /tmp/pypi/requirements.txt && rm -fR /tmp/pypi
ENV PYTHONPATH=/app/

COPY install/ /install/

CMD ["python"]
```

### Output descriptor

```yaml
package_manager: poetry
base_image: python:3.13-slim
multistage: true
pipefail: true
poetry_version: "1.8.5"
system_packages:
  - tzdata
builder_build_args:
  - PYPI_USERNAME
  - PYPI_PASSWORD
env:
  TZ: Europe/Paris
  PYTHONPATH: /app/
extra_instructions:
  builder:
    before_install_pkgmgr:
      # Private PyPI credentials — ENV must be set in builder before `poetry install`
      - 'ENV POETRY_HTTP_BASIC_PRIVATE_USERNAME="${PYPI_USERNAME}"'
      - 'ENV POETRY_HTTP_BASIC_PRIVATE_PASSWORD="${PYPI_PASSWORD}"'
  runtime:
    finalize:
      # Additional source trees outside the default COPY . .
      - cp: {install/: /install/}
cmd: ["python"]
```

Note how the `poetry export` + `pip wheel` + `pip install --no-index` pipeline from the original Dockerfile has been **normalized away** (see conversion rule 7): the mold's standard multistage poetry build produces a functionally equivalent image.

## Output format

Return **only** the YAML descriptor inside a fenced code block. Add a brief comment for any `extra_instructions` entry explaining what the original instruction did. If rule 8 normalization dropped an intermediate stage, or rule 10 flagged a hard limit, add a top-of-file comment summarizing what was normalized away or approximated — so the user can verify the simplification is safe.
