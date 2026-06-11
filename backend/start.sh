#!/usr/bin/env bash
set -euo pipefail

export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-0}"

echo "[bohumfit] ensuring Playwright Chromium is installed (PLAYWRIGHT_BROWSERS_PATH=${PLAYWRIGHT_BROWSERS_PATH})"
python -m playwright install chromium

echo "[bohumfit] starting API server"
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
