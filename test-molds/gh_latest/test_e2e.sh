#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
MOLD="$ROOT_DIR/molds/gh_latest/gh_latest.py"
PORT_FILE="$(mktemp)"
SERVER_PID=""
TAG="v3.8.1"

cleanup() {
    [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null || true
    rm -f "$PORT_FILE"
}
trap cleanup EXIT

uv run "$SCRIPT_DIR/_server.py" "$PORT_FILE" "$TAG" &
SERVER_PID=$!

for _ in $(seq 1 30); do
    [ -s "$PORT_FILE" ] && break
    sleep 0.1
done
PORT=$(cat "$PORT_FILE")

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

echo "gh_latest e2e tests (server on :$PORT)"

# Test 1: basic tag extraction
out=$(fimod s -i "http://127.0.0.1:$PORT/releases/latest" -m "$MOLD" 2>/dev/null)
check "basic tag" "$TAG" "$out"

# Test 2: asset URL with {version} placeholder
out=$(fimod s -i "http://127.0.0.1:$PORT/releases/latest" -m "$MOLD" \
    --arg repo=org/repo --arg "asset=app-{version}-linux.tar.gz" 2>/dev/null)
check "asset URL" "https://github.com/org/repo/releases/download/$TAG/app-3.8.1-linux.tar.gz" "$out"

# Test 3: asset URL with {tag} placeholder
out=$(fimod s -i "http://127.0.0.1:$PORT/releases/latest" -m "$MOLD" \
    --arg repo=org/repo --arg "asset=app-{tag}.zip" 2>/dev/null)
check "tag placeholder" "https://github.com/org/repo/releases/download/$TAG/app-$TAG.zip" "$out"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
