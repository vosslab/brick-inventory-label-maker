# Vendor Source

This directory contains byte-identical copies of files from the upstream
brick-collection repository.

## Source

Repository: https://github.com/neilvoss/brick-collection

Source commit: `f33bddee899fb26505729423256884ec9f6a7d90`

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

Or with a custom source directory:

```bash
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
