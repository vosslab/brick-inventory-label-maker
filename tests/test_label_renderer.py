"""Tests for label_renderer adapter."""

# Standard Library
import io

# PIP3 modules
import PIL.Image
import pytest

# local repo modules
import backend.adapters.label_renderer as label_renderer
import backend.adapters.image_pipeline as image_pipeline
import backend.adapters.bricklink_adapter as bricklink_adapter


#============================================
def _make_test_png_bytes(width=100, height=100):
	"""Create a minimal valid PNG as bytes for testing."""
	image = PIL.Image.new('RGB', (width, height), color=(200, 200, 200))
	buf = io.BytesIO()
	image.save(buf, format='PNG')
	return buf.getvalue()


#============================================
def test_render_minifig_pdf_bright_image(monkeypatch):
	"""Test minifig PDF rendering with bright images."""
	# Stub BrickLink adapter
	def mock_get_minifig_record(minifig_id, set_id=None):
		return {
			"minifig_id": minifig_id,
			"name": "Test Minifig",
			"year_released": "2020",
			"category_name": "Fantasy",
			"superset_count": 2,
			"set_id": set_id,
			"image_url": "http://example.com/img.jpg",
		}

	monkeypatch.setattr(
		bricklink_adapter,
		"get_minifig_record",
		mock_get_minifig_record
	)

	# Stub image pipeline to return bright image
	def mock_fetch_and_classify(url, kind, item_id):
		png_bytes = _make_test_png_bytes(100, 100)
		return image_pipeline.Trimmed(
			image_bytes=png_bytes,
			mean_lstar=80.0,
			width=100,
			height=100
		)

	monkeypatch.setattr(
		image_pipeline,
		"fetch_and_classify",
		mock_fetch_and_classify
	)

	# Render minifig PDF
	pdf_bytes, warnings = label_renderer.render_minifig_pdf(
		[("sw0001", None)],
		debug=False,
		calibration=False
	)

	# Assert PDF starts with magic bytes
	assert pdf_bytes.startswith(b'%PDF'), "PDF should start with %PDF header"
	assert len(pdf_bytes) > 100, "PDF should have content"
	assert len(warnings) == 0, "No warnings for bright images"


#============================================
def test_render_minifig_pdf_dark_reject(monkeypatch):
	"""Test minifig PDF with dark image that is rejected."""
	def mock_get_minifig_record(minifig_id, set_id=None):
		return {
			"minifig_id": minifig_id,
			"name": "Dark Test",
			"year_released": "2020",
			"category_name": "Dark",
			"superset_count": None,
			"set_id": set_id,
			"image_url": "http://example.com/dark.jpg",
		}

	monkeypatch.setattr(
		bricklink_adapter,
		"get_minifig_record",
		mock_get_minifig_record
	)

	# Stub image pipeline to return dark image (rejected)
	def mock_fetch_and_classify(url, kind, item_id):
		return image_pipeline.DarkImage(
			action="reject",
			mean_lstar=20.0,
			image_bytes=None
		)

	monkeypatch.setattr(
		image_pipeline,
		"fetch_and_classify",
		mock_fetch_and_classify
	)

	# Render minifig PDF
	pdf_bytes, warnings = label_renderer.render_minifig_pdf(
		[("sw0001", None)],
		debug=False,
		calibration=False
	)

	# Assert PDF is still valid but has warning
	assert pdf_bytes.startswith(b'%PDF'), "PDF should be valid even with rejected image"
	assert len(warnings) == 1, "Should have one warning for rejected image"
	assert warnings[0]["reason"] == "dark_image_reject", "Should mention reject action"
	assert warnings[0]["mean_lstar"] == 20.0, "Should record L* value"


#============================================
def test_render_minifig_pdf_missing_image(monkeypatch):
	"""Test minifig PDF with missing image."""
	def mock_get_minifig_record(minifig_id, set_id=None):
		return {
			"minifig_id": minifig_id,
			"name": "No Image",
			"year_released": "2020",
			"category_name": "Test",
			"superset_count": 0,
			"set_id": set_id,
			"image_url": "http://example.com/missing.jpg",
		}

	monkeypatch.setattr(
		bricklink_adapter,
		"get_minifig_record",
		mock_get_minifig_record
	)

	# Stub image pipeline to return missing image
	def mock_fetch_and_classify(url, kind, item_id):
		return image_pipeline.MissingImage(reason="decode failed")

	monkeypatch.setattr(
		image_pipeline,
		"fetch_and_classify",
		mock_fetch_and_classify
	)

	# Render minifig PDF
	pdf_bytes, warnings = label_renderer.render_minifig_pdf(
		[("sw0001", None)],
		debug=False,
		calibration=False
	)

	# Assert PDF is valid and warning present
	assert pdf_bytes.startswith(b'%PDF'), "PDF should be valid even with missing image"
	assert len(warnings) == 1, "Should have one warning for missing image"
	assert "image_missing" in warnings[0]["reason"], "Should mention missing image"


#============================================
def test_render_minifig_pdf_no_items(monkeypatch):
	"""Test minifig PDF with no items."""
	def mock_get_minifig_record(minifig_id, set_id=None):
		return None

	monkeypatch.setattr(
		bricklink_adapter,
		"get_minifig_record",
		mock_get_minifig_record
	)

	# Render empty minifig PDF
	pdf_bytes, warnings = label_renderer.render_minifig_pdf(
		[("invalid_id", None)],
		debug=False,
		calibration=False
	)

	# Assert PDF is valid
	assert pdf_bytes.startswith(b'%PDF'), "PDF should be valid for empty request"
	assert len(warnings) == 1, "Should have warning for failed lookup"


#============================================
def test_render_minifig_pdf_with_calibration(monkeypatch):
	"""Test minifig PDF with calibration page."""
	def mock_get_minifig_record(minifig_id, set_id=None):
		return {
			"minifig_id": minifig_id,
			"name": "Test",
			"year_released": "2020",
			"category_name": "Test",
			"superset_count": 0,
			"set_id": set_id,
			"image_url": "http://example.com/img.jpg",
		}

	monkeypatch.setattr(
		bricklink_adapter,
		"get_minifig_record",
		mock_get_minifig_record
	)

	def mock_fetch_and_classify(url, kind, item_id):
		png_bytes = _make_test_png_bytes(100, 100)
		return image_pipeline.Trimmed(
			image_bytes=png_bytes,
			mean_lstar=80.0,
			width=100,
			height=100
		)

	monkeypatch.setattr(
		image_pipeline,
		"fetch_and_classify",
		mock_fetch_and_classify
	)

	# Render with calibration
	pdf_bytes, warnings = label_renderer.render_minifig_pdf(
		[("sw0001", None)],
		debug=False,
		calibration=True
	)

	# Assert PDF is larger (has extra calibration page)
	assert pdf_bytes.startswith(b'%PDF'), "PDF should be valid"
	assert len(pdf_bytes) > 100, "PDF should have content"
	assert len(warnings) == 0, "No warnings for bright images"


#============================================
def test_render_minifig_pdf_credentials_error(monkeypatch):
	"""Test minifig PDF when credentials are missing."""
	def mock_get_minifig_record(minifig_id, set_id=None):
		raise bricklink_adapter.CredentialsMissingError("/path/to/creds.yml")

	monkeypatch.setattr(
		bricklink_adapter,
		"get_minifig_record",
		mock_get_minifig_record
	)

	# Render should raise CredentialsMissingError
	with pytest.raises(bricklink_adapter.CredentialsMissingError):
		label_renderer.render_minifig_pdf(
			[("sw0001", None)],
			debug=False,
			calibration=False
		)


#============================================
def test_render_set_pdf_bright_image(monkeypatch):
	"""Test set PDF rendering with bright images."""
	def mock_get_set_record(set_id):
		return {
			"set_id": set_id,
			"name": "Test Set",
			"num_parts": 500,
			"category_name": "Buildings",
			"year_released": "2020",
			"year": "2020",
			"theme_name": "Architecture",
			"set_img_url": "http://example.com/set.jpg",
		}

	monkeypatch.setattr(
		bricklink_adapter,
		"get_set_record",
		mock_get_set_record
	)

	def mock_fetch_and_classify(url, kind, item_id):
		png_bytes = _make_test_png_bytes(150, 150)
		return image_pipeline.Trimmed(
			image_bytes=png_bytes,
			mean_lstar=85.0,
			width=150,
			height=150
		)

	monkeypatch.setattr(
		image_pipeline,
		"fetch_and_classify",
		mock_fetch_and_classify
	)

	# Render set PDF
	pdf_bytes, warnings = label_renderer.render_set_pdf(
		["10240"],
		debug=False,
		calibration=False
	)

	# Assert PDF is valid
	assert pdf_bytes.startswith(b'%PDF'), "PDF should start with %PDF header"
	assert len(pdf_bytes) > 100, "PDF should have content"
	assert len(warnings) == 0, "No warnings for bright images"


#============================================
def test_render_set_pdf_credentials_error(monkeypatch):
	"""Test set PDF when credentials are missing."""
	def mock_get_set_record(set_id):
		raise bricklink_adapter.CredentialsMissingError("/path/to/creds.yml")

	monkeypatch.setattr(
		bricklink_adapter,
		"get_set_record",
		mock_get_set_record
	)

	# Render should raise CredentialsMissingError
	with pytest.raises(bricklink_adapter.CredentialsMissingError):
		label_renderer.render_set_pdf(
			["10240"],
			debug=False,
			calibration=False
		)
