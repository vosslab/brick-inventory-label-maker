"""Image pipeline for fetching, trimming, and classifying BrickLink images."""

# Standard Library
import dataclasses
import io
import os
import random
import time

# PIP3 modules
import numpy
import PIL.Image

# local repo modules
import libbrick.image_cache


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


def fetch_and_classify(image_url: str, kind: str, item_id: str) -> Trimmed | DarkImage | MissingImage:
	"""
	Fetch image via vendored libbrick cache, trim white edges, compute CIE L*, and classify.

	Args:
		image_url: URL to fetch image from.
		kind: Image kind ('minifig' or 'set'). Must be one of these values.
		item_id: Item ID for cache key.

	Returns:
		Trimmed: bright image with cropped bytes and L* value.
		DarkImage: image below L* threshold; action and bytes depend on config.
		MissingImage: fetch/decode failure or blank image.
	"""
	# Validate kind argument
	if kind not in ('minifig', 'set'):
		raise ValueError(f"kind must be 'minifig' or 'set', got {kind!r}")

	# Random delay before network call, per repo style
	time.sleep(random.random())

	# Fetch and cache image via vendored libbrick
	try:
		cached_path = libbrick.image_cache.get_cached_image(
			image_url, kind, item_id
		)
	except Exception as e:
		return MissingImage(reason=str(e))

	# Load and process the cached image
	try:
		image = PIL.Image.open(cached_path)
	except Exception:
		return MissingImage(reason="decode failed")

	# Trim white edges
	trimmed = _trim_white_edges(image)
	if trimmed is None:
		return MissingImage(reason="blank image")

	# Convert to RGB for L* computation (drop alpha if present)
	if trimmed.mode != 'RGB':
		trimmed_rgb = trimmed.convert('RGB')
	else:
		trimmed_rgb = trimmed

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
