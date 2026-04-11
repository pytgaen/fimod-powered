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
| `extra_instructions` | object | — | Custom instructions injected at hook points (see below) |

### Hook points (`extra_instructions`)

For anything the mold doesn't handle natively, use `extra_instructions` with these keys:

- **`after_system`** — after `apt-get install`, before user creation. Use for: custom certs, extra repos, system-level setup.
- **`after_install`** — after dependency install, before `COPY . .`. Use for: downloading ML models, pre-compilation steps.
- **`after_copy`** — after `COPY . .`, before `EXPOSE`/`CMD`. Use for: collectstatic, migrations, VOLUME declarations.

Each key takes a list of raw Dockerfile instructions (strings).

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

6. **Custom instructions** — anything that doesn't map to a field goes into `extra_instructions`. Place each instruction in the right hook based on where it appears in the original Dockerfile:
   - Between `apt-get` and dependency install → `after_system`
   - Between dependency install and `COPY . .` → `after_install`
   - After `COPY . .` and before `EXPOSE`/`CMD` → `after_copy`

7. **Ignore generated patterns** — skip instructions that the mold generates automatically:
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
  after_system:
    - "COPY custom.conf /etc/app/custom.conf"
  after_copy:
    - "RUN python manage.py collectstatic --noinput"
cmd: ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

## Output format

Return **only** the YAML descriptor inside a fenced code block. Add a brief comment for any `extra_instructions` explaining what the original instruction did. If the Dockerfile contains patterns that cannot be represented at all (e.g., multi-FROM beyond two stages, complex conditional logic), note them as comments in the YAML.
