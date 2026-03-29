# Contributing

## Adding a new mold

### 1. Create the mold

```
molds/my_mold/
├── my_mold.py             # Must export transform(data, args, env, headers)
├── templates/             # Jinja2 templates (optional)
│   └── template.j2
└── README.md              # Usage, input format, examples
```

The mold filename must match the directory name.

### 2. Mold conventions

- **Docstring**: The module-level docstring (`"""..."""`) is the description shown by `fimod mold list`.
- **Directives**: Declare output format, input format, and arguments with `# fimod:` comments at the top of the file.
- **Error handling**: Use `msg_warn()` for non-fatal issues, `gk_fail()` for validation failures.

```python
"""
Short description of what the mold does.

Usage:
    fimod s -i input.json -m @my_mold --arg foo=bar
"""
# fimod: output-format=json
# fimod: arg=foo  Description of the foo argument

def transform(data, args, env, headers):
    # ...
    return result
```

### 3. Add tests

Create fixture-based tests in `test-molds/my_mold/`:

```
test-molds/my_mold/
├── basic.input.json       # Input file
├── basic.expected.json    # Expected output
└── basic.run-test.toml    # Optional: args, env, exit code
```

**Test config format** (`*.run-test.toml`):

```toml
[args]
foo = "bar"

[env_vars]
MY_VAR = "value"

output_format = "json"
exit_code = 0
# skip = true   # uncomment to disable this test case
```

### 4. Update the catalog

After adding or modifying a mold, regenerate `molds/catalog.toml` so the registry stays up-to-date:

```bash
fimod registry build-catalog ./molds
```

Commit the updated `molds/catalog.toml` along with your changes. CI will verify the catalog is in sync — the PR check will fail if it's outdated.

### 5. Run tests

```bash
# Test your mold
fimod mold test ./test-molds/my_mold

# Test everything
fimod mold test ./test-molds
```

## Pre-commit hooks

Install hooks before committing:

```bash
pre-commit install
```

Run manually:

```bash
pre-commit run --all-files
```
