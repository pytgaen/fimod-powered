# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Code directive

Don’t change anything unless you’re 95% sure about it. If you're ever in doubt, just give me a shout with some follow-up questions.

## Project Overview

Fimod-Powered is a collection of production-ready Python transformation scripts ("molds") for the [fimod](https://github.com/pytgaen/fimod) CLI. Fimod is a Rust-based data transformation engine that reads JSON/YAML/TOML/CSV/NDJSON/plain text, executes Python molds via Monty (embedded Python runtime), and outputs in any format. No system Python required.

## Testing

Tests use fimod's fixture-based test runner. Each mold's tests live in `test-molds/{mold_name}/`.

```bash
# Test all molds
fimod mold test ./test-molds

# Test a specific mold
fimod mold test ./test-molds/dockerfile

# Preview a mold's output manually
fimod s -i test-molds/poetry_migrate/basic.input.toml -m molds/poetry_migrate/poetry_migrate.py --arg target=uv
```

### Fixture format

Each test case consists of:
- `{case}.input.*` — input file (JSON, TOML, CSV, etc.)
- `{case}.expected.*` — expected output
- `{case}.run-test.toml` — optional config for args, env vars, exit code, output format, `skip = true`

## Architecture

### Mold structure

```
molds/{name}/
├── {name}.py              # Main transformation (must export `transform`)
├── templates/             # Jinja2 templates (optional)
│   └── template.j2
└── README.md

test-molds/{name}/
├── {case}.input.*
├── {case}.expected.*
└── {case}.run-test.toml   # optional
```

### Transform function signature

Every mold must export:
```python
def transform(data, args, env, headers):
```
- `data` — parsed input (dict, list, or scalar depending on format)
- `args` — dict from `--arg key=value` CLI flags
- `env` — dict of environment variables (filtered by `--env PATTERN`)
- `headers` — list of column names for CSV input, else None

### Mold directives

Special `# fimod:` comments at the top of mold files:
- `output-format=txt|json|toml|yaml|csv|raw` — override output format
- `input-format=http|json|yaml|toml|csv|txt` — override input format
- `arg=name Description` — document CLI arguments (shown in `fimod mold list`)
- `no-follow` — don't follow HTTP redirects
- `raw-mode=no-quote` — output bare strings without JSON quoting

The module-level docstring (`"""..."""`) is the mold description shown by `fimod mold list`.

## Available Built-in Functions

Molds run in Monty's sandbox with these built-ins (no imports needed):

| Category | Functions |
|----------|-----------|
| **Output** | `set_output_format(fmt)`, `set_output_file(filename)` |
| **Logging** | `msg_print`, `msg_info`, `msg_warn`, `msg_error` |
| **Validation** | `gk_fail(msg)` (exit with error), `gk_assert(cond, msg)`, `gk_warn(msg)` |
| **Hashing** | `hs_md5`, `hs_sha256`, `hs_sha1` |
| **Dotpath** | `dp_get(obj, "path.to.field")`, `dp_set(obj, "path", value)` |
| **Iteration** | `it_keys`, `it_values`, `it_flatten`, `it_group_by`, `it_sort_by`, `it_unique`, `it_unique_by` |
| **Templates** | `tpl_render_str(template, context)`, `tpl_render_from_mold(path, context, auto_escape=False)` |
| **Regex** | `re_search`, `re_match`, `re_findall`, `re_sub`, `re_split` (plus `_fancy` variants for lookahead/lookbehind) |
| **Environment** | `env_subst("${VAR_NAME}")` |

## Key Patterns

- **Error handling**: Use `msg_warn()` for non-fatal issues, `gk_fail()` for validation failures
- **HTTP molds**: Use `# fimod: input-format=http` to get raw response with `data["headers"]` and `data["body"]`
- **Template rendering**: Load Jinja2 templates via `tpl_render_from_mold("templates/template.j2", context)`
- **Args access**: `args.get("key", "default")` for safe access to CLI arguments

## Current Molds

| Mold | Purpose |
|------|---------|
| `dockerfile` | Generate production Dockerfiles from JSON/YAML descriptors (Python + Node.js, multistage builds) |
| `html_report` | Convert JSON/CSV to standalone HTML reports with sortable tables |
| `poetry_migrate` | Migrate Poetry pyproject.toml to Poetry 2 or uv (PEP 621) |
| `download` | Download files from URLs (wget-like, uses HTTP input format) |
| `gh_latest` | Get latest GitHub release tag or download URL |
| `skylos_to_gitlab` | Convert Skylos dead code reports to GitLab Code Quality format |
