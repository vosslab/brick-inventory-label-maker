# Usage

Paste LEGO minifigure or set IDs into the web UI to generate print-ready PDF labels. The app fetches photos and metadata from BrickLink, detects dark images, and renders labels sized for Avery sheets (Avery 18260 for minifigs, Avery 5163 for sets).

## Quick start

1. Open the URL printed by the startup script (e.g., `http://127.0.0.1:8000`).
2. Paste IDs (newline or comma-separated) into the textarea.
3. Toggle between **minifig** and **set** mode.
4. Click the green **Download** button. A PDF downloads when complete.

## Modes

### Minifig mode (Avery 18260, 30-up)

Input BrickLink minifig IDs. Examples: `sw1113`, `colhp01`, `frnd0583`.

Output: 30 minifigs per page, name and price per label.

### Set mode (Avery 5163, 10-up)

Input LEGO set IDs. Examples: `10240-1` or `10240` (the `-1` is optional).

Output: 10 sets per page, name and MSRP per label.

## Flags

- **Calibration**: prepend a test page with rulers and slot outlines. Print on plain paper, hold against label stock, confirm alignment within 1 mm.
- **Debug outlines**: draw red slot boxes and blue content boxes on every page. Useful for layout debugging.

## Live progress

As items are processed, progress cards appear in the UI (newest at top, oldest scrolls off). Each card shows a status icon (spinner, check, warning, or error), thumbnail (raw -> processed), item ID, name, and optional warning.

A **warnings panel** appears at the top when any item warns. Reasons:

- `bricklink_lookup_failed`: minifig/set not found on BrickLink.
- `image_url_missing`: BrickLink record has no image URL.
- `image_missing: <reason>`: image download or cache failure.
- `dark_image_warn` / `dark_image_reject` / `dark_image_ignore`: image darkness action taken.

## Dark-image behavior

The backend detects images darker than a threshold (default L\* = 35, lower = darker) and takes an action:

- `warn` (default): log warning, include image anyway.
- `reject`: skip the image entirely (blank space in PDF).
- `ignore`: include all images, no warning.

Configure via environment variables:

```bash
DARK_IMAGE_ACTION=warn DARK_IMAGE_LSTAR_THRESHOLD=35 bash run_local.sh
```

Or in `compose.yml` under `environment:`.

## MSRP cache refresh

MSRP data is bundled in `vendor/libbrick/msrp_loader.py` and loaded from `<BRICK_CACHE_DIR>/msrp_cache.yml`. To update:

1. Refresh the upstream `external/brick-collection/CACHE/msrp_cache.yml`.
2. Run `bash sync_vendor.sh` to pull the updated cache into `vendor/`.

## API endpoints (manual testing)

### Non-streaming (full PDF in response)

```bash
curl -X POST http://127.0.0.1:8000/api/labels/minifigs \
  -H 'Content-Type: application/json' \
  -d '{"ids":["sw1113"],"debug":false,"calibration":false}' \
  -o labels.pdf
```

### Streaming (SSE with progress events)

```bash
curl -X POST http://127.0.0.1:8000/api/labels/minifigs/stream \
  -H 'Content-Type: application/json' \
  -d '{"ids":["sw1113"]}'
```

Returns `text/event-stream` with `event: progress` frames (item status, thumbnail URL) and `event: done` with PDF bytes.

### Cache routes (for UI thumbnails)

```bash
curl http://127.0.0.1:8000/api/cache/minifig/sw1113/raw.jpg -o raw.jpg
curl http://127.0.0.1:8000/api/cache/minifig/sw1113/processed.png -o processed.png
```

`kind` must be `minifig` or `set`. Item ID validated as `^[A-Za-z0-9_-]+$`.

## Output format

The PDF is named `labels-<mode>-YYYY-MM-DD.pdf` and downloads automatically from the UI. Each label includes:

- Item thumbnail (processed image on white background).
- Item ID and name.
- MSRP (for sets) or purchase price (for minifigs, if available).
- Barcode or QR code (future).

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `BRICKLINK_API_FILE` | `./bricklink_api_private.yml` | Path to OAuth1 credentials (read-only in container). |
| `BRICK_CACHE_DIR` | `./cache` | Image and MSRP cache directory. |
| `DARK_IMAGE_ACTION` | `warn` | Dark-image handling: `warn`, `reject`, or `ignore`. |
| `DARK_IMAGE_LSTAR_THRESHOLD` | `35` | Darkness threshold (L\* value, lower = darker). |
| `LABELS_OFFLINE` | `0` | Set to `1` to skip BrickLink lookup (cache-only mode, for testing). |
| `LABELS_PORT` | `8080` | (Container only) port for uvicorn. Set by `run_podman.sh`. |
