# TODO

Backlog of improvements and follow-up tasks without committed timelines.

## Planned features

- **v0.2 Server-sent events (SSE) hosted proxy**: Host a lightweight SSE-based label-generation service so users can paste IDs into a public web form and download PDFs. Current streaming endpoints require local OAuth1 credentials; a proxy would handle auth server-side and return base64 PDFs only.
- **Per-card thumbnail refinement**: Live progress cards show 56x56px thumbnails with a top-center crop for minifigs. Expand to full-width responsive thumbnails in a gallery view before render, allowing users to preview and confirm all images before committing to PDF.
- **Upstream cache-only methods**: Coordinate with `brick-collection` on offering cache-only image-fetch methods so the label maker can skip expensive Hugging Face model loads when all images are already cached.

## Maintenance backlog

- **Environment variable rule violation**: Current code references `DARK_IMAGE_*` conceptually (see USAGE.md) but implements them as command-line flags only. Remove any environment variable references from docs and code to align with [PYTHON_STYLE.md](PYTHON_STYLE.md#environment-variables) (environment variables should be standard OS/ecosystem vars, not app-specific).
- **Frontend node_modules exclusion**: Ensure `frontend/node_modules/` stays out of git via `.gitignore` and document the one-time `setup_frontend.sh` requirement. Currently excluded; verify CI/CD templates do not accidentally commit it.
- **Mass-untracking of frontend build artifacts**: If `frontend/dist/` or build outputs are accidentally tracked, add to `.gitignore` and run `git rm --cached` to stop tracking without deleting.

## Known gaps

- [ ] Outline v0.2 proxy service architecture and deployment strategy.
- [ ] Benchmarks for large batches (100+ items) and identify multi-threading bottlenecks.
- [ ] Playwright test coverage for all flag combinations and error paths.
- [ ] End-to-end dark-image action behavior validation across all three modes (warn, reject, ignore).
