# Vendor Source

This directory contains byte-identical copies of files from the upstream
brick-collection repository. Vendor tracks upstream `main` HEAD rather than
pinning a specific commit: brick-collection is in maintenance mode under the
sole maintainer, and only receives bug fixes. Re-run `bash sync_vendor.sh`
to refresh; the script `git pull --ff-only`s upstream first.

## Source

Repository: https://github.com/neilvoss/brick-collection

Last synced from upstream commit: `02fdfce85fff357b419f864bb8fd2458c2117aea`

## Vendored Files

- `libbrick/__init__.py`
- `libbrick/common.py`
- `libbrick/image_cache.py`
- `libbrick/msrp_loader.py`
- `libbrick/path_utils.py`
- `libbrick/reportlab_label_utils.py`
- `libbrick/wrappers/__init__.py`
- `libbrick/wrappers/bricklink_wrapper.py`
- `libbrick/wrappers/wrapper_base.py`
- `reportlab_make_minifig_labels.py`
- `reportlab_make_set_labels.py`

## Sync Command

To refresh vendor files from brick-collection, run:

```bash
bash sync_vendor.sh
```

Pulls latest upstream `main` then copies the files above. To vendor whatever
is currently checked out without pulling (offline / pinned-checkout), set
`SKIP_PULL=1`. To point at an alternate source directory, set
`BRICK_COLLECTION_DIR`:

```bash
SKIP_PULL=1 bash sync_vendor.sh
BRICK_COLLECTION_DIR=/path/to/brick-collection bash sync_vendor.sh
```

## Verification

To verify byte-identical copies:

```bash
for file in libbrick/__init__.py libbrick/common.py libbrick/image_cache.py libbrick/msrp_loader.py libbrick/path_utils.py libbrick/reportlab_label_utils.py libbrick/wrappers/__init__.py libbrick/wrappers/bricklink_wrapper.py libbrick/wrappers/wrapper_base.py reportlab_make_minifig_labels.py reportlab_make_set_labels.py; do
  diff external/brick-collection/$file vendor/$file || exit 1
done
```

Should produce no output and exit code 0.
