"""Image pipeline for fetching, trimming, and classifying BrickLink images."""

# Standard Library
import dataclasses
import io
import os
import random
import subprocess
import time
from typing import Callable

# PIP3 modules
import numpy
import PIL.Image
import requests.exceptions

# local repo modules
import libbrick.image_cache
import libbrick.path_utils


#============================================
# Result dataclasses


@dataclasses.dataclass(frozen=True)
class Trimmed:
	"""Successfully trimmed and classified bright image."""
	image_bytes: bytes
	mean_lstar: float
	width: int
	height: int


@dataclasses.dataclass(frozen=True)
class DarkImage:
	"""Image classified as dark below threshold."""
	action: str
	mean_lstar: float
	image_bytes: bytes | None


@dataclasses.dataclass(frozen=True)
class MissingImage:
	"""Image could not be fetched or processed."""
	reason: str


#============================================
# Configuration helpers


def _dark_action() -> str:
	"""Read DARK_IMAGE_ACTION lazily so tests can monkeypatch env."""
	return os.environ.get('DARK_IMAGE_ACTION', 'warn')


def _dark_threshold() -> float:
	"""Read DARK_IMAGE_LSTAR_THRESHOLD lazily."""
	return float(os.environ.get('DARK_IMAGE_LSTAR_THRESHOLD', '35'))


def _get_images_dir() -> str:
	"""Compute images directory path the same way vendor does."""
	git_root = libbrick.path_utils.get_git_root()
	if git_root is None:
		return 'images'
	return os.path.join(git_root, 'images')


#============================================
# Private helpers


def _compute_mean_lstar(rgb_array: numpy.ndarray) -> float:
	"""Compute mean CIE L* lightness over RGB array."""
	if rgb_array.size == 0:
		return 0.0

	# Normalize to 0-1 range
	rgb_normalized = rgb_array.astype(numpy.float32) / 255.0

	# Apply sRGB companding: inverse gamma to linear
	mask = rgb_normalized <= 0.04045
	linear = numpy.where(
		mask,
		rgb_normalized / 12.92,
		numpy.power((rgb_normalized + 0.055) / 1.055, 2.4)
	)

	# sRGB to XYZ (D65 illuminant)
	matrix = numpy.array([
		[0.4124564, 0.3575761, 0.1804375],
		[0.2126729, 0.7151522, 0.0721750],
		[0.0193339, 0.1191920, 0.9503041]
	])
	xyz = numpy.dot(linear, matrix.T)

	# XYZ to Lab using D65 reference white
	ref_white = numpy.array([0.95047, 1.00000, 1.08883])
	xyz_norm = xyz / ref_white

	# Lab conversion
	delta = 6.0 / 29.0
	mask = xyz_norm > delta ** 3
	f_xyz = numpy.where(
		mask,
		numpy.power(xyz_norm, 1.0 / 3.0),
		xyz_norm / (3 * delta ** 2) + 4.0 / 29.0
	)

	l_star = 116 * f_xyz[..., 1] - 16
	return float(numpy.mean(l_star))


def _is_white_ish(pixel: tuple) -> bool:
	"""Check if pixel meets white-ish criterion (R,G,B >= 245)."""
	if len(pixel) < 3:
		return False
	r, g, b = pixel[0], pixel[1], pixel[2]
	return r >= 245 and g >= 245 and b >= 245


def _flatten_to_white(image: PIL.Image.Image) -> PIL.Image.Image:
	"""
	Composite an image onto a solid white background and return RGB.

	rembg-processed PNGs carry transparency where the background was removed.
	Naive `image.convert('RGB')` would composite against black; explicit paste
	onto a white canvas preserves the printable "white background" appearance.
	"""
	if image.mode == 'RGB':
		return image
	if image.mode != 'RGBA':
		image = image.convert('RGBA')
	background = PIL.Image.new('RGB', image.size, (255, 255, 255))
	# split()[3] is the alpha channel used as paste mask
	background.paste(image, mask=image.split()[3])
	return background


def _trim_white_edges(image: PIL.Image.Image) -> PIL.Image.Image | None:
	"""
	Trim white-ish edges from image.

	Converts to RGBA, builds mask of non-white pixels, computes bbox,
	and crops. Returns None if image is entirely white-ish (blank).
	"""
	if image.mode != 'RGBA':
		image = image.convert('RGBA')

	width, height = image.size
	pixels = image.load()

	# Build mask: 1 where pixel is NOT white-ish (or has alpha < 255)
	mask = numpy.zeros((height, width), dtype=numpy.uint8)
	for y in range(height):
		for x in range(width):
			pixel = pixels[x, y]
			alpha = pixel[3] if len(pixel) > 3 else 255
			is_white = _is_white_ish(pixel) and alpha == 255
			if not is_white:
				mask[y, x] = 1

	# Compute bounding box
	rows = numpy.any(mask, axis=1)
	cols = numpy.any(mask, axis=0)

	if not (numpy.any(rows) and numpy.any(cols)):
		# Entire image is white-ish
		return None

	ymin, ymax = numpy.where(rows)[0][[0, -1]]
	xmin, xmax = numpy.where(cols)[0][[0, -1]]

	# Crop
	cropped = image.crop((xmin, ymin, xmax + 1, ymax + 1))
	return cropped


#============================================
# Main pipeline


def fetch_and_classify(
	image_url: str,
	kind: str,
	item_id: str,
	on_event: Callable[[dict], None] | None = None,
) -> Trimmed | DarkImage | MissingImage:
	"""
	Fetch image via vendored libbrick cache, trim white edges, compute CIE L*, and classify.

	Args:
		image_url: URL to fetch image from.
		kind: Image kind ('minifig' or 'set'). Must be one of these values.
		item_id: Item ID for cache key.
		on_event: Optional callback(event: dict) -> None. Emits image_downloaded and
			image_processed events.

	Returns:
		Trimmed: bright image with cropped bytes and L* value.
		DarkImage: image below L* threshold; action and bytes depend on config.
		MissingImage: fetch/decode failure or blank image.
	"""
	# Validate kind argument
	if kind not in ('minifig', 'set'):
		raise ValueError(f"kind must be 'minifig' or 'set', got {kind!r}")

	# Compute cache paths using vendor's logic
	images_dir = _get_images_dir()
	libbrick.image_cache.ensure_images_directory(images_dir)
	raw_filename = os.path.join(images_dir, 'raw', f"{kind}_{item_id}.jpg")
	processed_filename = os.path.join(images_dir, 'processed', f"{kind}_{item_id}.png")

	# Cache-warm short-circuit: processed file is the only thing downstream needs.
	# If processed exists, skip both download and process; otherwise download (if raw
	# is missing) and process. Raw alone is not sufficient: still process.
	processed_cached = os.path.exists(processed_filename)
	raw_cached = os.path.exists(raw_filename)

	if not processed_cached:
		if not raw_cached:
			# Random delay before network call, per repo style
			time.sleep(random.random())
			# Download image (OSError covers FileNotFoundError + disk-full PermissionError)
			try:
				libbrick.image_cache.download_image(image_url, raw_filename)
			except (OSError, requests.exceptions.RequestException) as e:
				return MissingImage(reason=str(e))

	# Emit image_downloaded event regardless of cache state.
	if on_event:
		on_event({"type": "image_downloaded", "id": item_id, "kind": kind})

	if not processed_cached:
		try:
			libbrick.image_cache.process_image(raw_filename, processed_filename)
		except (subprocess.CalledProcessError, OSError) as e:
			return MissingImage(reason=str(e))

	# Emit image_processed event (cache status or actual process)
	if on_event:
		on_event({"type": "image_processed", "id": item_id, "kind": kind})

	# Load and process the cached image
	try:
		image = PIL.Image.open(processed_filename)
	except Exception:
		return MissingImage(reason="decode failed")

	# Trim white edges
	trimmed = _trim_white_edges(image)
	if trimmed is None:
		return MissingImage(reason="blank image")

	# Flatten transparency onto white background BEFORE RGB conversion.
	# PIL's convert('RGB') composites against black by default; rembg output
	# has transparent background, so a naive convert would turn the bin labels
	# into a black-bordered minifig. Explicit composite keeps the label printable.
	trimmed_rgb = _flatten_to_white(trimmed)

	# Compute mean L*
	rgb_array = numpy.array(trimmed_rgb)
	mean_lstar = _compute_mean_lstar(rgb_array)

	# Check threshold
	threshold = _dark_threshold()
	if mean_lstar < threshold:
		action = _dark_action()
		# Encode cropped image to bytes if needed
		if action in ('warn', 'ignore'):
			buf = io.BytesIO()
			trimmed_rgb.save(buf, format='PNG')
			image_bytes = buf.getvalue()
		else:  # reject
			image_bytes = None
		return DarkImage(action=action, mean_lstar=mean_lstar, image_bytes=image_bytes)

	# Bright image: encode and return Trimmed
	buf = io.BytesIO()
	trimmed_rgb.save(buf, format='PNG')
	image_bytes = buf.getvalue()

	width, height = trimmed_rgb.size
	return Trimmed(image_bytes=image_bytes, mean_lstar=mean_lstar, width=width, height=height)
