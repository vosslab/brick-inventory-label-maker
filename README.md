# Brick inventory label maker

Print photo labels for your LEGO storage bins. Paste BrickLink set or minifigure IDs into a local web app; it fetches LEGO images and metadata, then builds a print-ready PDF laid out for Avery label sheets. Runs on your computer.

## What it does

Type LEGO identifiers (e.g. `10240-1` for a set, `sw1234` for a minifigure) into a browser. The app pulls official photos and names from BrickLink (the largest online LEGO marketplace) and lays them out on a printable PDF. For collectors organizing physical bins. Single-user, local-only, no cloud uploads.

## At a glance

- Supports Avery 18260 (30-up minifigure labels) and Avery 5163 (10-up set labels).
- Fetches set and minifigure photos and metadata from BrickLink.
- Generates print-ready PDFs in a web browser.
- Runs locally; single-user; no cloud uploads.

## Status

v1 in progress. Local-only, Podman-first.

## Quick start (Podman)

1. Install Podman Desktop.
2. Copy `bricklink_api_private.example.yml` to `bricklink_api_private.yml` and paste BrickLink OAuth1 keys.
3. Run `podman compose up`.
4. Open `http://127.0.0.1:8080`.
5. Paste minifig or set IDs, click Generate, save the PDF.

## Quick start (dev)

1. Run `source source_me.sh`.
2. Run `pip install -r pip_requirements.txt`.
3. Run `bash sync_vendor.sh` (one-time copy from `external/brick-collection`).
4. Run `bash run_local.sh`.
5. Open `http://127.0.0.1:8080`.

## How it works

- FastAPI backend wraps byte-identical copies of `brick-collection` `libbrick` + reportlab label helpers.
- BrickLink API credentials live server-side in `bricklink_api_private.yml`; browser never sees them.
- Dark-variant images are warned by default (ink-saving); configurable with `DARK_IMAGE_ACTION`.
- Cache is local by default (`./cache/`); set `BRICK_CACHE_DIR` to share with `external/brick-collection/CACHE`.

## Docs

- [docs/CHANGELOG.md](docs/CHANGELOG.md)

## Author

[Neil Voss](https://bsky.app/profile/neilvosslab.bsky.social)
