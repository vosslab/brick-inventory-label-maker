#!/usr/bin/env bash
# Strict mode minus nounset: source_me.sh pulls ~/.bashrc which may reference unset PS1.
set -eo pipefail
cd "$(dirname "$0")"

# Build frontend bundle.
bash build_frontend.sh

# Source repo env (PYTHONPATH=vendor/, PYTHONUNBUFFERED, etc.).
# shellcheck disable=SC1091
source source_me.sh

# Pick a free random port in 8000-9999 (try up to 20 candidates).
pick_port() {
	for _ in $(seq 1 20); do
		local candidate=$((8000 + RANDOM % 2000))
		if ! lsof -iTCP:"$candidate" -sTCP:LISTEN -n -P >/dev/null 2>&1; then
			echo "$candidate"
			return 0
		fi
	done
	echo "could not find free port in 8000-9999" >&2
	return 1
}
PORT="$(pick_port)"
URL="http://127.0.0.1:$PORT"
echo "serving on $URL"

# macOS: open default browser once uvicorn has bound the port.
if [ "$(uname -s)" = "Darwin" ]; then
	(
		for _ in $(seq 1 30); do
			if lsof -iTCP:"$PORT" -sTCP:LISTEN -n -P >/dev/null 2>&1; then
				open "$URL"
				exit 0
			fi
			sleep 0.3
		done
	) &
fi

# Run FastAPI app via uvicorn on loopback.
exec python3 -m uvicorn backend.app:app --host 127.0.0.1 --port "$PORT" --reload
