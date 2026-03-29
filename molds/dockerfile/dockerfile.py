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

def transform(data, args, **_):
    pm = data.get("package_manager")

    if not pm:
        # Try to infer from base_image
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

    # Set defaults
    if not data.get("base_image"):
        data["base_image"] = DEFAULT_IMAGES[pm]

    if not data.get("workdir"):
        data["workdir"] = "/app"

    data["package_manager"] = pm
    data["is_python"] = pm in PYTHON_MANAGERS
    data["is_node"] = pm in NODE_MANAGERS
    data["multistage"] = data.get("multistage", False)

    return tpl_render_from_mold("templates/Dockerfile.j2", data)
