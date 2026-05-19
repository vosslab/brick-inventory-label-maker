"""Tests for streaming /api/labels/*/stream HTTP endpoints."""

# Standard Library
import base64
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
def test_stream_minifig_labels_success(client, monkeypatch):
	"""Test successful minifig label streaming."""
	pdf_bytes = _make_test_pdf_bytes(5000)

	def mock_render_minifig_pdf(pairs, debug, calibration, on_progress=None):
		if on_progress:
			on_progress({"type": "start", "mode": "minifig", "count": 2})
			on_progress({"type": "item_start", "id": "sw0001", "index": 1, "total": 2})
			on_progress({"type": "item_done", "id": "sw0001", "name": "sw0001", "warning": None})
			on_progress({"type": "item_start", "id": "sw0002", "index": 2, "total": 2})
			on_progress({"type": "item_done", "id": "sw0002", "name": "sw0002", "warning": None})
			on_progress({"type": "render_start"})
			on_progress({"type": "done", "warnings_count": 0, "pages": 1})
		return (pdf_bytes, [])

	monkeypatch.setattr(
		label_renderer,
		"render_minifig_pdf",
		mock_render_minifig_pdf
	)

	response = client.post(
		"/api/labels/minifigs/stream",
		json={
			"ids": ["sw0001", "sw0002"],
			"debug": False,
			"calibration": False
		}
	)

	assert response.status_code == 200, f"Expected 200, got {response.status_code}"
	assert "text/event-stream" in response.headers["content-type"], "Should return SSE"

	# Parse SSE frames
	body = response.text
	frames = body.split("\n\n")
	frames = [f.strip() for f in frames if f.strip()]

	# Should have at least: start, item_start, item_done, render_start, done
	assert len(frames) >= 5, f"Expected at least 5 SSE frames, got {len(frames)}"

	# Verify we have progress and done events
	progress_count = sum(1 for f in frames if f.startswith("event: progress"))
	done_count = sum(1 for f in frames if f.startswith("event: done"))

	assert progress_count > 0, "Should have progress events"
	assert done_count == 1, "Should have exactly one done event"

	# Parse the done event to get PDF
	for frame in frames:
		if frame.startswith("event: done"):
			# Extract the data line
			lines = frame.split("\n")
			data_line = [l for l in lines if l.startswith("data: ")][0]
			json_str = data_line[6:]  # Remove "data: " prefix
			event_data = json.loads(json_str)

			assert "pdf_b64" in event_data, "Done event should have pdf_b64"
			assert "warnings" in event_data, "Done event should have warnings"

			# Decode and verify PDF
			decoded_pdf = base64.b64decode(event_data["pdf_b64"])
			assert decoded_pdf.startswith(b"%PDF"), "Decoded PDF should start with %PDF magic"
			break


#============================================
def test_stream_set_labels_success(client, monkeypatch):
	"""Test successful set label streaming."""
	pdf_bytes = _make_test_pdf_bytes(5000)

	def mock_render_set_pdf(set_ids, debug, calibration, on_progress=None):
		if on_progress:
			on_progress({"type": "start", "mode": "set", "count": 1})
			on_progress({"type": "item_start", "id": "10240", "index": 1, "total": 1})
			on_progress({"type": "item_done", "id": "10240", "name": "Star Destroyer", "warning": None})
			on_progress({"type": "render_start"})
			on_progress({"type": "done", "warnings_count": 0, "pages": 1})
		return (pdf_bytes, [])

	monkeypatch.setattr(
		label_renderer,
		"render_set_pdf",
		mock_render_set_pdf
	)

	response = client.post(
		"/api/labels/sets/stream",
		json={
			"ids": ["10240"],
			"debug": False,
			"calibration": False
		}
	)

	assert response.status_code == 200, f"Expected 200, got {response.status_code}"
	assert "text/event-stream" in response.headers["content-type"], "Should return SSE"

	body = response.text
	frames = body.split("\n\n")
	frames = [f.strip() for f in frames if f.strip()]

	assert len(frames) >= 5, f"Expected at least 5 SSE frames, got {len(frames)}"

	done_count = sum(1 for f in frames if f.startswith("event: done"))
	assert done_count == 1, "Should have exactly one done event"


#============================================
def test_stream_minifig_labels_credentials_missing(client, monkeypatch):
	"""Test minifig streaming with missing credentials."""

	def mock_render_minifig_pdf(pairs, debug, calibration, on_progress=None):
		raise bricklink_adapter.CredentialsMissingError("/path/to/bricklink_api_private.yml")

	monkeypatch.setattr(
		label_renderer,
		"render_minifig_pdf",
		mock_render_minifig_pdf
	)

	response = client.post(
		"/api/labels/minifigs/stream",
		json={
			"ids": ["sw0001"],
			"debug": False,
			"calibration": False
		}
	)

	assert response.status_code == 200, "Stream should return 200 even with error"

	body = response.text
	frames = body.split("\n\n")
	frames = [f.strip() for f in frames if f.strip()]

	# Should have error event
	error_count = sum(1 for f in frames if f.startswith("event: error"))
	assert error_count == 1, "Should have error event"

	# Verify error content
	for frame in frames:
		if frame.startswith("event: error"):
			lines = frame.split("\n")
			data_line = [l for l in lines if l.startswith("data: ")][0]
			json_str = data_line[6:]
			event_data = json.loads(json_str)

			assert event_data["error"] == "credentials_missing", "Should report credentials_missing"
			assert "expected_path" in event_data, "Should have expected_path"
			break
