# File structure

## Top-level layout

- `backend/` - FastAPI application code (routes, adapters, config).
- `frontend/` - TypeScript UI bundle (source in `src/`, esbuild output in `dist/`).
- `vendor/` - Byte-identical copies of `external/brick-collection` (do not edit locally).
- `tests/` - pytest unit tests, Playwright browser specs, and E2E harness.
- `docs/` - user-facing and developer documentation (see [Documentation map](#documentation-map) below).
- `images/` - cache for downloaded and processed images (git-ignored).
- `cache/` or `CACHE/` - MSRP and HTTP cache directory (git-ignored).
- `_artifacts/` - test outputs and temporary files (git-ignored).
- `compose.yml` - Podman/Docker Compose configuration.
- `Dockerfile` - Python 3.12-slim production image.
- `source_me.sh` - shell setup; prepends `vendor/` to PYTHONPATH.
- `run_local.sh`, `run_podman.sh` - dev and container launch scripts.
- `setup_frontend.sh`, `build_frontend.sh` - npm setup and esbuild compile.
- `sync_vendor.sh` - refresh `vendor/` from `external/brick-collection`.
- `pip_requirements.txt`, `pip_requirements-dev.txt` - Python dependencies.
- `bricklink_api_private.yml` - BrickLink credentials (git-ignored; use `.example.yml` template).
- `VERSION` - CalVer version string (synced with `pyproject.toml`).

## Backend structure

```text
backend/
+- app.py                          # FastAPI app factory
+- config.py                       # Configuration and secrets loading
+- schemas.py                      # Pydantic request/response schemas
+- static_mount.py                 # Static file mounting helper
+- routes/
|  +- __init__.py
|  +- health.py                    # GET /api/health
|  +- labels.py                    # POST /api/labels/{minifigs,sets}[/stream]
|  `- cache.py                     # GET /api/cache/{kind}/{item_id}/{raw.jpg,processed.png}
`- adapters/
   +- __init__.py
   +- label_renderer.py            # Orchestrator; emits SSE events
   +- bricklink_adapter.py         # Fetch minifig/set metadata
   +- msrp_adapter.py              # Fetch retail pricing
   `- image_pipeline.py            # Download, cache, process images
```

## Frontend structure

```text
frontend/
+- src/
|  +- init.ts                      # App entry point
|  +- api/
|  |  `- client.ts                 # API client (health, labels streaming)
|  +- types/
|  |  `- api_types.ts              # TypeScript type definitions for API
|  `- ui/
|     +- health_banner.ts          # Health status display
|     +- flags_panel.ts            # Dark image action radio buttons
|     +- input_panel.ts            # ID textarea and generate button
|     +- item_card.ts              # Per-item thumbnail + status
|     +- progress_feed.ts          # SSE event feed parser
|     +- progress_log.ts           # Activity log UI
|     +- warnings_panel.ts         # Red error panel (pinned top)
|     `- download.ts               # PDF download button handler
+- dist/                           # esbuild output (git-ignored except tracking)
|  +- index.html
|  +- style.css
|  `- app.js
+- index.html                      # HTML template (esbuild input)
+- style.css                       # LEGO palette CSS
+- esbuild.config.mjs              # esbuild bundler config
+- tsconfig.json                   # TypeScript strict-mode config
+- package.json                    # npm scripts and dependencies
`- node_modules/                   # npm packages (git-ignored)
```

## Vendor structure

Byte-identical copies from `external/brick-collection`. Do not edit locally; sync via `bash sync_vendor.sh`.

```text
vendor/
+- libbrick/
|  +- __init__.py
|  +- common.py                    # Utility functions
|  +- image_cache.py               # Image caching and I/O
|  +- msrp_loader.py               # MSRP cache loader
|  +- path_utils.py                # Path handling
|  +- reportlab_label_utils.py      # ReportLab drawing helpers
|  `- wrappers/
|     +- __init__.py
|     +- bricklink_wrapper.py       # BrickLink API client
|     +- wrapper_base.py            # Base wrapper class
|     `- (other wrappers for Rebrickable, Brickset, etc.)
+- reportlab_make_minifig_labels.py # 30-up minifig label renderer
+- reportlab_make_set_labels.py    # 10-up set label renderer
`- VENDOR_SOURCE.md                # Upstream commit and sync instructions
```

## Tests structure

```text
tests/
+- test_*.py                       # pytest unit tests (fast; ~344 tests)
+- conftest.py                     # pytest config (excludes e2e, playwright)
+- git_file_utils.py               # Shared utility for repo root discovery
+- minifig_test_ids.csv            # Test data for minifig tests
+- TESTS_README.md                 # Test documentation
+- playwright/
|  +- test_*.spec.ts               # Playwright browser specs
|  +- test-results/                # test report (git-ignored)
|  `- _artifacts/                  # test screenshots/videos (git-ignored)
`- e2e/                            # End-to-end shell/Python scripts
   `- (e2e_*.sh, e2e_*.py when added)
```

## Generated artifacts and caches

- `images/raw/` - downloaded JPEG images from BrickLink (git-ignored).
- `images/processed/` - background-flattened PNG images (git-ignored).
- `cache/` or `CACHE/` - MSRP SQLite cache and HTTP cache (git-ignored; can be `external/brick-collection/CACHE`).
- `frontend/dist/` - esbuild bundle output (tracked for easy deployment).
- `_artifacts/` - temporary test outputs (git-ignored).
- `tests/playwright/test-results/` - Playwright HTML report (git-ignored).
- `tests/playwright/_artifacts/` - Playwright screenshots and videos (git-ignored).

## Documentation map

Docs live in `docs/` and are linked from `README.md`.

- `README.md` - brief purpose, features, quick start.
- `INSTALL.md` - setup steps, Podman/dev prerequisites, dependencies.
- `USAGE.md` - how to run minifig/set modes, CLI flags, environment variables.
- `CODE_ARCHITECTURE.md` - high-level design, request flow, vendor boundary, configuration.
- `FILE_STRUCTURE.md` - this file; directory layout and artifact locations.
- `CHANGELOG.md` - chronological user-facing record of changes.
- `PYTHON_STYLE.md` - Python formatting, linting, conventions (tabs, no try/except, etc.).
- `TYPESCRIPT_STYLE.md` - TypeScript strict-mode, type design, naming.
- `PLAYWRIGHT_USAGE.md` - browser test patterns and setup.
- `PYTEST_STYLE.md` - pytest test design, fixtures, fragile patterns to avoid.
- `REPO_STYLE.md` - repo-wide organization, versioning, Changelog rotation.
- `MARKDOWN_STYLE.md` - Markdown formatting and link rules.
- `E2E_TESTS.md` - end-to-end test structure and conventions.
- `CLAUDE_HOOK_USAGE_GUIDE.md` - safe patterns for AI agent bash usage.

## Where to add new work

- **Backend route** - add handler to `backend/routes/` or extend existing route.
- **Backend adapter** - add to `backend/adapters/` for new data source or processing step.
- **Frontend UI component** - add to `frontend/src/ui/` with TypeScript strict mode.
- **Frontend API** - extend `frontend/src/api/client.ts` and `frontend/src/types/api_types.ts`.
- **Test (unit)** - add `tests/test_*.py` for pytest, excluded from `e2e` and `playwright`.
- **Test (browser)** - add `tests/playwright/test_*.spec.ts` for Playwright specs.
- **Test (E2E)** - add `tests/e2e/e2e_*.sh` or `tests/e2e/e2e_*.py` for whole-system orchestration.
- **Documentation** - add to `docs/*.md` or update existing docs; keep in sync with [MARKDOWN_STYLE.md](MARKDOWN_STYLE.md).
- **Script** - add `name_purpose.sh` at repo root for single-purpose shell runners.
