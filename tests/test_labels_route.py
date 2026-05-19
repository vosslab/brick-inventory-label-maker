"""Tests for /api/labels HTTP endpoints."""

# Standard Library
import json

# PIP3 modules
import fastapi.testclient
import pytest

# local repo modules
import backend.app
import backend.adapters.label_renderer as label_renderer
import backend.adapters.bricklink_adapter as bricklink_adapter


#============================================
def _make_test_pdf_bytes(size=1000):
	"""Create minimal PDF bytes for testing."""
	return (b'%PDF-1.4\n' + b'X' * size)


#============================================
@pytest.fixture
def client():
	"""FastAPI test client."""
	app = backend.app.create_app()
	return fastapi.testclient.TestClient(app)


#============================================
def test_post_minifig_labels_success(client, monkeypatch):
	"""Test successful minifig label generation."""
	pdf_bytes = _make_test_pdf_bytes(5000)

	def mock_render_minifig_pdf(pairs, debug, calibration):
		return (pdf_bytes, [])

	monkeypatch.setattr(
		label_renderer,
		"render_minifig_pdf",
		mock_render_minifig_pdf
	)

	response = client.post(
		"/api/labels/minifigs",
		json={
			"ids": ["sw0001", "sw0002"],
			"debug": False,
			"calibration": False
		}
	)

	assert response.status_code == 200, f"Expected 200, got {response.status_code}"
	assert response.headers["content-type"] == "application/pdf", "Should return PDF"
	assert "attachment" in response.headers["content-disposition"], "Should have attachment header"
	assert "labels-minifigs.pdf" in response.headers["content-disposition"], "Should have filename"
	assert "X-Item-Warnings" in response.headers, "Should have warnings header"

	# Parse warnings header
	warnings_json = response.headers["X-Item-Warnings"]
	warnings = json.loads(warnings_json)
	assert isinstance(warnings, list), "Warnings should be a JSON array"
	assert len(warnings) == 0, "Should have no warnings"


#============================================
def test_post_minifig_labels_with_warnings(client, monkeypatch):
	"""Test minifig label generation with warnings."""
	pdf_bytes = _make_test_pdf_bytes(5000)

	def mock_render_minifig_pdf(pairs, debug, calibration):
		warnings = [
			{"id": "sw0001", "reason": "dark_image_warn", "mean_lstar": 30.0},
			{"id": "sw0002", "reason": "image_missing: blank", "mean_lstar": None},
		]
		return (pdf_bytes, warnings)

	monkeypatch.setattr(
		label_renderer,
		"render_minifig_pdf",
		mock_render_minifig_pdf
	)

	response = client.post(
		"/api/labels/minifigs",
		json={
			"ids": ["sw0001", "sw0002"],
			"debug": False,
			"calibration": False
		}
	)

	assert response.status_code == 200, f"Expected 200, got {response.status_code}"

	# Parse warnings header
	warnings_json = response.headers["X-Item-Warnings"]
	warnings = json.loads(warnings_json)
	assert len(warnings) == 2, "Should have two warnings"
	assert warnings[0]["id"] == "sw0001", "First warning should be for sw0001"
	assert warnings[0]["mean_lstar"] == 30.0, "Should preserve L* value"


#============================================
def test_post_minifig_labels_credentials_error(client, monkeypatch):
	"""Test minifig labels endpoint when credentials are missing."""
	def mock_render_minifig_pdf(pairs, debug, calibration):
		raise bricklink_adapter.CredentialsMissingError("/home/user/.bricklink/creds.yml")

	monkeypatch.setattr(
		label_renderer,
		"render_minifig_pdf",
		mock_render_minifig_pdf
	)

	response = client.post(
		"/api/labels/minifigs",
		json={
			"ids": ["sw0001"],
			"debug": False,
			"calibration": False
		}
	)

	assert response.status_code == 400, f"Expected 400, got {response.status_code}"
	body = response.json()
	assert body["error"] == "credentials_missing", "Should indicate credentials error"
	assert "expected_path" in body, "Should include expected path"
	assert "creds.yml" in body["expected_path"], "Should show credential path"


#============================================
def test_post_set_labels_success(client, monkeypatch):
	"""Test successful set label generation."""
	pdf_bytes = _make_test_pdf_bytes(5000)

	def mock_render_set_pdf(set_ids, debug, calibration):
		return (pdf_bytes, [])

	monkeypatch.setattr(
		label_renderer,
		"render_set_pdf",
		mock_render_set_pdf
	)

	response = client.post(
		"/api/labels/sets",
		json={
			"ids": ["10240", "10241"],
			"debug": False,
			"calibration": False
		}
	)

	assert response.status_code == 200, f"Expected 200, got {response.status_code}"
	assert response.headers["content-type"] == "application/pdf", "Should return PDF"
	assert "attachment" in response.headers["content-disposition"], "Should have attachment header"
	assert "labels-sets.pdf" in response.headers["content-disposition"], "Should have filename"
	assert "X-Item-Warnings" in response.headers, "Should have warnings header"

	# Parse warnings header
	warnings_json = response.headers["X-Item-Warnings"]
	warnings = json.loads(warnings_json)
	assert isinstance(warnings, list), "Warnings should be a JSON array"
	assert len(warnings) == 0, "Should have no warnings"


#============================================
def test_post_set_labels_credentials_error(client, monkeypatch):
	"""Test set labels endpoint when credentials are missing."""
	def mock_render_set_pdf(set_ids, debug, calibration):
		raise bricklink_adapter.CredentialsMissingError("/home/user/.bricklink/creds.yml")

	monkeypatch.setattr(
		label_renderer,
		"render_set_pdf",
		mock_render_set_pdf
	)

	response = client.post(
		"/api/labels/sets",
		json={
			"ids": ["10240"],
			"debug": False,
			"calibration": False
		}
	)

	assert response.status_code == 400, f"Expected 400, got {response.status_code}"
	body = response.json()
	assert body["error"] == "credentials_missing", "Should indicate credentials error"
	assert "expected_path" in body, "Should include expected path"


#============================================
def test_post_minifig_labels_with_debug_flag(client, monkeypatch):
	"""Test minifig labels with debug flag enabled."""
	pdf_bytes = _make_test_pdf_bytes(5000)
	captured_args = {}

	def mock_render_minifig_pdf(pairs, debug, calibration):
		captured_args["debug"] = debug
		captured_args["calibration"] = calibration
		return (pdf_bytes, [])

	monkeypatch.setattr(
		label_renderer,
		"render_minifig_pdf",
		mock_render_minifig_pdf
	)

	response = client.post(
		"/api/labels/minifigs",
		json={
			"ids": ["sw0001"],
			"debug": True,
			"calibration": True
		}
	)

	assert response.status_code == 200, f"Expected 200, got {response.status_code}"
	assert captured_args["debug"] is True, "Debug flag should be True"
	assert captured_args["calibration"] is True, "Calibration flag should be True"


#============================================
def test_post_set_labels_with_debug_flag(client, monkeypatch):
	"""Test set labels with debug flag enabled."""
	pdf_bytes = _make_test_pdf_bytes(5000)
	captured_args = {}

	def mock_render_set_pdf(set_ids, debug, calibration):
		captured_args["debug"] = debug
		captured_args["calibration"] = calibration
		return (pdf_bytes, [])

	monkeypatch.setattr(
		label_renderer,
		"render_set_pdf",
		mock_render_set_pdf
	)

	response = client.post(
		"/api/labels/sets",
		json={
			"ids": ["10240"],
			"debug": True,
			"calibration": True
		}
	)

	assert response.status_code == 200, f"Expected 200, got {response.status_code}"
	assert captured_args["debug"] is True, "Debug flag should be True"
	assert captured_args["calibration"] is True, "Calibration flag should be True"
