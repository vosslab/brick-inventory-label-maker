#!/usr/bin/env bash
# Install or repair frontend dev dependencies (typescript, esbuild) in frontend/node_modules.
# Run after a fresh clone, after node_modules is cleared, or when build_frontend.sh
# fails with "tsc: command not found".
set -eo pipefail
cd "$(dirname "$0")/frontend"

if ! command -v npm >/dev/null 2>&1; then
	echo "ERROR: npm not found. Install Node.js first (e.g., 'brew install node')." >&2
	exit 1
fi

# Reinstall if typescript binary is missing or unexecutable.
if [ ! -x node_modules/.bin/tsc ] || [ ! -x node_modules/.bin/esbuild ]; then
	echo "Installing frontend dev dependencies (typescript, esbuild)..."
	npm install
else
	echo "Frontend dev dependencies already present. Re-running npm install to refresh."
	npm install
fi

echo
echo "Frontend setup complete."
echo "Build with:  bash build_frontend.sh"
echo "Run dev:     bash run_local.sh"
