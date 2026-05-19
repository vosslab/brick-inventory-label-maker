#!/usr/bin/env bash
# E2E smoke test: validates container build, uvicorn boot, frontend mount, route wiring.
# Expects HTTP 400 with credentials_missing error (validates error path without live network).
set -euo pipefail
cd "$(dirname "$0")/../.."

# Bring stack up in detached mode.
podman compose up -d --build

# Wait for health endpoint.
for i in 1 2 3 4 5 6 7 8 9 10; do
	if curl -sf http://127.0.0.1:8080/api/health >/dev/null 2>&1; then
		break
	fi
	sleep 1
done

# Sanity: health responds.
if ! curl -sf http://127.0.0.1:8080/api/health 2>/dev/null | grep -q '"ok": true'; then
	echo "health check failed"
	podman compose logs
	podman compose down
	exit 1
fi

# POST a minimal request without credentials; expect HTTP 400 with credentials_missing.
# This validates: container builds, uvicorn boots, frontend dist is mounted, route is wired,
# error path returns JSON properly.
OUT=$(mktemp)
STATUS=$(curl -s -w '%{http_code}' -X POST http://127.0.0.1:8080/api/labels/minifigs \
	-H 'Content-Type: application/json' \
	-d '{"ids":["sw1234"], "debug": false, "calibration": false}' \
	-o "$OUT")

if [ "$STATUS" != "400" ]; then
	echo "Expected HTTP 400, got $STATUS"
	echo "Response body:"
	cat "$OUT"
	podman compose logs
	podman compose down
	rm -f "$OUT"
	exit 1
fi

if ! grep -q "credentials_missing" "$OUT"; then
	echo "Expected credentials_missing error in response"
	echo "Response body:"
	cat "$OUT"
	podman compose logs
	podman compose down
	rm -f "$OUT"
	exit 1
fi

rm -f "$OUT"
podman compose down
echo "e2e smoke OK: container wiring validated"
