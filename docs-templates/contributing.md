# Contributing

We welcome contributions! This page covers the workflow for proposing a mold to fimod-powered. For how to write a mold, see [Authoring a mold](authoring.md).

## Setup

```bash
git clone https://github.com/pytgaen/fimod-powered.git
cd fimod-powered
```

## Propose a mold

### 1. Create the mold

Follow the [Authoring guide](authoring.md) to create your mold in `molds/my_mold/` and its tests in `test-molds/my_mold/`.

### 2. Rebuild the catalog

```bash
fimod registry build-catalog ./molds
```

The catalog (`molds/catalog.toml`) is the index that allows remote registries to list and resolve molds without cloning the entire repo. Commit the updated catalog with your changes — CI will verify it's in sync.

### 3. Run tests and submit

Every mold **must** include tests and a `README.md` — pull requests without them will be rejected.

```bash
# Test your mold
fimod mold test ./test-molds/my_mold

# Test everything
fimod mold test ./test-molds
```

Then open a pull request on [GitHub](https://github.com/pytgaen/fimod-powered).

## Pre-commit hooks (optional but recommended)

The repository includes pre-commit hooks that check for trailing whitespace, valid TOML/YAML/JSON, and merge conflicts. CI runs the same checks, so installing them locally catches issues early.

```bash
# Install
pre-commit install

# Run manually
pre-commit run --all-files
```
