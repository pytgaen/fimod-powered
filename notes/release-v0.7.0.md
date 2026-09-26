# Release notes — 0.7.0

## poetry_migrate

- Use native Python `re` for Python version constraint normalization, removing the dependency on legacy regex helpers. Requires Fimod with native `import re` support.
- Link the full migration workflow from the mold README to its source on GitHub.

## Docs

- Correct mold test commands and document the local HTTP test suites.
- Document extensible transform signatures and native Python replacements for deprecated Fimod built-ins.

## Tooling

- Share concise repository instructions through `AGENTS.md`, imported by `CLAUDE.md`.
