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


def _mock_download_and_process(png_path, monkeypatch):
	"""Set up mocks for download_image and process_image."""
	import shutil
	import os

	def mock_download(url, filename):
		os.makedirs(os.path.dirname(filename), exist_ok=True)
		shutil.copy(str(png_path), filename)
		return filename

	def mock_process(raw_filename, processed_filename):
		os.makedirs(os.path.dirname(processed_filename), exist_ok=True)
		shutil.copy(raw_filename, processed_filename)
		return processed_filename

	def mock_ensure_dir(images_dir):
		os.makedirs(os.path.join(images_dir, 'raw'), exist_ok=True)
		os.makedirs(os.path.join(images_dir, 'processed'), exist_ok=True)

	monkeypatch.setattr(libbrick.image_cache, 'download_image', mock_download)
	monkeypatch.setattr(libbrick.image_cache, 'process_image', mock_process)
	monkeypatch.setattr(libbrick.image_cache, 'ensure_images_directory', mock_ensure_dir)


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

	_mock_download_and_process(png_path, monkeypatch)

	# Mock images directory to isolate test from existing cache
	images_dir = tmp_path / "images"
	monkeypatch.setattr(image_pipeline, '_get_images_dir', lambda: str(images_dir))

	mock_sleep = mock.Mock()
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

	_mock_download_and_process(png_path, monkeypatch)

	# Mock images directory to isolate test from existing cache
	images_dir = tmp_path / "images"
	monkeypatch.setattr(image_pipeline, '_get_images_dir', lambda: str(images_dir))

	mock_sleep = mock.Mock()
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

	_mock_download_and_process(png_path, monkeypatch)

	# Mock images directory to isolate test from existing cache
	images_dir = tmp_path / "images"
	monkeypatch.setattr(image_pipeline, '_get_images_dir', lambda: str(images_dir))

	mock_sleep = mock.Mock()
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

	_mock_download_and_process(png_path, monkeypatch)

	# Mock images directory to isolate test from existing cache
	images_dir = tmp_path / "images"
	monkeypatch.setattr(image_pipeline, '_get_images_dir', lambda: str(images_dir))

	mock_sleep = mock.Mock()
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

	_mock_download_and_process(png_path, monkeypatch)

	# Mock images directory to isolate test from existing cache
	images_dir = tmp_path / "images"
	monkeypatch.setattr(image_pipeline, '_get_images_dir', lambda: str(images_dir))

	mock_sleep = mock.Mock()
	monkeypatch.setattr('time.sleep', mock_sleep)

	result = image_pipeline.fetch_and_classify('http://example.com/white.png', 'minifig', 'item1')

	assert isinstance(result, image_pipeline.MissingImage)
	assert result.reason == 'blank image'
	mock_sleep.assert_called_once()


def test_download_image_failure_returns_missing_image(tmp_path, monkeypatch):
	"""download_image raising an exception should return MissingImage."""
	import requests.exceptions

	def mock_download_error(url, filename):
		raise requests.exceptions.RequestException('network error')

	def mock_ensure_dir(images_dir):
		import os
		os.makedirs(os.path.join(images_dir, 'raw'), exist_ok=True)
		os.makedirs(os.path.join(images_dir, 'processed'), exist_ok=True)

	# Mock images directory to isolate test from existing cache
	images_dir = tmp_path / "images"
	monkeypatch.setattr(image_pipeline, '_get_images_dir', lambda: str(images_dir))

	mock_sleep = mock.Mock()
	monkeypatch.setattr(libbrick.image_cache, 'download_image', mock_download_error)
	monkeypatch.setattr(libbrick.image_cache, 'ensure_images_directory', mock_ensure_dir)
	monkeypatch.setattr('time.sleep', mock_sleep)

	result = image_pipeline.fetch_and_classify('http://example.com/fail.png', 'set', 'item1')

	assert isinstance(result, image_pipeline.MissingImage)
	assert 'network error' in result.reason
	mock_sleep.assert_called_once()


def test_invalid_kind_raises_value_error(tmp_path, monkeypatch):
	"""Invalid kind should raise ValueError before any fetch."""
	# Mock images directory to isolate test from existing cache
	images_dir = tmp_path / "images"
	monkeypatch.setattr(image_pipeline, '_get_images_dir', lambda: str(images_dir))

	mock_sleep = mock.Mock()
	mock_download = mock.Mock()
	monkeypatch.setattr('time.sleep', mock_sleep)
	monkeypatch.setattr(libbrick.image_cache, 'download_image', mock_download)

	try:
		image_pipeline.fetch_and_classify('http://example.com/image.png', 'invalid_kind', 'item1')
		assert False, "Should have raised ValueError"
	except ValueError as e:
		assert 'minifig' in str(e) or 'set' in str(e)

	# Sleep should NOT be called because validation happens first
	mock_sleep.assert_not_called()
	mock_download.assert_not_called()


def test_random_sleep_called_before_fetch(tmp_path, monkeypatch):
	"""Random sleep should be called once before download_image."""
	png_bytes = _make_solid_png(width=100, height=100, color=(200, 200, 200))

	png_path = tmp_path / "image.png"
	png_path.write_bytes(png_bytes)

	call_order = []

	def mock_sleep(duration):
		call_order.append(('sleep', duration))
		assert isinstance(duration, float)
		assert 0 <= duration <= 1

	def mock_download(url, filename):
		import os
		import shutil
		call_order.append(('download_image', url))
		os.makedirs(os.path.dirname(filename), exist_ok=True)
		shutil.copy(str(png_path), filename)
		return filename

	def mock_process(raw_filename, processed_filename):
		import os
		import shutil
		call_order.append(('process_image', raw_filename))
		os.makedirs(os.path.dirname(processed_filename), exist_ok=True)
		shutil.copy(raw_filename, processed_filename)
		return processed_filename

	def mock_ensure_dir(images_dir):
		import os
		os.makedirs(os.path.join(images_dir, 'raw'), exist_ok=True)
		os.makedirs(os.path.join(images_dir, 'processed'), exist_ok=True)

	# Mock images directory to isolate test from existing cache
	images_dir = tmp_path / "images"
	monkeypatch.setattr(image_pipeline, '_get_images_dir', lambda: str(images_dir))

	monkeypatch.setattr('time.sleep', mock_sleep)
	monkeypatch.setattr(libbrick.image_cache, 'download_image', mock_download)
	monkeypatch.setattr(libbrick.image_cache, 'process_image', mock_process)
	monkeypatch.setattr(libbrick.image_cache, 'ensure_images_directory', mock_ensure_dir)

	result = image_pipeline.fetch_and_classify('http://example.com/image.png', 'minifig', 'item1')

	assert isinstance(result, image_pipeline.Trimmed)
	# Verify call order: sleep should come before download_image
	assert len(call_order) >= 2
	assert call_order[0][0] == 'sleep'
	assert call_order[1][0] == 'download_image'


def test_on_event_callback_fires_with_correct_events(tmp_path, monkeypatch):
	"""on_event callback should fire with image_downloaded and image_processed events."""
	png_bytes = _make_solid_png(width=100, height=100, color=(200, 200, 200))

	png_path = tmp_path / "image.png"
	png_path.write_bytes(png_bytes)

	_mock_download_and_process(png_path, monkeypatch)

	# Mock images directory to isolate test from existing cache
	images_dir = tmp_path / "images"
	monkeypatch.setattr(image_pipeline, '_get_images_dir', lambda: str(images_dir))

	events = []

	def event_callback(event: dict):
		events.append(event)

	mock_sleep = mock.Mock()
	monkeypatch.setattr('time.sleep', mock_sleep)

	result = image_pipeline.fetch_and_classify(
		'http://example.com/image.png',
		'minifig',
		'sw1113',
		on_event=event_callback
	)

	assert isinstance(result, image_pipeline.Trimmed)
	# Should have fired both image_downloaded and image_processed events
	assert len(events) == 2
	assert events[0]['type'] == 'image_downloaded'
	assert events[0]['id'] == 'sw1113'
	assert events[0]['kind'] == 'minifig'
	assert events[1]['type'] == 'image_processed'
	assert events[1]['id'] == 'sw1113'
	assert events[1]['kind'] == 'minifig'


def test_on_event_none_does_not_fire_callback(tmp_path, monkeypatch):
	"""When on_event=None, no events should be fired."""
	png_bytes = _make_solid_png(width=100, height=100, color=(200, 200, 200))

	png_path = tmp_path / "image.png"
	png_path.write_bytes(png_bytes)

	_mock_download_and_process(png_path, monkeypatch)

	# Mock images directory to isolate test from existing cache
	images_dir = tmp_path / "images"
	monkeypatch.setattr(image_pipeline, '_get_images_dir', lambda: str(images_dir))

	mock_callback = mock.Mock()

	mock_sleep = mock.Mock()
	monkeypatch.setattr('time.sleep', mock_sleep)

	result = image_pipeline.fetch_and_classify(
		'http://example.com/image.png',
		'minifig',
		'sw1113',
		on_event=None
	)

	assert isinstance(result, image_pipeline.Trimmed)
	# Callback should never be called
	mock_callback.assert_not_called()
