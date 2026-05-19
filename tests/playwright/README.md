# Playwright End-to-End Tests

Browser-driven end-to-end tests for the brick inventory label maker, using [Playwright](https://playwright.dev/).

These tests live under `tests/playwright/` and are excluded from pytest collection via `collect_ignore` in `tests/conftest.py`. Run them directly with `npx playwright test`, not via `pytest tests/`.

## Setup

Install Playwright and dependencies:

```bash
cd tests/playwright
npm install
npx playwright install --with-deps chromium
```

## Running tests

From the `tests/playwright/` directory:

```bash
npx playwright test
```

Or run a specific test file:

```bash
npx playwright test minifig_smoke.spec.ts
```

## Prerequisites

The backend must be running at `http://127.0.0.1:8080`. Start it with:

```bash
./run_local.sh
```

Override the base URL with the `BASE_URL` environment variable:

```bash
BASE_URL=http://example.com:3000 npx playwright test
```

## Test: `minifig_smoke.spec.ts`

Smoke test exercising the live minifig label generation endpoint with five specific BrickLink minifig IDs.

### Test IDs

The test posts these five minifig IDs to `POST /api/labels/minifigs`:

- `sw0001c` - Star Wars minifig (image fetch may fail; tests expect warning without failure)
- `sw1113` - Star Wars minifig (image fetch may fail)
- `sw1321` - Star Wars minifig (image fetch may fail)
- `sw0092` - Star Wars minifig (image fetch may fail)
- `sw1247` - Star Wars minifig (image fetch may fail)

### Behavior

**If credentials are missing** (`config_present === false`):
- Expects HTTP 400 with error: `credentials_missing`
- Does not generate PDF

**If credentials are present** (`config_present === true`):
- Expects HTTP 200 with `Content-Type: application/pdf`
- Verifies PDF magic bytes (`%PDF`)
- Verifies PDF body is at least 1000 bytes
- Parses optional `X-Item-Warnings` JSON header
  - Each warning (if present) must have `id`, `reason`, and `mean_lstar` fields
  - Test does NOT assert on warning count (some images may fetch successfully, others may not)
- Writes the generated PDF to `_artifacts/minifig_smoke.pdf` for manual verification
- Verifies artifact file exists and has non-zero size

### Why images may fail

Some minifig images on BrickLink are unavailable or inaccessible at image fetch time. The endpoint treats missing images as warnings, not errors, and still generates a complete PDF. The test expects this behavior and does not fail if warnings are present.

## Output artifacts

Generated PDFs are written to `_artifacts/` and are ignored by git (see `_artifacts/.gitignore`).

For manual verification:
```bash
open tests/playwright/_artifacts/minifig_smoke.pdf
```
