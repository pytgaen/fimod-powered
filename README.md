# fimod-powered

A curated collection of production-ready [fimod](https://github.com/pytgaen/fimod) molds — Python transformation scripts that convert structured data into useful outputs.

No system Python required: fimod embeds its own runtime ([Monty](https://github.com/pydantic/monty)) in a single ~2.3 MB binary.

## Available molds

| Mold | Description |
|------|-------------|
| [`dockerfile`](molds/dockerfile/) | Generate production Dockerfiles from JSON/YAML descriptors (Python + Node.js, multistage builds) |
| [`html_report`](molds/html_report/) | Convert JSON/CSV data to standalone HTML reports with sortable tables |
| [`poetry_migrate`](molds/poetry_migrate/) | Migrate Poetry `pyproject.toml` to Poetry 2 or uv (PEP 621) |
| [`download`](molds/download/) | Download files from URLs (wget-like) |
| [`gh_latest`](molds/gh_latest/) | Get latest GitHub release tag or download URL |
| [`skylos_to_gitlab`](molds/skylos_to_gitlab/) | Convert Skylos dead code reports to GitLab Code Quality format |

## Quick start

### Install fimod (>= 0.3.0)

See the [fimod installation guide](https://github.com/pytgaen/fimod#installation).

### Use a mold

```bash
# From a local clone
fimod s -i input.yaml -m molds/dockerfile/dockerfile.py -o Dockerfile

# From a registry (once published)
fimod s -i input.yaml -m @dockerfile -o Dockerfile
```

### Pass arguments

```bash
fimod s -i pyproject.toml -m @poetry_migrate --arg target=uv --arg build=hatchling
```

## Use as a registry

You can register this repository as a fimod mold registry to use its molds directly by name.

### From a remote URL (GitHub)

```bash
fimod registry add fimod-powered https://github.com/pytgaen/fimod-powered
```

### From a local clone

```bash
git clone https://github.com/pytgaen/fimod-powered.git
fimod registry add fimod-powered ./fimod-powered/molds
```

### Browse and use molds

```bash
# List available molds
fimod mold list fimod-powered

# Use a mold by registry-qualified name
fimod s -i input.yaml -m @fimod-powered/dockerfile -o Dockerfile

# If set as default registry, the prefix is optional
fimod registry set-default fimod-powered
fimod s -i input.yaml -m @dockerfile -o Dockerfile
```

## Testing

Each mold has fixture-based tests in `test-molds/`.

```bash
# Run all mold tests
fimod mold test ./test-molds

# Run tests for a single mold
fimod mold test ./test-molds/dockerfile
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on the test fixture format.

## License

[Apache-2.0](LICENSE.txt)
