# Getting started

## Install fimod

### One-liner

```bash
curl -fsSL https://raw.githubusercontent.com/pytgaen/fimod/main/install.sh | sh
```

### Other methods

See the [fimod Quick Start guide](https://pytgaen.github.io/fimod/guides/quick-start/) for all installation options.

## Add the fimod-powered registry

### Via `fimod registry setup` (recommended)

```bash
fimod registry setup
```

The interactive setup will propose to install **fimod-powered**. Accept, and you're done.

### From GitHub

```bash
fimod registry add fimod-powered https://github.com/pytgaen/fimod-powered/tree/main/molds
```

### From a local clone

```bash
git clone https://github.com/pytgaen/fimod-powered.git
fimod registry add fimod-powered "$(pwd)/fimod-powered/molds"
```

!!! warning
    The path must be absolute. Using a relative path will break if you run fimod from a different directory.

## Set the priority

Give `fimod-powered` the highest priority so its molds are resolved first:

```bash
fimod registry set-priority fimod-powered 10
```

!!! tip
    When multiple registries are configured, fimod resolves short names (e.g. `@dockerfile`) from the highest-priority registry first. Setting priority 1 ensures fimod-powered wins, so you can write `@dockerfile` instead of `@fimod-powered/dockerfile`.

## Use a mold

```bash
# Generate a Dockerfile from a descriptor
fimod s -i app.json -m @dockerfile -o Dockerfile

# Pass arguments
fimod s -i pyproject.toml -m @poetry_migrate --arg target=uv

# Preview the output (stdout)
fimod s -i data.csv -m @html_report
```

## List available molds

```bash
fimod mold list fimod-powered
```

## Troubleshooting

### Mold not found

```
Error: mold "dockerfile" not found in any registry
```

Check that the registry is properly added and has the highest priority:

```bash
fimod registry list
fimod registry set-priority fimod-powered 1
```

If you used a local clone, make sure the path is absolute (see [From a local clone](#from-a-local-clone) above).

### Unknown mold name

Use `fimod mold list fimod-powered` to see all available molds. Mold names use underscores, not dashes (e.g. `@poetry_migrate`, not `@poetry-migrate`).

### Input format errors

If fimod can't parse your input file, check the expected format on the mold's documentation page. Some molds (like `@download` and `@gh_latest`) expect a URL as input, not a local file path.
