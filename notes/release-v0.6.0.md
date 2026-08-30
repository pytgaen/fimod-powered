# Release notes — 0.6.0

## dockerfile
- New `skip_builder_copy_all` option (uv / Poetry multistage): omits the builder `COPY . .` and installs third-party dependencies only, for projects whose runtime stage runs from copied sources.
- Poetry multistage builds now split the installation in two: `--only main --no-root` before the source copy, then `--only-root` after it. Dependency layers stay cached when only the source tree changes.
- `CONVERT_PROMPT.md`: new `.dockerignore` pre-conversion check — the build context is validated against the generated `COPY` instructions, with a separate stack-aware `.dockerignore` proposal when needed.
