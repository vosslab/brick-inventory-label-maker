"""Tests for image_pipeline module."""

# Standard Library
import io
from unittest import mock

# PIP3 modules
import PIL.Image

# local repo modules
import backend.adapters.image_pipeline as image_pipeline
import libbrick.image_cache


#============================================
# Helpers for test fixtures


def _make_png_with_border(
	width: int = 200,
	height: int = 200,
	border_size: int = 30,
	border_color: tuple = (255, 255, 255),
	center_color: tuple = (0, 0, 255)
) -> bytes:
	"""
	Create a PNG with a colored border and contrasting center.

	Args:
		width: Image width in pixels.
		height: Image height in pixels.
		border_size: Width of border in pixels.
		border_color: RGB tuple for border.
		center_color: RGB tuple for center.

	Returns:
		PNG bytes.
	"""
	img = PIL.Image.new('RGB', (width, height), border_color)
	# Draw center rectangle
	for y in range(border_size, height - border_size):
		for x in range(border_size, width - border_size):
			img.putpixel((x, y), center_color)
	buf = io.BytesIO()
	img.save(buf, format='PNG')
	return buf.getvalue()


def _make_solid_png(
	width: int = 100,
	height: int = 100,
	color: tuple = (0, 0, 0)
) -> bytes:
	"""Create a solid-color PNG."""
	img = PIL.Image.new('RGB', (width, height), color)
	buf = io.BytesIO()
	img.save(buf, format='PNG')
	return buf.getvalue()


#============================================
# Tests


def test_trim_removes_white_border(tmp_path, monkeypatch):
	"""Trim should remove white borders and preserve center."""
	png_bytes = _make_png_with_border(
		width=200,
		height=200,
		border_size=30,
		border_color=(255, 255, 255),
		center_color=(200, 200, 255)
	)

	# Write PNG to a temp file
	png_path = tmp_path / "image.png"
	png_path.write_bytes(png_bytes)

	def mock_get_cached(url, kind, item_id):
		return str(png_path)

	mock_sleep = mock.Mock()
	monkeypatch.setattr(libbrick.image_cache, 'get_cached_image', mock_get_cached)
	monkeypatch.setattr('time.sleep', mock_sleep)

	result = image_pipeline.fetch_and_classify('http://example.com/image.png', 'minifig', 'item1')

	assert isinstance(result, image_pipeline.Trimmed)
	# Center should be roughly 140x140 (200 - 30*2), allow ±4 px tolerance
	assert 136 <= result.width <= 144, f"width={result.width}"
	assert 136 <= result.height <= 144, f"height={result.height}"
	mock_sleep.assert_called_once()


def test_pure_black_returns_dark_image_warn_by_default(tmp_path, monkeypatch):
	"""Pure black PNG should return DarkImage with warn action."""
	png_bytes = _make_solid_png(width=100, height=100, color=(0, 0, 0))

	png_path = tmp_path / "black.png"
	png_path.write_bytes(png_bytes)

	def mock_get_cached(url, kind, item_id):
		return str(png_path)

	mock_sleep = mock.Mock()
	monkeypatch.setattr(libbrick.image_cache, 'get_cached_image', mock_get_cached)
	monkeypatch.setattr('time.sleep', mock_sleep)

	result = image_pipeline.fetch_and_classify('http://example.com/black.png', 'set', 'item1')

	assert isinstance(result, image_pipeline.DarkImage)
	assert result.action == 'warn'
	assert result.mean_lstar < 5
	assert result.image_bytes is not None
	mock_sleep.assert_called_once()


def test_reject_action_drops_image_bytes(tmp_path, monkeypatch):
	"""DARK_IMAGE_ACTION=reject should set image_bytes to None."""
	png_bytes = _make_solid_png(width=100, height=100, color=(0, 0, 0))

	png_path = tmp_path / "black.png"
	png_path.write_bytes(png_bytes)

	def mock_get_cached(url, kind, item_id):
		return str(png_path)

	mock_sleep = mock.Mock()
	monkeypatch.setattr(libbrick.image_cache, 'get_cached_image', mock_get_cached)
	monkeypatch.setattr('time.sleep', mock_sleep)
	monkeypatch.setenv('DARK_IMAGE_ACTION', 'reject')

	result = image_pipeline.fetch_and_classify('http://example.com/black.png', 'minifig', 'item1')

	assert isinstance(result, image_pipeline.DarkImage)
	assert result.action == 'reject'
	assert result.image_bytes is None
	mock_sleep.assert_called_once()


def test_ignore_action_returns_dark_image_with_bytes(tmp_path, monkeypatch):
	"""DARK_IMAGE_ACTION=ignore should return DarkImage with bytes."""
	png_bytes = _make_solid_png(width=100, height=100, color=(0, 0, 0))

	png_path = tmp_path / "black.png"
	png_path.write_bytes(png_bytes)

	def mock_get_cached(url, kind, item_id):
		return str(png_path)

	mock_sleep = mock.Mock()
	monkeypatch.setattr(libbrick.image_cache, 'get_cached_image', mock_get_cached)
	monkeypatch.setattr('time.sleep', mock_sleep)
	monkeypatch.setenv('DARK_IMAGE_ACTION', 'ignore')

	result = image_pipeline.fetch_and_classify('http://example.com/black.png', 'set', 'item1')

	assert isinstance(result, image_pipeline.DarkImage)
	assert result.action == 'ignore'
	assert result.image_bytes is not None
	mock_sleep.assert_called_once()


def test_pure_white_returns_missing_image(tmp_path, monkeypatch):
	"""Pure white PNG should return MissingImage (blank)."""
	png_bytes = _make_solid_png(width=100, height=100, color=(255, 255, 255))

	png_path = tmp_path / "white.png"
	png_path.write_bytes(png_bytes)

	def mock_get_cached(url, kind, item_id):
		return str(png_path)

	mock_sleep = mock.Mock()
	monkeypatch.setattr(libbrick.image_cache, 'get_cached_image', mock_get_cached)
	monkeypatch.setattr('time.sleep', mock_sleep)

	result = image_pipeline.fetch_and_classify('http://example.com/white.png', 'minifig', 'item1')

	assert isinstance(result, image_pipeline.MissingImage)
	assert result.reason == 'blank image'
	mock_sleep.assert_called_once()


def test_get_cached_image_failure_returns_missing_image(monkeypatch):
	"""get_cached_image raising an exception should return MissingImage."""
	def mock_get_cached_error(url, kind, item_id):
		raise RuntimeError('network error')

	mock_sleep = mock.Mock()
	monkeypatch.setattr(libbrick.image_cache, 'get_cached_image', mock_get_cached_error)
	monkeypatch.setattr('time.sleep', mock_sleep)

	result = image_pipeline.fetch_and_classify('http://example.com/fail.png', 'set', 'item1')

	assert isinstance(result, image_pipeline.MissingImage)
	assert 'network error' in result.reason
	mock_sleep.assert_called_once()


def test_invalid_kind_raises_value_error(monkeypatch):
	"""Invalid kind should raise ValueError before any fetch."""
	mock_sleep = mock.Mock()
	mock_get_cached = mock.Mock()
	monkeypatch.setattr('time.sleep', mock_sleep)
	monkeypatch.setattr(libbrick.image_cache, 'get_cached_image', mock_get_cached)

	try:
		image_pipeline.fetch_and_classify('http://example.com/image.png', 'invalid_kind', 'item1')
		assert False, "Should have raised ValueError"
	except ValueError as e:
		assert 'minifig' in str(e) or 'set' in str(e)

	# Sleep should NOT be called because validation happens first
	mock_sleep.assert_not_called()
	mock_get_cached.assert_not_called()


def test_random_sleep_called_before_fetch(tmp_path, monkeypatch):
	"""Random sleep should be called once before get_cached_image."""
	png_bytes = _make_solid_png(width=100, height=100, color=(200, 200, 200))

	png_path = tmp_path / "image.png"
	png_path.write_bytes(png_bytes)

	call_order = []

	def mock_sleep(duration):
		call_order.append(('sleep', duration))
		assert isinstance(duration, float)
		assert 0 <= duration <= 1

	def mock_get_cached(url, kind, item_id):
		call_order.append(('get_cached_image', url))
		return str(png_path)

	monkeypatch.setattr('time.sleep', mock_sleep)
	monkeypatch.setattr(libbrick.image_cache, 'get_cached_image', mock_get_cached)

	result = image_pipeline.fetch_and_classify('http://example.com/image.png', 'minifig', 'item1')

	assert isinstance(result, image_pipeline.Trimmed)
	# Verify call order: sleep should come before get_cached_image
	assert len(call_order) == 2
	assert call_order[0][0] == 'sleep'
	assert call_order[1][0] == 'get_cached_image'
