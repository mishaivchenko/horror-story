#!/usr/bin/env bash
# smoke.sh — drive horror-story CLI and report pass/fail
# Run from the repo root: bash .claude/skills/run-horror-story/smoke.sh
set -euo pipefail

VENV=.venv/bin/activate
STORY=tests/fixtures/mini-story.txt
OUT=/tmp/hs-smoke-$$

if [ ! -f "$VENV" ]; then
  echo "ERROR: virtualenv not found at $VENV — run: python3 -m venv .venv && pip install -e ." >&2
  exit 1
fi

source "$VENV"

echo "=== horror-story smoke test ==="

echo "[1/4] version"
python -m horror_story --version

echo "[2/4] validate-schemas"
python -m horror_story validate-schemas

echo "[3/4] run --dry-run"
python -m horror_story run --story "$STORY" --out "$OUT" --seed 42 --dry-run

echo "[4/4] validate (stub)"
python -m horror_story validate --run-dir "$OUT"

echo ""
echo "=== ALL PASSED ==="
