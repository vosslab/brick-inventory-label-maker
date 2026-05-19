# Install

## Recommended: Podman Desktop

1. Download and install [Podman Desktop](https://podman-desktop.io/) on macOS.
2. On first run, Podman Desktop initializes a Podman machine. Accept the defaults.
3. Prepare BrickLink credentials:
   ```bash
   cp bricklink_api_private.example.yml bricklink_api_private.yml
   ```
   Edit the file and paste your OAuth1 keys (consumer_key, consumer_secret, token, token_secret) from BrickLink's API portal.
4. Bring up the container:
   ```bash
   podman compose up
   ```
5. Open [http://localhost:8080](http://localhost:8080) in your browser.

## Developer install

For local development without containers:

1. Ensure Python 3.12 from Homebrew is installed.
2. Activate the repo environment:
   ```bash
   source source_me.sh
   ```
3. Install Python dependencies:
   ```bash
   pip install -r pip_requirements.txt
   ```
4. Copy vendored dependencies (one-time setup from `external/brick-collection`):
   ```bash
   bash sync_vendor.sh
   ```
5. Install frontend dependencies:
   ```bash
   cd frontend && npm install
   cd ..
   ```
6. Run the dev server:
   ```bash
   bash run_local.sh
   ```
   This builds the frontend, then starts uvicorn on `127.0.0.1:8080` with hot-reload.

## Docker compatibility

Docker support is best-effort. The `Dockerfile` and `compose.yml` are Podman-first. On systems with Docker, `docker compose up` may work but Podman Desktop is the tested and recommended path.

## Cache directory

The default cache directory is `./cache/` at the repo root. To share the cache with an external `brick-collection` checkout, set `BRICK_CACHE_DIR` to `external/brick-collection/CACHE` and update the `volumes` section in `compose.yml` accordingly.
