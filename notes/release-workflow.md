# Release Workflow

This document describes the Fimod-Powered release cycle: conventions, tooling, invariants. It targets maintainers and contributors proposing PRs or cutting versions.

## TL;DR

1. Work happens on a branch, proposed via PR, squash-merged into `main`.
2. PR title + body are written as conventional commits.
3. A release is a `chore(release): X.Y.Z` commit **directly on main** (no PR), with a tag `vX.Y.Z`.
4. A public prerelease (`rc.N`) ships a staging tag that is **not marked "latest"** on GitHub — useful for opt-in validation before a stable X.Y.0.

---

## Commit conventions

Fimod-Powered follows [Conventional Commits](https://www.conventionalcommits.org/).

**Recognized types** (semver impact):

| Type | Bump |
|---|---|
| `feat` | minor |
| `fix`, `perf` | patch |
| `docs`, `refactor`, `chore`, `test`, `style`, `ci`, `build` | — |

**BREAKING CHANGE** (via `!` in the type or `BREAKING CHANGE:` footer):

- In 0.x.y (pre-1.0): bump **minor** (0.2.x → 0.3.0). Project convention, compatible with [semver §4](https://semver.org/#spec-item-4).
- From 1.0.0 onwards: bump **major**.

Examples:

```
feat(dockerfile): add pipefail option
fix(poetry_migrate): preserve URL deps for uv target
perf(html_report): lazy-render large tables
chore(release): 0.3.0
```

---

## How the CHANGELOG is built

Fimod-Powered uses **squash & merge** on GitHub. Unlike fimod (which uses `git-cliff`), the CHANGELOG is **hand-written** during phase 2, sourced from a transient notes file rather than commit metadata.

### Source: `notes/release-vX.Y.Z.md`

During feature work (phase 1), every PR contributing to upcoming version `X.Y.Z` appends user-facing entries to `notes/release-vX.Y.Z.md`. This file is reviewed as part of the PR.

Format: sections grouped **by mold**, matching the final CHANGELOG structure.

```markdown
# Release notes — 0.3.0

## dockerfile
- Configurable uv install method
- `pipefail` option for stricter shell errors

## poetry_migrate
- Index strategy argument for uv target

## Tooling
- Pre-commit hook updates

## Other
- License updated to Apache 2.0
```

### Consumption: phase 2

At release time, `notes/release-vX.Y.Z.md` is transformed into a CHANGELOG section (rewrite `## mold` → `### mold`, prepend `## X.Y.Z — YYYY-MM-DD`), and the source file is **deleted** in the same `chore(release):` commit.

### Grouping by mold (not by type)

Users care about what changed in *the mold they use*. `### dockerfile` and `### poetry_migrate` subsections are more useful than a global `### Features` / `### Bug Fixes` split. Meta sections: `### Tooling` (CI, pre-commit), `### Docs` (non-mold docs), `### Other` (license, meta).

### Editorial highlights (optional)

Alongside per-mold bullets, `notes/release-vX.Y.Z.md` may include a top-level `## Highlights` section — short editorial prose (emojis allowed) capturing *what matters* in the release. Example:

```markdown
## Highlights

- 🏗️ **Dockerfile hooks restructured** — explicit `builder` / `runtime` stages with 6 injection points.
- 📦 **Poetry → uv enriched** — PEP 508 markers, multi-constraints, URL / git deps.
```

Phase 2 extracts this block and injects it as a `### Highlights` subsection placed first in the `## X.Y.Z` CHANGELOG entry, before the per-mold subsections. The GitHub Release notes (optional step 2.10) receive the same content.

---

## Release cycle

### Phase 1 — Work (iterative, via PR)

1. Create a branch (`feat/...`, `fix/...`, `release/X.Y.Z`).
2. Commit normally (intra-branch commits are squashed at merge time).
3. **Never** modify `CHANGELOG.md` in this phase.
4. **Append to `notes/release-vX.Y.Z.md`** with a user-facing summary grouped by mold.
5. If any mold was changed, rebuild `molds/catalog.toml` via `fimod registry build-catalog ./molds` and commit the result (CI enforces freshness via the `catalog-check` job).
6. Run `task test:all` locally.
7. Open the PR with a conventional title + body.
8. Wait for green CI.
9. Squash-merge (GitHub option *"Default to pull request title and description"*).

### Phase 2 — Release (direct on main)

1. Switch to `main`, `git pull --ff-only` (linear history required).
2. Verify working tree clean.
3. Analyze commits since last stable tag; determine bump (patch/minor/major per rules above).
4. Consume `notes/release-vX.Y.Z.md` into a CHANGELOG section inserted at the top (after `# Changelog`). If the notes contain a `## Highlights` block, place it first as a `### Highlights` subsection.
5. If any mold was modified since the last release, ensure `molds/catalog.toml` is up to date.
6. Stage EXACTLY these files:
   - `CHANGELOG.md` (modified)
   - `notes/release-vX.Y.Z.md` (deleted)
   - `molds/catalog.toml` (modified, only if molds changed)
7. Commit `chore(release): X.Y.Z` and tag `vX.Y.Z`.
8. Push with confirmation: `git push && git push origin vX.Y.Z`.
9. Optional: create a GitHub Release with the CHANGELOG section as notes.

**Note:** Fimod-Powered has **no versioned file** (no `Cargo.toml`, no `pyproject.toml`). The version exists solely as a CHANGELOG section and a git tag.

---

## Public prerelease (rc.N)

Used to ship a **staging** tag that is **not marked as "latest"** on GitHub. Useful for:

- Opt-in testing of a mold with breaking changes
- Pre-announcement before a stable X.Y.0
- Validating tooling around a specific mold version

### Key differences vs release

|  | Prerelease (`vX.Y.Z-rc.N`) | Release (`vX.Y.Z`) |
|---|---|---|
| **Goal** | Staging / opt-in | Official publication |
| **CHANGELOG.md** | Not modified | New section prepended |
| **Commit** | None (tag only) | `chore(release): X.Y.Z` |
| **Tag** | `vX.Y.Z-rc.N` | `vX.Y.Z` |
| **GitHub Release** | `--prerelease` flag | Stable |
| **Branch** | Any (main or feature) | `main` only |
| **Notes source** | `notes/release-vX.Y.Z.md` left intact | Consumed & deleted |
| **Latest indicator** | Not "latest" | Marked "latest" |

### Prerelease cycle

1. Working tree clean (tag is placed on current HEAD — no commit, no file change).
2. Determine target version `X.Y.Z` and `rc.N` number (auto-increment via `git tag -l "vX.Y.Z-rc.*"`).
3. Tag: `git tag vX.Y.Z-rc.N`.
4. Push: `git push origin vX.Y.Z-rc.N`.
5. Create GitHub Release with `--prerelease`:
   ```bash
   gh release create vX.Y.Z-rc.N \
     --prerelease \
     --title "vX.Y.Z-rc.N" \
     --notes-file notes/release-vX.Y.Z.md
   ```

**No commit, no file change** — the tag lands on an unchanged HEAD. `CHANGELOG.md` stays untouched; `notes/release-vX.Y.Z.md` stays intact (it will be consumed by the final `chore(release): X.Y.Z` commit).

### rc numbering convention

- `rc.N` with **point** separator, never dash (`rc.1`, `rc.2`, ...) — compliant with [semver §9](https://semver.org/#spec-item-9).
- Independent numbering per target version: `0.3.0-rc.1`, `0.3.0-rc.2`, then `0.3.0`.
- An rc can live on any branch (no need to merge into main first).

---

## Critical invariants

Must be respected — violating any of these corrupts the CHANGELOG, the history, or the public GitHub state:

1. `CHANGELOG.md` NEVER appears in a non-`chore(release):` commit. Any accidental phase-1 edit must be relocated to `notes/release-vX.Y.Z.md` or stashed until phase 2.
2. The `chore(release):` commit contains EXACTLY these files:
   - `CHANGELOG.md` (modified)
   - `notes/release-vX.Y.Z.md` (deleted)
   - Optionally `molds/catalog.toml` (modified) if molds were changed

   Any other file → STOP.
3. No tag is created before the work PR is merged into `main`.
4. No direct commit on `main` during phase 1 — everything goes through a PR. The `chore(release):` commit is the only exception.
5. Release commit subject EXACTLY `chore(release): X.Y.Z` — never `feat:`, `fix:`, etc. No body, no `Co-Authored-By`.
6. Squash-merge only — no merge commits (linear history required).
7. Prerelease tags: `vX.Y.Z-rc.N` with point, never dash. A prerelease **must not modify any tracked file**.
8. GitHub Prereleases **must** use `--prerelease`; without it, the rc tag would displace the current "latest" on the Releases page.

---

## Tooling

- **GitHub squash-merge** — enable *"Default to pull request title and description"* in repo settings so the PR body makes it into the commit on main.
- **`task test:all`** — runs `fimod mold test` across every mold. Required to pass before opening a PR.
- **`fimod registry build-catalog ./molds`** — rebuilds `molds/catalog.toml`. Run after changing any mold's metadata (arg docs, descriptions, format directives). CI `catalog-check` fails on stale catalogs.
- **`prek -a`** — runs all pre-commit hooks.

---

## Reference files

- `CHANGELOG.md` — public history, hand-written, grouped by mold.
- `notes/release-vX.Y.Z.md` — transient release notes, consumed and deleted at release time.
- `molds/catalog.toml` — mold catalog (rebuilt via `fimod registry build-catalog`).
- `.github/workflows/ci.yml` — test + catalog + pre-commit pipeline.
- `.claude/skills/release-workflow/SKILL.md` — skill orchestrating the full flow.
- `.claude/skills/prerelease-workflow/SKILL.md` — skill for tagging rc.N + GitHub Prerelease.
