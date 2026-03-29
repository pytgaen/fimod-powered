#!/usr/bin/env python3
"""Generate MkDocs documentation from mold READMEs, catalog.toml, and templates."""

import json
import shutil
import tomllib
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
MOLDS_DIR = ROOT / "molds"
CATALOG = MOLDS_DIR / "catalog.toml"
DOCS_DIR = ROOT / "docs"
TEMPLATES_DIR = ROOT / "docs-templates"
ASSETS_DIR = ROOT / "docs-assets"

FORMAT_LABELS = {
    "json": "JSON",
    "yaml": "YAML",
    "toml": "TOML",
    "csv": "CSV",
    "txt": "Text",
    "raw": "Raw",
    "http": "HTTP",
}

# Material icon per mold (used in grid cards on the home page)
MOLD_ICONS = {
    "dockerfile": ":material-docker:",
    "download": ":material-download:",
    "gh_latest": ":material-tag-arrow-down:",
    "html_report": ":material-table:",
    "poetry_migrate": ":material-swap-horizontal:",
    "skylos_to_gitlab": ":material-code-json:",
}


def load_catalog() -> dict:
    with open(CATALOG, "rb") as f:
        return tomllib.load(f)["molds"]


def build_metadata_header(name: str, meta: dict) -> str:
    """Build a metadata header block for a mold page."""
    lines = [f"# {name}", ""]

    description = meta.get("description", "")
    if description:
        lines.append(f"> {description}")
        lines.append("")

    # Format badges
    badges = []
    if "input_format" in meta:
        label = FORMAT_LABELS.get(meta["input_format"], meta["input_format"])
        badges.append(f"**Input:** `{label}`")
    if "output_format" in meta:
        label = FORMAT_LABELS.get(meta["output_format"], meta["output_format"])
        badges.append(f"**Output:** `{label}`")
    if "options" in meta:
        for opt in meta["options"]:
            badges.append(f"**Option:** `{opt}`")

    if badges:
        lines.append(" | ".join(badges))
        lines.append("")

    # Args table from catalog
    args = meta.get("args", {})
    if args:
        lines.append("| Arg | Description |")
        lines.append("|-----|-------------|")
        for arg_name, arg_desc in args.items():
            lines.append(f"| `{arg_name}` | {arg_desc} |")
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def build_mold_page(name: str, meta: dict) -> str:
    """Build a full mold documentation page."""
    readme_path = MOLDS_DIR / name / "README.md"
    readme_content = readme_path.read_text() if readme_path.exists() else ""

    # Strip the first H1 from README since we generate our own
    readme_lines = readme_content.split("\n")
    if readme_lines and readme_lines[0].startswith("# "):
        readme_lines = readme_lines[1:]
        # Also strip the blank line after the H1
        if readme_lines and readme_lines[0].strip() == "":
            readme_lines = readme_lines[1:]
    readme_content = "\n".join(readme_lines)

    header = build_metadata_header(name, meta)
    return header + readme_content


def build_catalog_index(catalog: dict) -> str:
    """Build the molds index page."""
    lines = [
        "# Mold Catalogue",
        "",
        "All available fimod-powered molds.",
        "",
        "| Mold | Description | Input | Output |",
        "|------|-------------|-------|--------|",
    ]

    for name, meta in sorted(catalog.items()):
        desc = meta.get("description", "")
        in_fmt = FORMAT_LABELS.get(meta.get("input_format", ""), "")
        out_fmt = FORMAT_LABELS.get(meta.get("output_format", ""), "")
        lines.append(f"| [`{name}`]({name}.md) | {desc} | {in_fmt} | {out_fmt} |")

    lines.append("")
    return "\n".join(lines)


def main():
    catalog = load_catalog()

    # Enrich catalog with icons for templates
    molds_ctx = {}
    for name, meta in sorted(catalog.items()):
        molds_ctx[name] = {
            **meta,
            "icon": MOLD_ICONS.get(name, ":material-cog:"),
        }

    # Clean and recreate docs/
    if DOCS_DIR.exists():
        shutil.rmtree(DOCS_DIR)
    (DOCS_DIR / "molds").mkdir(parents=True)

    # Generate mold pages (dynamic, from catalog + READMEs)
    for name, meta in catalog.items():
        page = build_mold_page(name, meta)
        (DOCS_DIR / "molds" / f"{name}.md").write_text(page)

    # Generate catalog index (dynamic)
    index = build_catalog_index(catalog)
    (DOCS_DIR / "molds" / "index.md").write_text(index)

    # Load showcase data
    showcase_path = TEMPLATES_DIR / "showcase.json"
    showcase = json.loads(showcase_path.read_text()) if showcase_path.exists() else []

    # Render Jinja2 templates (.md.j2)
    jinja_env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        keep_trailing_newline=True,
    )
    template_ctx = {"molds": molds_ctx, "showcase": showcase}

    for template_path in TEMPLATES_DIR.glob("*.md.j2"):
        template = jinja_env.get_template(template_path.name)
        output_name = template_path.name.removesuffix(".j2")
        rendered = template.render(**template_ctx)
        (DOCS_DIR / output_name).write_text(rendered)

    # Copy static templates (.md, no rendering needed)
    for static_path in TEMPLATES_DIR.glob("*.md"):
        shutil.copy2(static_path, DOCS_DIR / static_path.name)

    # Copy static assets
    if ASSETS_DIR.exists():
        shutil.copytree(ASSETS_DIR, DOCS_DIR / "assets")

    jinja_count = len(list(TEMPLATES_DIR.glob("*.md.j2")))
    static_count = len(list(TEMPLATES_DIR.glob("*.md")))
    print(f"Documentation generated in {DOCS_DIR}/")
    print(f"  - {len(catalog)} mold pages (from catalog + READMEs)")
    print(f"  - 1 catalog index")
    print(f"  - {jinja_count} rendered template(s)")
    print(f"  - {static_count} static page(s)")


if __name__ == "__main__":
    main()
