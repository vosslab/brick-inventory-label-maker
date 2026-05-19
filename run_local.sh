#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Build frontend bundle.
bash build_frontend.sh

# Source repo env (PYTHONPATH=vendor/, PYTHONUNBUFFERED, etc.).
# shellcheck disable=SC1091
source source_me.sh

# Run FastAPI app via uvicorn on loopback.
exec python3 -m uvicorn backend.app:app --host 127.0.0.1 --port 8080 --reload
