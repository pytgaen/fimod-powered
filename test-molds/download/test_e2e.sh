#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
MOLD="$ROOT_DIR/molds/download/download.py"
PORT_FILE="$(mktemp)"
WORK_DIR="$(mktemp -d)"
SERVER_PID=""
EXPECTED_CONTENT="hello from fimod download test"

cleanup() {
    [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null || true
    rm -f "$PORT_FILE"
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

uv run "$SCRIPT_DIR/_server.py" "$PORT_FILE" "$EXPECTED_CONTENT" &
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

echo "download e2e tests (server on :$PORT)"

cd "$WORK_DIR"

# Test 1: download with --arg out= writes correct content
fimod s -i "http://127.0.0.1:$PORT/data/report.csv" -m "$MOLD" --arg out=myfile.bin 2>/dev/null
check "custom filename content" "$EXPECTED_CONTENT" "$(cat "$WORK_DIR/myfile.bin")"

# Test 2: verify the file is created with the requested name
check "custom filename exists" "myfile.bin" "$(ls "$WORK_DIR")"

# Test 3: download without --arg out= → filename guessed from URL
rm -f "$WORK_DIR"/*
fimod s -i "http://127.0.0.1:$PORT/data/report.csv" -m "$MOLD" 2>/dev/null
check "auto filename exists" "report.csv" "$(ls "$WORK_DIR")"
check "auto filename content" "$EXPECTED_CONTENT" "$(cat "$WORK_DIR/report.csv")"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
