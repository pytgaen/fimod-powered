#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
MOLD="$ROOT_DIR/molds/gh_latest/gh_latest.py"
PORT_FILE1="$(mktemp)"
PORT_FILE2="$(mktemp)"
SERVER_PIDS=()
TAG="v3.8.1"
TAG_NO_V="2.0.0"

cleanup() {
    for pid in "${SERVER_PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    rm -f "$PORT_FILE1" "$PORT_FILE2"
}
trap cleanup EXIT

wait_for_port() {
    local pf="$1"
    for _ in $(seq 1 30); do
        [ -s "$pf" ] && break
        sleep 0.1
    done
    cat "$pf"
}

# Server 1: tag with v prefix
uv run "$SCRIPT_DIR/_server.py" "$PORT_FILE1" "$TAG" &
SERVER_PIDS+=($!)

# Server 2: tag without v prefix
uv run "$SCRIPT_DIR/_server.py" "$PORT_FILE2" "$TAG_NO_V" &
SERVER_PIDS+=($!)

PORT1=$(wait_for_port "$PORT_FILE1")
PORT2=$(wait_for_port "$PORT_FILE2")

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

check_fail() {
    local label="$1"
    shift
    if ! "$@" >/dev/null 2>&1; then
        echo "  PASS: $label"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $label (expected non-zero exit)"
        FAIL=$((FAIL + 1))
    fi
}

echo "gh_latest e2e tests (servers on :$PORT1, :$PORT2)"

# Test 1: basic tag extraction
out=$(fimod s -i "http://127.0.0.1:$PORT1/releases/latest" -m "$MOLD" 2>/dev/null)
check "basic tag" "$TAG" "$out"

# Test 2: asset URL with {version} placeholder
out=$(fimod s -i "http://127.0.0.1:$PORT1/releases/latest" -m "$MOLD" \
    --arg repo=org/repo --arg "asset=app-{version}-linux.tar.gz" 2>/dev/null)
check "asset URL" "https://github.com/org/repo/releases/download/$TAG/app-3.8.1-linux.tar.gz" "$out"

# Test 3: asset URL with {tag} placeholder
out=$(fimod s -i "http://127.0.0.1:$PORT1/releases/latest" -m "$MOLD" \
    --arg repo=org/repo --arg "asset=app-{tag}.zip" 2>/dev/null)
check "tag placeholder" "https://github.com/org/repo/releases/download/$TAG/app-$TAG.zip" "$out"

# Test 4: no release (location header absent) — should fail
check_fail "no release" \
    fimod s -i "http://127.0.0.1:$PORT1/no-release/releases/latest" -m "$MOLD"

# Test 5: tag without v prefix
out=$(fimod s -i "http://127.0.0.1:$PORT2/releases/latest" -m "$MOLD" 2>/dev/null)
check "tag without v prefix" "$TAG_NO_V" "$out"

# Test 6: tag without v prefix — {version} equals {tag}
out=$(fimod s -i "http://127.0.0.1:$PORT2/releases/latest" -m "$MOLD" \
    --arg repo=org/repo --arg "asset=app-{version}-linux.tar.gz" 2>/dev/null)
check "no-v asset URL" "https://github.com/org/repo/releases/download/$TAG_NO_V/app-$TAG_NO_V-linux.tar.gz" "$out"

# Test 7: repo without asset — returns tag only
out=$(fimod s -i "http://127.0.0.1:$PORT1/releases/latest" -m "$MOLD" \
    --arg repo=org/repo 2>/dev/null)
check "repo without asset" "$TAG" "$out"

# Test 8: asset without repo — returns tag only
out=$(fimod s -i "http://127.0.0.1:$PORT1/releases/latest" -m "$MOLD" \
    --arg "asset=app-{version}.tar.gz" 2>/dev/null)
check "asset without repo" "$TAG" "$out"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
