# Usage

## Inputs

- **Minifig list**: BrickLink minifig IDs, comma- or newline-separated. Examples: `sw1234`, `colhp01`.
- **Set list**: LEGO set IDs. Example: `10240-1` (trailing `-1` optional).

## Mode toggle

Select **minifig** or **set** mode via the radio button in the UI. This determines which endpoint is called.

## Flags

- **Calibration**: prepend a calibration page with rulers and slot outlines (useful for alignment checks).
- **Debug outlines**: draw red slot boxes and blue content-area boxes on every page (useful for layout debugging).

## Output

The browser automatically downloads `labels-<mode>-YYYY-MM-DD.pdf` when the request completes.

## Dark-image action

The backend respects the `DARK_IMAGE_ACTION` environment variable (default: `warn`). Valid modes:

- `warn`: log a warning if an image is too dark but include it in the PDF.
- `reject`: skip dark images entirely (resulting PDF may have blank spaces).
- `ignore`: include all images regardless of darkness.

The darkness threshold is controlled by `DARK_IMAGE_LSTAR_THRESHOLD` (default: 35). Lower values mean darker. Adjust both via `compose.yml` or locally in `run_local.sh`.

## MSRP refresh

The MSRP cache lives in `vendor/libbrick/msrp_loader.py` and reads from `<BRICK_CACHE_DIR>/msrp_cache.yml`. To update MSRP data:

1. Refresh the upstream `brick-collection/CACHE/msrp_cache.yml`.
2. Run `bash sync_vendor.sh` if needed to pull the updated cache.

## Calibration print

Print the calibration page on plain paper, then hold it against the Avery label stock to confirm alignment is within 1 mm.

## Manual PDF smoke (creds-required)

To test PDF generation with a live BrickLink connection:

```bash
curl -X POST http://localhost:8080/api/labels/minifigs \
  -H 'Content-Type: application/json' \
  -d '{"ids":["sw1234"], "debug": false, "calibration": false}'
```

Ensure `bricklink_api_private.yml` is present and valid; otherwise the endpoint returns HTTP 400 with `credentials_missing`.
