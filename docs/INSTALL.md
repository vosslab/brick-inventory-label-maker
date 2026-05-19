# Install

The application is a local web service that generates print-ready PDF labels for LEGO storage. Installation makes the app runnable either in a container (Podman, recommended) or locally (Python + Node.js).

## Requirements

- **Podman path**: [Podman Desktop](https://podman-desktop.io/) (kid-friendly, tested on macOS).
- **Developer path**: Python 3.12 (Homebrew), Node.js, and npm (for frontend build).
- **Credentials**: BrickLink OAuth1 keys (consumer_key, consumer_secret, token, token_secret) from [BrickLink's API portal](https://www.bricklink.com/).
- **System deps**: `rembg` CLI (via pip, downloads model on first run; may be slow).

## Install steps

### Podman (recommended, kid-friendly)

1. Download and install [Podman Desktop](https://podman-desktop.io/).
2. On first run, Podman Desktop initializes a machine. Accept the defaults.
3. Prepare BrickLink credentials:
   ```bash
   cd /path/to/brick-inventory-label-maker
   cp bricklink_api_private.example.yml bricklink_api_private.yml
   ```
   Edit the file and paste your OAuth1 keys.
4. Bring up the stack:
   ```bash
   bash run_podman.sh
   ```
   This picks a random free port (8000-9999), builds the image, starts the container, and opens your browser. Logs stream in the foreground; `Ctrl-C` stops the stream but keeps the stack running.

### Developer (local Python + Node.js)

1. Ensure Python 3.12 is installed (Homebrew).
2. In the repo directory:
   ```bash
   source source_me.sh
   pip install -r pip_requirements.txt
   bash sync_vendor.sh
   bash setup_frontend.sh
   bash run_local.sh
   ```
   The script builds the frontend, starts uvicorn on a random port (8000-9999), and opens your browser.

## Verify install

After running your chosen path above, check that the app loads:

```bash
curl http://127.0.0.1:8000/health
```

(Replace `8000` with whatever port the startup script reports.)

Expected response: HTTP 200, JSON `{"status":"ok"}`.

## Environment and credentials

- **Credentials file**: default `./bricklink_api_private.yml` at the repo root. Override via `BRICKLINK_API_FILE` (e.g. `/etc/brick-labels/bricklink_api_private.yml` in container).
- **Cache dir**: default `./cache/`. Override via `BRICK_CACHE_DIR` (e.g., shared with upstream `external/brick-collection/CACHE`).
- **Dark-image action**: `DARK_IMAGE_ACTION` env var (`warn` default; also `reject` or `ignore`). Threshold: `DARK_IMAGE_LSTAR_THRESHOLD` (default 35, lower = darker).

## Troubleshooting

- **Port binding fails**: ensure no other service is using ports 8000-9999. `lsof -i :8080` shows listeners.
- **BrickLink credentials missing**: verify `bricklink_api_private.yml` exists and contains valid OAuth1 keys. Container mounts it read-only; check file permissions.
- **`rembg` model download hangs**: first call to dark-image detection downloads a large model (~400 MB). Be patient; subsequent calls use the cached model.

## Docker compatibility

Docker support is best-effort. The `compose.yml` is Podman-first. On systems with Docker, `docker compose up` may work; Podman Desktop is the tested and recommended path.
