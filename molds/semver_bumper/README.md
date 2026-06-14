# semver_bumper

Calculate the next semantic version from commits since the last tag.

## Usage

### From JSON commits

```bash
fimod s -i commits.json -m @semver_bumper --arg current=v0.5.0
```

Input:

```json
[
  {"subject": "feat(dockerfile): add shell hooks"},
  {"subject": "fix(poetry_migrate): preserve URL dependencies"},
  {"subject": "docs: refresh examples"}
]
```

Output:

```json
{
  "current": "0.5.0",
  "current_tag": "v0.5.0",
  "next": "0.6.0",
  "next_tag": "v0.6.0",
  "bump": "minor"
}
```

### From git history

Find the latest stable tag, accepting both `v0.5.0` and `0.5.0` tag styles:

```bash
last_tag=$(git describe --tags --abbrev=0 \
  --match 'v[0-9]*' \
  --match '[0-9]*' \
  --exclude '*-*')
```

Pass commits since that tag to the mold:

```bash
git log --format='%H%x1f%s%x1f%b%x1e' "$last_tag"..HEAD \
  | fimod s --input-format txt -m @semver_bumper --arg current="$last_tag"
```

The `%x1f` and `%x1e` separators preserve commit subjects and bodies, including
`BREAKING CHANGE:` footers.

### Print only the next tag

```bash
git log --format='%H%x1f%s%x1f%b%x1e' "$last_tag"..HEAD \
  | fimod s --input-format txt -m @semver_bumper \
      --arg current="$last_tag" \
      --arg output=tag
```

## Args

| Arg | Required | Description |
|-----|----------|-------------|
| `current` | Yes, unless present in JSON input | Current stable version or tag. Accepts `v0.5.0` and `0.5.0`. |
| `output` | No | Output mode: `json`, `version`, `tag`, or `bump` (default: `json`). |
| `tag-prefix` | No | Prefix for `next_tag`: `auto`, `v`, or `none` (default: `auto`). |
| `on-none` | No | Behavior when no version-worthy commit is found: `keep` or `fail` (default: `keep`). |

## Rules

The mold follows the Fimod-Powered release convention:

| Commit | Bump |
|--------|------|
| `feat` | minor |
| `fix`, `perf` | patch |
| `docs`, `refactor`, `chore`, `test`, `style`, `ci`, `build` | none |
| `type!:` or `BREAKING CHANGE:` footer | minor before `1.0.0`, major from `1.0.0` onward |

Unknown commit types are treated as `none`.

## Version and tag handling

`current` accepts a plain SemVer version or a tag with a leading `v`:

- `0.5.0`
- `v0.5.0`

The numeric calculation always uses the normalized version (`0.5.0`). By
default, `next_tag` preserves the input prefix:

| Current | Next version | Next tag |
|---------|--------------|----------|
| `v0.5.0` | `0.6.0` | `v0.6.0` |
| `0.5.0` | `0.6.0` | `0.6.0` |

Use `--arg tag-prefix=v` or `--arg tag-prefix=none` to force the output style.

## Mold directives

- `output-format=json` - return structured bump details by default
