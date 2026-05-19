# Troubleshooting

This document covers known issues, common failure modes, and recovery steps.

## Image download and processing

### First-call rembg model download is slow

When you run the label maker for the first time, the background-removal model downloads from Hugging Face (~350 MB). This can take several seconds or longer on slow connections.

- **Symptom**: Long pause (5-30 seconds) on first minifig or set in the session, then subsequent items process quickly.
- **Fix**: This is normal. The model caches locally after the first call. Subsequent runs reuse the cached model.

### Dark image detection warns or rejects minifigs

The label maker classifies minifigure and set images by perceived brightness (L* in the CIELab color space). Dark images may waste ink when printed.

- **Symptom**: Progress log shows "dark_image_warn" or "dark_image_reject" for some items.
- **Action**: Check the raw image on BrickLink to see if it has a dark background. Either accept the warning (item still renders) or adjust the `--dark-image` flag (warn, reject, or ignore).
- **Note**: Dark-image detection runs after background removal, so transparent backgrounds with white compositing are treated as light.

### Image fetch returns 403 or other HTTP errors

BrickLink's image CDN may reject requests with non-standard User-Agent headers.

- **Symptom**: Progress log shows "image_missing" for items that exist on BrickLink.
- **Fix**: The label maker now sends a desktop Chrome User-Agent header by default (vendor sync as of 2026-05-19). If you see this error, verify that `vendor/libbrick/image_cache.py` has the updated UA string. Run `bash sync_vendor.sh` to refresh.

### Cache corruption or stale images

Images are cached locally under `images/raw/` and `images/processed/`. A corrupted file may cause processing to fail.

- **Symptom**: Consistent failure for a specific minifig or set, but other items work.
- **Action**: Delete the cached files in `images/raw/{kind}/{item_id}/raw.jpg` and `images/processed/{kind}/{item_id}/processed.png`, then retry. The label maker will re-download and re-process.

## Credentials and API access

### BrickLink API credentials missing or invalid

The label maker requires OAuth1 credentials to fetch minifigure and set data from BrickLink.

- **Symptom**: Progress log shows "credentials_missing" or the app fails to start.
- **Action**: Copy `bricklink_api_private.example.yml` to `bricklink_api_private.yml`. Paste your OAuth1 consumer key and token from BrickLink's API settings.

### BrickLink item not found (404)

When you paste a minifigure or set ID that does not exist or is misspelled, the API returns 404.

- **Symptom**: Progress log shows "bricklink_lookup_failed" for that item; the label is skipped.
- **Action**: Verify the ID on BrickLink and correct the spelling.

## Rendering and output

### PDF is empty or missing images

If many or all images fail to fetch or process, the PDF may render with blank image areas.

- **Symptom**: PDF opens but shows text-only labels with no photos.
- **Debug**: Check the progress log for "image_missing" or processing errors. See the "Image fetch" and "Image download and processing" sections above.

### Labels are misaligned on the page

The label maker targets specific Avery templates (18260 for minifigs, 5163 for sets). Misalignment usually means you are using a different sheet template.

- **Symptom**: Printed labels do not line up with the Avery sheet holes.
- **Action**: Verify your sheet template matches the one the label maker targets. Adjust your printer settings if needed (scaling, margins).

## Known gaps

- [ ] Playwright end-to-end tests for dark-image action flags and User-Agent header behavior.
- [ ] Documentation of `--dark-image` flag values and examples.
- [ ] Podman rootless mode on macOS and permission quirks (investigate cgroup limits, bind mounts).
- [ ] Performance profiling for large batches (100+ items) and multi-threaded image processing feasibility.
