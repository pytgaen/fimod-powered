# dockerfile

Generate a production-ready Dockerfile from a JSON or YAML project descriptor.

Supports **Python** (pip, poetry, uv) and **Node.js** (npm, yarn, pnpm) with optimized layer caching, non-root user, and healthcheck.

## Usage

```bash
fimod s -i app.yaml -m @dockerfile -o Dockerfile
fimod s -i app.yaml -m @dockerfile    # preview to stdout
```

## Input format

Only `cmd` (or `entrypoint`) is required. Everything else has sensible defaults.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `package_manager` | string | auto-detected | `pip`, `poetry`, `uv`, `npm`, `yarn`, `pnpm` |
| `base_image` | string | per manager | `python:3.12-slim` or `node:22-slim` |
| `multistage` | bool | `false` | Two-stage build (smaller final image) |
| `workdir` | string | `/app` | Working directory |
| `system_packages` | list | — | APT packages to install |
| `labels` | dict | — | Docker labels |
| `build_args` | list | — | Build-time ARG declarations (runtime stage) |
| `builder_build_args` | list | — | Build-time ARG declarations for the **builder** stage (private-registry credentials, etc.) |
| `env` | dict | — | Environment variables |
| `expose` | list | — | Ports to expose |
| `user` | string | — | Non-root user (created automatically) |
| `healthcheck` | object | — | `cmd`, `interval`, `timeout`, `start_period`, `retries` |
| `entrypoint` | list | — | Docker ENTRYPOINT |
| `cmd` | list | — | Docker CMD |
| `uv_version` | string | `latest` | uv version tag (e.g. `0.7.2`) |
| `uv_install` | string | `copy` | uv install method: `copy`, `curl`, `pip` |
| `poetry_version` | string | — | Poetry version to pin |
| `poetry_install` | string | `curl` | Poetry install method: `curl`, `pipx`, `pip` |
| `pipefail` | bool | `false` | Add `SHELL ["/bin/bash", "-o", "pipefail", "-c"]` |
| `skip_copy_all` | bool | `false` | Omit the runtime `COPY . .`. Use when you want fully selective copies via `runtime.finalize` + `.dockerignore` |
| `extra_instructions` | object | — | Custom instructions at hook points, split by stage (see below) |

## Extra instructions

For anything the mold doesn't handle natively, inject instructions at specific hook points. The block is split by stage (`builder` / `runtime`), each with three hooks:

```yaml
extra_instructions:
  builder:                  # only rendered if multistage: true
    before_install_pkgmgr:  # start of builder, before installing poetry/uv/npm
      - 'ENV POETRY_HTTP_BASIC_PRIVATE_USERNAME="${PYPI_USERNAME}"'
    before_install_deps:    # pkgmgr installed, before `poetry install` / `uv sync`
      - "RUN poetry config http-basic.private $PYPI_USERNAME $PYPI_PASSWORD"
    finalize:               # end of builder, after deps install + COPY . .
      - "RUN poetry run python -m app.precompile"

  runtime:
    after_os_update:        # after apt-get install, before user creation
      - cp: {certs/: /usr/local/share/ca-certificates/}
      - "RUN update-ca-certificates"
    after_deps_install:     # after dependency install, before COPY . .
      - "RUN python -m spacy download fr_core_news_sm"
    finalize:               # after COPY . ., before EXPOSE/CMD
      - "RUN python manage.py collectstatic --noinput"
      - "VOLUME /app/data"
```

Each hook accepts a list of entries. Every entry is one of:

- **Raw string** — inserted verbatim as a Dockerfile line (`"RUN ..."`, `"ENV ..."`, `"VOLUME ..."`, ...).
- **`{cp: {src: dest}}`** — expands to `COPY src dest` (with `--chown=user:user` auto-added when `user` is set).
- **`{cp: path/}`** — shorthand expanding to `COPY path/ <workdir>/path/` (same-name inside the working directory).

For private-registry auth: declare `ARG` via `builder_build_args` (not `build_args`, which only reaches the runtime stage), bind them to `ENV` via `builder.before_install_pkgmgr`, then optionally configure the package manager via `builder.before_install_deps`.

## Converting an existing Dockerfile

Use `CONVERT_PROMPT.md` with any LLM to convert an existing Dockerfile into a fimod descriptor:

```
cat molds/dockerfile/CONVERT_PROMPT.md my-existing/Dockerfile | llm "convert this Dockerfile"
```

The prompt guides the LLM to map standard Dockerfile patterns to descriptor fields, and route custom instructions into the appropriate `extra_instructions` hooks.

## Layer caching

The template is optimized for Docker layer caching: dependency manifest files are copied and installed **before** the source code. This means `docker build` only re-installs dependencies when `requirements.txt`, `pyproject.toml`, `package.json`, etc. actually change.

With `multistage: true`, the builder stage installs everything, then only the virtualenv (`.venv`) or `node_modules` is copied into the final image — no build tools, no cache, no package manager in production.

## Install methods

### uv (`uv_install`)

| Value | Method | Kaniko-compatible |
|-------|--------|:-:|
| `copy` (default) | `COPY --from=ghcr.io/astral-sh/uv:TAG` | no |
| `curl` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | yes |
| `pip` | `pip install uv` | yes |

### Poetry (`poetry_install`)

| Value | Method | Needs curl |
|-------|--------|:-:|
| `curl` (default) | `curl -sSL https://install.python-poetry.org \| python -` | yes |
| `pipx` | `pip install pipx && pipx install poetry` | no |
| `pip` | `pip install poetry` | no |

Both support version pinning via `uv_version` / `poetry_version`.

## Examples

### Python + uv

```yaml
package_manager: uv
expose: [8000]
user: app
cmd: ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

```dockerfile
FROM python:3.12-slim

RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=app:app . .

RUN uv sync --frozen --no-dev

EXPOSE 8000

USER app

CMD ["uvicorn","main:app","--host","0.0.0.0"]
```

### Python + poetry + healthcheck

```yaml
package_manager: poetry
system_packages: [curl]
expose: [8000]
healthcheck:
  cmd: ["curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 5s
  start_period: 10s
cmd: ["gunicorn", "app:app"]
```

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN curl -sSL https://install.python-poetry.org | python -
ENV PATH="/root/.local/bin:$PATH"
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
 && poetry install --only main --no-interaction --no-ansi

COPY . .

EXPOSE 8000

HEALTHCHECK \
    --interval=30s \
    --timeout=5s \
    --start-period=10s \
    CMD ["curl","-f","http://localhost:8000/health"]

CMD ["gunicorn","app:app"]
```

### Node.js + pnpm

```yaml
package_manager: pnpm
expose: [3000]
user: node
cmd: ["node", "index.js"]
```

```dockerfile
FROM node:22-slim

RUN groupadd -r node && useradd -r -g node -d /app -s /sbin/nologin node

WORKDIR /app

RUN corepack enable
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile --prod

COPY --chown=node:node . .

EXPOSE 3000

USER node

CMD ["node","index.js"]
```

### Multistage build (Python + uv)

Set `multistage: true` for a two-stage build: dependencies are installed in a builder stage, then only the virtualenv (Python) or `node_modules` (Node.js) is copied into the final image. This produces a smaller, cleaner runtime image.

```yaml
package_manager: uv
multistage: true
user: app
expose: [8000]
cmd: ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

```dockerfile
# ── Build stage ──────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

RUN uv sync --frozen --no-dev

# ── Runtime stage ────────────────────────────────────────────────
FROM python:3.12-slim

RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY --chown=app:app . .

EXPOSE 8000

USER app

CMD ["uvicorn","main:app","--host","0.0.0.0"]
```

### Minimal (auto-detected)

If `package_manager` is omitted, it's inferred from `base_image` (`python:*` → pip, `node:*` → npm):

```bash
echo '{"base_image":"node:20-slim","cmd":["node","app.js"]}' | fimod s -m @dockerfile
```
