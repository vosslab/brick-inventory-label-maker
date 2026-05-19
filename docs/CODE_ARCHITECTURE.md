# Code architecture

## Layers

- `frontend/` - TypeScript + esbuild bundle, served from `/` by FastAPI's static mount.
- `backend/` - FastAPI application; routes dispatch to adapters.
- `backend/adapters/` - Adapters for BrickLink API, MSRP lookup, image pipeline, and label rendering.
- `vendor/` - Byte-identical copies of `external/brick-collection/libbrick` plus ReportLab label makers. Read-only; do not edit.

## Reuse boundary

Upstream is `external/brick-collection`. The `sync_vendor.sh` script refreshes the `vendor/` directory to match the upstream copy. Repo style rules (tabs, no try/except, etc.) do NOT apply inside `vendor/`. The vendor tree is an external dependency boundary.

## Request flow

1. User submits minifig or set IDs via the frontend UI.
2. POST -> `backend/routes/labels.py` route.
3. Route calls `label_renderer.py` adapter.
4. Label renderer orchestrates:
   - `bricklink_adapter.py` - fetch minifig/set metadata.
   - `msrp_adapter.py` - fetch retail pricing.
   - `image_pipeline.py` - download and process images.
5. Renderers (`vendor/reportlab_make_minifig_labels.py`, `vendor/reportlab_make_set_labels.py`) create ReportLab Canvas.
6. Canvas renders to PDF bytes.
7. Route returns PDF as `application/pdf`.

## Credentials

The file `bricklink_api_private.yml` is loaded lazily by `backend/config.py`. If missing or invalid, the route returns HTTP 400 with `error: credentials_missing` before attempting a live BrickLink call. In container mode, the file is bind-mounted read-only from the host.

## Configuration

Environment variables:

- `BRICKLINK_API_FILE`: path to credentials YAML (default: `bricklink_api_private.yml`).
- `BRICK_CACHE_DIR`: directory for MSRP and image caches (default: `./cache/`).
- `DARK_IMAGE_ACTION`: action for dark images - `warn`, `reject`, or `ignore` (default: `warn`).
- `DARK_IMAGE_LSTAR_THRESHOLD`: L* threshold for darkness (default: 35).
- `LABELS_OFFLINE`: reserved for future offline/fixture mode.

## Containers

The `Dockerfile` (Python 3.12-slim base) and `compose.yml` (Podman-first, Docker best-effort) ship a production-ready image. The container sets `PYTHONPATH=/app/vendor` so absolute imports in the vendor code resolve correctly. Cache and credentials are bind-mounted at runtime.
