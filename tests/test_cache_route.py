"""Tests for cache route endpoints."""

# Standard Library
import os
import tempfile

# PIP3 modules
import PIL.Image
from fastapi.testclient import TestClient

# local repo modules
import backend.app
import backend.routes.cache


#============================================


def test_cache_route_get_raw_image_success(monkeypatch):
	"""Test successful GET /api/cache/{kind}/{item_id}/raw.jpg."""
	with tempfile.TemporaryDirectory() as tmpdir:
		# Create images/raw directory and a test JPG
		images_dir = os.path.join(tmpdir, 'images')
		raw_dir = os.path.join(images_dir, 'raw')
		os.makedirs(raw_dir)

		# Write a test JPG file
		test_jpg_path = os.path.join(raw_dir, 'minifig_sw1113.jpg')
		img = PIL.Image.new('RGB', (100, 100), color='red')
		img.save(test_jpg_path, format='JPEG')

		# Monkeypatch _get_images_dir to return our temp dir
		monkeypatch.setattr(backend.routes.cache, '_get_images_dir', lambda: images_dir)

		# Create app and test client
		app = backend.app.create_app()
		client = TestClient(app)

		# Test GET request
		response = client.get('/api/cache/minifig/sw1113/raw.jpg')
		assert response.status_code == 200
		assert response.headers['content-type'] == 'image/jpeg'
		assert len(response.content) > 0


#============================================


def test_cache_route_get_processed_image_success(monkeypatch):
	"""Test successful GET /api/cache/{kind}/{item_id}/processed.png."""
	with tempfile.TemporaryDirectory() as tmpdir:
		# Create images/processed directory and a test PNG
		images_dir = os.path.join(tmpdir, 'images')
		processed_dir = os.path.join(images_dir, 'processed')
		os.makedirs(processed_dir)

		# Write a test PNG file
		test_png_path = os.path.join(processed_dir, 'minifig_sw1113.png')
		img = PIL.Image.new('RGBA', (100, 100), color=(255, 0, 0, 255))
		img.save(test_png_path, format='PNG')

		# Monkeypatch _get_images_dir to return our temp dir
		monkeypatch.setattr(backend.routes.cache, '_get_images_dir', lambda: images_dir)

		# Create app and test client
		app = backend.app.create_app()
		client = TestClient(app)

		# Test GET request
		response = client.get('/api/cache/minifig/sw1113/processed.png')
		assert response.status_code == 200
		assert response.headers['content-type'] == 'image/png'
		assert len(response.content) > 0


#============================================


def test_cache_route_raw_image_not_found(monkeypatch):
	"""Test 404 when raw image does not exist."""
	with tempfile.TemporaryDirectory() as tmpdir:
		# Create images directory but no raw subdirectory
		images_dir = os.path.join(tmpdir, 'images')
		os.makedirs(images_dir)

		monkeypatch.setattr(backend.routes.cache, '_get_images_dir', lambda: images_dir)

		app = backend.app.create_app()
		client = TestClient(app)

		response = client.get('/api/cache/minifig/nonexistent/raw.jpg')
		assert response.status_code == 404


#============================================


def test_cache_route_processed_image_not_found(monkeypatch):
	"""Test 404 when processed image does not exist."""
	with tempfile.TemporaryDirectory() as tmpdir:
		# Create images directory but no processed subdirectory
		images_dir = os.path.join(tmpdir, 'images')
		os.makedirs(images_dir)

		monkeypatch.setattr(backend.routes.cache, '_get_images_dir', lambda: images_dir)

		app = backend.app.create_app()
		client = TestClient(app)

		response = client.get('/api/cache/minifig/nonexistent/processed.png')
		assert response.status_code == 404


#============================================


def test_cache_route_raw_image_bad_kind(monkeypatch):
	"""Test 400 when kind is invalid for raw image."""
	with tempfile.TemporaryDirectory() as tmpdir:
		images_dir = os.path.join(tmpdir, 'images')
		os.makedirs(images_dir)

		monkeypatch.setattr(backend.routes.cache, '_get_images_dir', lambda: images_dir)

		app = backend.app.create_app()
		client = TestClient(app)

		response = client.get('/api/cache/invalid/sw1113/raw.jpg')
		assert response.status_code == 400


#============================================


def test_cache_route_processed_image_bad_kind(monkeypatch):
	"""Test 400 when kind is invalid for processed image."""
	with tempfile.TemporaryDirectory() as tmpdir:
		images_dir = os.path.join(tmpdir, 'images')
		os.makedirs(images_dir)

		monkeypatch.setattr(backend.routes.cache, '_get_images_dir', lambda: images_dir)

		app = backend.app.create_app()
		client = TestClient(app)

		response = client.get('/api/cache/invalid/sw1113/processed.png')
		assert response.status_code == 400


#============================================


def test_cache_route_set_kind_raw_image(monkeypatch):
	"""Test GET /api/cache/set/{item_id}/raw.jpg with set kind."""
	with tempfile.TemporaryDirectory() as tmpdir:
		images_dir = os.path.join(tmpdir, 'images')
		raw_dir = os.path.join(images_dir, 'raw')
		os.makedirs(raw_dir)

		# Write a test JPG file for a set
		test_jpg_path = os.path.join(raw_dir, 'set_10001.jpg')
		img = PIL.Image.new('RGB', (100, 100), color='blue')
		img.save(test_jpg_path, format='JPEG')

		monkeypatch.setattr(backend.routes.cache, '_get_images_dir', lambda: images_dir)

		app = backend.app.create_app()
		client = TestClient(app)

		response = client.get('/api/cache/set/10001/raw.jpg')
		assert response.status_code == 200
		assert response.headers['content-type'] == 'image/jpeg'
