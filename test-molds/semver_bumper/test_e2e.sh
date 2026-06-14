#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
MOLD="$ROOT_DIR/molds/semver_bumper/semver_bumper.py"
WORK_DIR="$(mktemp -d)"

cleanup() {
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

PASS=0
FAIL=0

check() {
    local label="$1" expected="$2" actual="$3"
    if [ "$actual" = "$expected" ]; then
        echo "  PASS: $label"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $label"
        echo "    expected: $expected"
        echo "    actual:   $actual"
        FAIL=$((FAIL + 1))
    fi
}

new_repo() {
    local name="$1"
    local repo="$WORK_DIR/$name"
    git init -q "$repo"
    git -C "$repo" config user.email "fimod-powered@example.invalid"
    git -C "$repo" config user.name "Fimod Powered Tests"
    git -C "$repo" config commit.gpgsign false
    git -C "$repo" config tag.gpgsign false
    printf '%s\n' "initial" > "$repo/file.txt"
    git -C "$repo" add file.txt
    git -C "$repo" commit -q -m "chore: initial"
    printf '%s\n' "$repo"
}

commit_change() {
    local repo="$1"
    local message="$2"
    printf '%s\n' "$message" >> "$repo/file.txt"
    git -C "$repo" add file.txt
    git -C "$repo" commit -q -m "$message"
}

commit_breaking_change() {
    local repo="$1"
    printf '%s\n' "breaking" >> "$repo/file.txt"
    git -C "$repo" add file.txt
    git -C "$repo" commit -q -m "refactor(api): simplify config" -m "BREAKING CHANGE: remove legacy option"
}

latest_stable_tag() {
    local repo="$1"
    git -C "$repo" describe --tags --abbrev=0 \
        --match 'v[0-9]*' \
        --match '[0-9]*' \
        --exclude '*-*'
}

run_bumper() {
    local repo="$1"
    local current="$2"
    shift 2
    git -C "$repo" log --format='%H%x1f%s%x1f%b%x1e' "$current"..HEAD \
        | fimod s --input-format txt -m "$MOLD" --arg current="$current" "$@"
}

echo "semver_bumper git e2e tests"

# Test 1: v-prefixed tag is discovered and preserved.
repo=$(new_repo "v-prefix")
git -C "$repo" tag v0.5.0
commit_change "$repo" "docs: refresh README"
commit_change "$repo" "fix(poetry_migrate): preserve URL dependencies"
commit_change "$repo" "feat(dockerfile): add shell hooks"
last_tag=$(latest_stable_tag "$repo")
check "discover v-prefixed tag" "v0.5.0" "$last_tag"
out=$(run_bumper "$repo" "$last_tag" --arg output=tag)
check "v-prefixed next tag" "v0.6.0" "$out"

# Test 2: unprefixed tag is discovered and preserved.
repo=$(new_repo "no-prefix")
git -C "$repo" tag 0.5.0
commit_change "$repo" "fix(download): report HTTP errors"
last_tag=$(latest_stable_tag "$repo")
check "discover unprefixed tag" "0.5.0" "$last_tag"
out=$(run_bumper "$repo" "$last_tag" --arg output=tag)
check "unprefixed next tag" "0.5.1" "$out"

# Test 3: tag-prefix can force v output for unprefixed input.
out=$(run_bumper "$repo" "$last_tag" --arg output=tag --arg tag-prefix=v)
check "force v prefix" "v0.5.1" "$out"

# Test 4: BREAKING CHANGE footer is preserved through real git log body parsing.
repo=$(new_repo "breaking")
git -C "$repo" tag 1.2.3
commit_breaking_change "$repo"
last_tag=$(latest_stable_tag "$repo")
out=$(run_bumper "$repo" "$last_tag" --arg output=tag)
check "breaking footer major bump" "2.0.0" "$out"

# Test 5: prerelease tags are ignored when discovering the latest stable tag.
repo=$(new_repo "skip-rc")
git -C "$repo" tag v0.5.0
commit_change "$repo" "feat(dockerfile): add shell hooks"
git -C "$repo" tag v0.6.0-rc.1
commit_change "$repo" "fix(dockerfile): refine generated shell"
last_tag=$(latest_stable_tag "$repo")
check "ignore prerelease tag" "v0.5.0" "$last_tag"
out=$(run_bumper "$repo" "$last_tag" --arg output=tag)
check "next tag after prerelease" "v0.6.0" "$out"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
