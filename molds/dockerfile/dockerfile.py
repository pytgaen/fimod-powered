"""
Generate a production-ready Dockerfile from a JSON/YAML descriptor.

Supports Python (pip, poetry, uv) and Node.js (npm, yarn, pnpm)
with optimized layer caching, non-root user, and best practices.

Usage:
  fimod s -i app.yaml -m @dockerfile -o Dockerfile
  fimod s -i app.yaml -m @dockerfile   # preview to stdout
"""
# fimod: output-format=txt

PYTHON_MANAGERS = ["pip", "poetry", "uv"]
NODE_MANAGERS = ["npm", "yarn", "pnpm"]
KNOWN_MANAGERS = PYTHON_MANAGERS + NODE_MANAGERS

DEFAULT_IMAGES = {
    "pip": "python:3.12-slim",
    "poetry": "python:3.12-slim",
    "uv": "python:3.12-slim",
    "npm": "node:22-slim",
    "yarn": "node:22-slim",
    "pnpm": "node:22-slim",
}

BUILDER_HOOKS = ["before_install_pkgmgr", "before_install_deps", "finalize"]
RUNTIME_HOOKS = ["after_os_update", "after_deps_install", "finalize"]


def _render_entry(entry, user, workdir):
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict) and len(entry) == 1 and "cp" in entry:
        val = entry["cp"]
        chown = f" --chown={user}:{user}" if user else ""
        if isinstance(val, str):
            name = val.rstrip("/").split("/")[-1]
            dest = f"{workdir.rstrip('/')}/{name}/"
            return f"COPY{chown} {val} {dest}"
        if isinstance(val, dict) and len(val) == 1:
            src, dest = next(iter(val.items()))
            return f"COPY{chown} {src} {dest}"
        gk_fail(f"Invalid 'cp' value (expected string or single-key dict): {val!r}")
    gk_fail(f"Invalid extra_instructions entry (expected string or {{cp: ...}}): {entry!r}")
    return ""


def _flatten_hooks(extra, section, hooks, user, workdir):
    block = extra.get(section) or {}
    if not isinstance(block, dict):
        gk_fail(f"extra_instructions.{section} must be a mapping, got {type(block).__name__}")
        return {}
    unknown = [k for k in block if k not in hooks]
    if unknown:
        gk_fail(f"Unknown {section} hooks: {unknown}. Expected: {hooks}")
    out = {}
    for hook in hooks:
        entries = block.get(hook) or []
        out[hook] = [_render_entry(e, user, workdir) for e in entries]
    return out


def transform(data, args, **_):
    pm = data.get("package_manager")

    if not pm:
        img = data.get("base_image", "")
        if "python" in img:
            pm = "pip"
        elif "node" in img:
            pm = "npm"
        else:
            pm = "pip"

    if pm not in KNOWN_MANAGERS:
        gk_fail(f"Unknown package_manager: '{pm}'. Expected one of: {', '.join(KNOWN_MANAGERS)}")
        return ""

    if not data.get("base_image"):
        data["base_image"] = DEFAULT_IMAGES[pm]

    if not data.get("workdir"):
        data["workdir"] = "/app"

    data["package_manager"] = pm
    data["is_python"] = pm in PYTHON_MANAGERS
    data["is_node"] = pm in NODE_MANAGERS
    data["multistage"] = data.get("multistage", False)
    data["uv_version"] = data.get("uv_version", "latest")
    data["uv_install"] = data.get("uv_install", "copy")
    data["poetry_version"] = data.get("poetry_version")
    data["poetry_install"] = data.get("poetry_install", "curl")
    data["pipefail"] = data.get("pipefail", False)
    data["skip_copy_all"] = data.get("skip_copy_all", False)

    extra = data.get("extra_instructions") or {}
    if not isinstance(extra, dict):
        gk_fail("extra_instructions must be a mapping with 'builder' and/or 'runtime' sub-blocks")
        return ""
    unknown_sections = [k for k in extra if k not in ("builder", "runtime")]
    if unknown_sections:
        gk_fail(f"extra_instructions must only contain 'builder' / 'runtime', got: {unknown_sections}")
        return ""

    user = data.get("user")
    workdir = data["workdir"]
    data["builder_hooks"] = _flatten_hooks(extra, "builder", BUILDER_HOOKS, user, workdir)
    data["runtime_hooks"] = _flatten_hooks(extra, "runtime", RUNTIME_HOOKS, user, workdir)

    return tpl_render_from_mold("templates/Dockerfile.j2", data)
