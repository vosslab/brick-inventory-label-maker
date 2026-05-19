#!/usr/bin/env bash
# Bring up the Podman-compose stack on a random free port in 8000-9999.
# On macOS, opens the default browser once the port binds.
set -eo pipefail
cd "$(dirname "$0")"

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

export LABELS_PORT="$(pick_port)"
URL="http://127.0.0.1:$LABELS_PORT"
echo "serving on $URL"

# Start stack detached so we can wait for the port and open the browser.
podman compose up -d --build

# Wait for port to bind.
if [ "$(uname -s)" = "Darwin" ]; then
	for _ in $(seq 1 60); do
		if lsof -iTCP:"$LABELS_PORT" -sTCP:LISTEN -n -P >/dev/null 2>&1; then
			open "$URL"
			break
		fi
		sleep 0.5
	done
fi

# Stream logs in the foreground; Ctrl-C stops the stream but leaves the stack up.
podman compose logs -f
