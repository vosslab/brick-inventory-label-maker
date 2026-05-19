# Code architecture

## Overview

A FastAPI backend renders print-ready PDF labels for LEGO minifigures and sets. The frontend submits item IDs via streaming POST; the backend fetches metadata from BrickLink and images from the network, caches results, and renders labels using ReportLab. No cloud uploads; all data stays local.

## Layers

- **Frontend** - TypeScript (strict mode) + esbuild bundle, served from `/` by FastAPI's static mount. Entry point `frontend/src/init.ts`; UI components in `frontend/src/ui/`, API client in `frontend/src/api/client.ts`, type definitions in `frontend/src/types/api_types.ts`.
- **Backend** - FastAPI app factory `backend/app.py`. Routes in `backend/routes/` (health, labels, cache). Schemas in `backend/schemas.py`.
- **Adapters** - Orchestrators and data fetchers:
  - `backend/adapters/label_renderer.py` - orchestrates minifig/set label generation, emits SSE events.
  - `backend/adapters/bricklink_adapter.py` - fetches minifig/set metadata from BrickLink API.
  - `backend/adapters/msrp_adapter.py` - looks up retail pricing from bundled cache.
  - `backend/adapters/image_pipeline.py` - downloads images, caches, and processes (dark detection, background flattening).
- **Vendor** - Byte-identical copies of `external/brick-collection`. Read-only; do not edit locally. Contains `libbrick/` (utilities) and `reportlab_make_*.py` (label renderers).

## Request flow (streaming minifigs and sets)

1. Frontend submits minifig or set IDs via `POST /api/labels/minifigs` or `POST /api/labels/sets`.
2. Frontend opens `POST /api/labels/minifigs/stream` or `POST /api/labels/sets/stream` with SSE to receive progress events.
3. Route handler calls `label_renderer.py` in a background thread.
4. Label renderer emits events on a queue; SSE handler writes them as `text/event-stream`.
5. For each item:
   - `bricklink_adapter.py` fetches minifig/set metadata (name, color, etc.).
   - `image_pipeline.py` downloads image, checks cache, detects darkness, flattens to white.
   - `msrp_adapter.py` looks up retail price.
   - Emits `item_started`, `image_downloaded`, `image_processed`, `item_finished` events.
6. After all items, `reportlab_make_minifig_labels.py` or `reportlab_make_set_labels.py` renders Canvas.
7. Canvas bytes returned as PDF to frontend; frontend downloads.

## Image pipeline

State machine for each item:

- **Cache-warm (short-circuit)** - both raw and processed images in cache; emit `image_downloaded` and `image_processed` immediately.
- **Partial cache** - raw image present, processed missing; skip download, process only, emit events.
- **Cold** - raw image missing; download, process, emit both events.

Events (`image_downloaded`, `image_processed`) emitted on both cold and partial paths for consistency.

## Vendor reuse boundary

Upstream is `external/brick-collection`. The `sync_vendor.sh` script refreshes `vendor/` to match the upstream copy. Repo style rules (tabs, no try/except, etc.) do NOT apply inside `vendor/`. The vendor tree is an external dependency boundary:

- `vendor/libbrick/` - utility modules (image caching, MSRP loading, wrappers for BrickLink/Rebrickable).
- `vendor/reportlab_make_minifig_labels.py` - renders 30-up minifig labels (Avery 18260).
- `vendor/reportlab_make_set_labels.py` - renders 10-up set labels (Avery 5163).

To update vendor, set `BRICK_COLLECTION_DIR=/path/to/brick-collection` and run `bash sync_vendor.sh`.

## Credentials

The file `bricklink_api_private.yml` (YAML format matching `brick-collection`) is loaded lazily by `backend/config.py`. If missing or invalid, the route returns HTTP 400 with `error: credentials_missing` before attempting a live BrickLink call. In container mode, the file is bind-mounted read-only from the host. Override path with `BRICKLINK_API_FILE` environment variable.

## Configuration

Environment variables:

- `BRICKLINK_API_FILE` - path to credentials YAML (default: `bricklink_api_private.yml`).
- `BRICK_CACHE_DIR` - directory for MSRP and image caches (default: `./cache/`). Can point to `external/brick-collection/CACHE` for shared cache.
- `DARK_IMAGE_ACTION` - action for dark images: `warn`, `reject`, or `ignore` (default: `warn`).
- `DARK_IMAGE_LSTAR_THRESHOLD` - L* threshold for darkness detection (default: 35).
- `LABELS_OFFLINE` - reserved for future offline/fixture mode.
- `LABELS_PORT` - port for uvicorn in dev mode (default: random 8000-9999).

## Containers

The `Dockerfile` (Python 3.12-slim base) and `compose.yml` (Podman-first, Docker best-effort) ship a production-ready image. The container sets `PYTHONPATH=/app/vendor` so absolute imports in the vendor code resolve correctly. Cache and credentials are bind-mounted at runtime.
