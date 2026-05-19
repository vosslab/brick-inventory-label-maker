# Brick inventory label maker

Generate print-ready PDF labels for your LEGO storage bins. Paste BrickLink set or minifigure IDs into a local web app; it fetches photos and metadata, then lays them out for Avery label sheets. Runs on your computer, no cloud uploads.

## Documentation

- [docs/INSTALL.md](docs/INSTALL.md): setup steps and prerequisites.
- [docs/USAGE.md](docs/USAGE.md): minifig and set modes, flags, environment variables.
- [docs/CODE_ARCHITECTURE.md](docs/CODE_ARCHITECTURE.md): request flow, layers, and credentials.
- [docs/FILE_STRUCTURE.md](docs/FILE_STRUCTURE.md): directory layout and artifact locations.
- [docs/CHANGELOG.md](docs/CHANGELOG.md): recent changes and implementation notes.

## Features

- Avery 18260 minifigure labels (30-up) and Avery 5163 set labels (10-up).
- Live progress with per-item cards, thumbnails, and warnings panel.
- Dark-image action (warn, reject, or ignore).
- MSRP from bundled cache.
- Image cache shared with `external/brick-collection`.
- Random-port + auto-open in wrappers (dev and Podman).

## Quick start (Podman)

1. Install Podman Desktop.
2. Copy `bricklink_api_private.example.yml` to `bricklink_api_private.yml` and paste BrickLink OAuth1 keys.
3. Run `bash run_podman.sh`.
4. Open the link printed to the terminal.

## Quick start (development)

1. Run `source source_me.sh`.
2. Run `pip install -r pip_requirements.txt`.
3. Run `bash sync_vendor.sh` (one-time setup).
4. Run `bash setup_frontend.sh` (one-time setup).
5. Run `bash run_local.sh`.
6. Open `http://127.0.0.1:8080`.

## Testing

```bash
source source_me.sh && python3 -m pytest tests/
```

## Author

[Neil Voss](https://bsky.app/profile/neilvosslab.bsky.social)
