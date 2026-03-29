# Authoring a mold

This page covers what's specific to the fimod-powered registry. For writing molds in general, see the official fimod documentation:

- :octicons-book-24: [Authoring molds guide](https://pytgaen.github.io/fimod/guides/authoring-molds/)
- :octicons-list-unordered-24: [Reference](https://pytgaen.github.io/fimod/reference/formats/)

## Registry structure

Each mold in fimod-powered follows this layout:

```
molds/my_mold/
├── my_mold.py             # Must export transform()
├── templates/             # Jinja2 templates (optional)
│   └── template.j2
└── README.md              # Usage, examples, args documentation

test-molds/my_mold/
├── basic.input.json       # Input file
├── basic.expected.json    # Expected output
└── basic.run-test.toml    # Optional test config
```

The mold filename **must** match the directory name.

## README.md

Every mold must include a `README.md`. This is what generates the mold's documentation page on this site. Use the existing molds as reference — [`dockerfile`](molds/dockerfile.md) and [`poetry_migrate`](molds/poetry_migrate.md) are good examples.

A typical README includes:

- **Usage** — one or two `fimod s` command examples
- **Args** — table of `--arg` options (if any)
- **How it works** — brief explanation of the approach

## Conventions

- The module docstring (`"""..."""`) is shown by `fimod mold list` — keep it to one line
- Use `msg_warn()` for non-fatal issues, `gk_fail()` for validation failures
- Prefer `def transform(data, args, **_):` — only declare `env`/`headers` if you use them
