# Related projects

This section documents upstream repositories, shared libraries, and integration touchpoints.

## Upstream: brick-collection

The label maker depends on code and data vendored from [brick-collection](https://github.com/neilvoss/brick-collection), a unified LEGO reference and image-caching system.

- **Vendored components**: `libbrick/` (image-cache, path utilities, MSRP loader), `reportlab_make_*.py` (PDF template helpers).
- **Synchronization**: Run `bash sync_vendor.sh` at the repo root to pull byte-identical copies and update `vendor/VENDOR_SOURCE.md` with the upstream commit hash.
- **Key dependencies**: `libbrick.image_cache.download_image()`, `libbrick.image_cache.process_image()` for image fetching and background removal; `libbrick.path_utils.get_git_root()` for cache path resolution; `msrp_loader.load_msrp_cache()` for MSRP fallback data.
- **Upstream coordination**: When upstreaming improvements to BrickLink API adapters, User-Agent headers, or image-processing logic, coordinate with `brick-collection` maintainers to avoid divergence. Current (2026-05-19) upstream includes Chrome User-Agent fix for BrickLink CDN 403 errors.

## Shared image cache with brick-collection

Both the label maker and `brick-collection` reference images under `images/raw/` and `images/processed/`. A single cache directory can be shared across both projects by symlinking or using an environment variable (future work).

- **Current state**: Each project maintains its own cache.
- **Future optimization**: Implement a symlink or `CACHE_ROOT` env var to unify cache directories and avoid redundant downloads.

## Known gaps

- [ ] Document the full vendoring procedure and upstream commit tracking in `VENDOR_SOURCE.md`.
- [ ] Investigate symlinked or shared image cache across both projects.
- [ ] Coordinate with `brick-collection` on backwards-compatibility guarantees for `libbrick/` API.
