#!/usr/bin/env bash
# Start the application. Usage: ./run.sh [port]
set -euo pipefail
cd "$(dirname "$0")"
PORT="${1:-8000}"
[ -f .env ] && set -a && . ./.env && set +a
echo "Capital Markets Agentic Capstone -> http://127.0.0.1:${PORT}"
echo "No API key needed. For a real model, open the console and click 'Model & key'."
exec python3 -m uvicorn app.api.main:app --host 127.0.0.1 --port "${PORT}" --reload
