#!/usr/bin/env bash

# Sync byte-identical copies of libbrick and reportlab helpers from brick-collection.
# Wipes vendor/ of over-copied files, copies only the targeted set, and refreshes VENDOR_SOURCE.md.

set -e

BRICK_COLLECTION_DIR="${BRICK_COLLECTION_DIR:-external/brick-collection}"
REPO_ROOT="$(git rev-parse --show-toplevel)"
VENDOR_DIR="$REPO_ROOT/vendor"

# Verify source directory exists
if [ ! -d "$BRICK_COLLECTION_DIR" ]; then
	echo "Error: BRICK_COLLECTION_DIR not found: $BRICK_COLLECTION_DIR" >&2
	exit 1
fi

# Files to copy (byte-identical, targeted list only)
declare -a FILES=(
	"libbrick/__init__.py"
	"libbrick/common.py"
	"libbrick/image_cache.py"
	"libbrick/msrp_loader.py"
	"libbrick/path_utils.py"
	"libbrick/reportlab_label_utils.py"
	"libbrick/wrappers/__init__.py"
	"libbrick/wrappers/bricklink_wrapper.py"
	"libbrick/wrappers/wrapper_base.py"
	"reportlab_make_minifig_labels.py"
	"reportlab_make_set_labels.py"
)

# Clean vendor directory to remove over-copied files, preserving VENDOR_SOURCE.md
if [ -d "$VENDOR_DIR/libbrick" ]; then
	rm -rf "$VENDOR_DIR/libbrick"
fi
rm -f "$VENDOR_DIR/reportlab_make_minifig_labels.py"
rm -f "$VENDOR_DIR/reportlab_make_set_labels.py"
rm -f "$VENDOR_DIR/pip_requirements-dev.txt"
rm -f "$VENDOR_DIR/pip_requirements.txt"
rm -f "$VENDOR_DIR/source_me.sh"
rm -f "$VENDOR_DIR/super_make_minifig_labels.py"
rm -f "$VENDOR_DIR/super_make_set_labels.py"
rm -rf "$VENDOR_DIR/seller_tools"

# Create target directories
mkdir -p "$VENDOR_DIR/libbrick/wrappers"

# Copy each file with mtimes preserved
for file in "${FILES[@]}"; do
	src="$BRICK_COLLECTION_DIR/$file"
	dst="$VENDOR_DIR/$file"
	if [ ! -f "$src" ]; then
		echo "Error: source file not found: $src" >&2
		exit 1
	fi
	install -D -p "$src" "$dst"
done

# Get source commit SHA
if cd "$BRICK_COLLECTION_DIR" 2>/dev/null && git rev-parse HEAD > /dev/null 2>&1; then
	SOURCE_SHA="$(git rev-parse HEAD)"
	SOURCE_COMMIT_LINE="Source commit: \`$SOURCE_SHA\`"
else
	SOURCE_COMMIT_LINE="Source commit: untracked working tree"
fi

cd "$REPO_ROOT"

# Regenerate VENDOR_SOURCE.md
cat > "$VENDOR_DIR/VENDOR_SOURCE.md" << 'EOF'
# Vendor Source

This directory contains byte-identical copies of files from the upstream
brick-collection repository.

## Source

Repository: https://github.com/neilvoss/brick-collection
EOF

echo "" >> "$VENDOR_DIR/VENDOR_SOURCE.md"
echo "$SOURCE_COMMIT_LINE" >> "$VENDOR_DIR/VENDOR_SOURCE.md"
echo "" >> "$VENDOR_DIR/VENDOR_SOURCE.md"

cat >> "$VENDOR_DIR/VENDOR_SOURCE.md" << 'EOF'
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
EOF

# Verify vendored files match source (check only the specific files we vendored)
HAS_DIFF=0
for file in "${FILES[@]}"; do
	src="$BRICK_COLLECTION_DIR/$file"
	dst="$VENDOR_DIR/$file"
	if ! diff "$src" "$dst" > /dev/null 2>&1; then
		echo "Error: vendor file differs from source: $file" >&2
		HAS_DIFF=1
	fi
done

if [ $HAS_DIFF -eq 0 ]; then
	echo "vendor sync OK (diff empty)"
	exit 0
else
	exit 1
fi
