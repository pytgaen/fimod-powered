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
| `build_args` | list | — | Build-time arguments |
| `env` | dict | — | Environment variables |
| `expose` | list | — | Ports to expose |
| `user` | string | — | Non-root user (created automatically) |
| `healthcheck` | object | — | `cmd`, `interval`, `timeout`, `retries` |
| `entrypoint` | list | — | Docker ENTRYPOINT |
| `cmd` | list | — | Docker CMD |

## Layer caching

The template is optimized for Docker layer caching: dependency manifest files are copied and installed **before** the source code. This means `docker build` only re-installs dependencies when `requirements.txt`, `pyproject.toml`, `package.json`, etc. actually change.

With `multistage: true`, the builder stage installs everything, then only the virtualenv (`.venv`) or `node_modules` is copied into the final image — no build tools, no cache, no package manager in production.

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

COPY . .

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
cmd: ["gunicorn", "app:app"]
```

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir poetry
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
 && poetry install --only main --no-interaction --no-ansi

COPY . .

EXPOSE 8000

HEALTHCHECK \
    --interval=30s \
    --timeout=5s \
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
