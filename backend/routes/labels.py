"""HTTP endpoints for PDF label generation."""

# Standard Library
import base64
import json
import queue
import threading

# PIP3 modules
import fastapi
import fastapi.responses

# local repo modules
import backend.schemas as schemas
import backend.adapters.label_renderer as label_renderer
import backend.adapters.bricklink_adapter as bricklink_adapter


router = fastapi.APIRouter(prefix="/api/labels", tags=["labels"])

_WARNINGS_HEADER_LIMIT = 32

# Module-level lock: non-blocking UX guard. If a label job is already in
# flight on this worker, a second request returns HTTP 409 instead of
# queuing. True rembg-RAM serialization lives in vendor's
# libbrick/image_cache.py::process_image via fcntl.LOCK_EX + 600s timeout.
_LABELS_JOB_LOCK = threading.Lock()


#============================================
def _build_warnings_header(warnings: list[dict]) -> str:
	"""Encode warnings list as a JSON string, capped at limit."""
	capped = warnings[:_WARNINGS_HEADER_LIMIT]
	return json.dumps(capped)


#============================================
@router.post("/minifigs")
def post_minifig_labels(req: schemas.LabelRequest) -> fastapi.Response:
	"""
	Generate a 30-up minifig labels PDF.

	POST /api/labels/minifigs
	Content-Type: application/json

	{
	  "ids": ["sw0001", "sw0002"],
	  "debug": false,
	  "calibration": false
	}

	Returns:
	- 200 OK: PDF with X-Item-Warnings header (JSON array of warnings).
	- 400: credentials_missing error with expected file path.
	- 409: job_in_progress error if another label job is already running.
	"""
	if not _LABELS_JOB_LOCK.acquire(blocking=False):
		return fastapi.responses.JSONResponse(
			status_code=409,
			content={
				"error": "job_in_progress",
				"message": "another label job is already running on this worker",
			},
		)

	try:
		pairs = [(item_id, None) for item_id in req.ids]
		try:
			pdf_bytes, warnings = label_renderer.render_minifig_pdf(
				pairs,
				req.debug,
				req.calibration
			)
		except bricklink_adapter.CredentialsMissingError as exc:
			return fastapi.responses.JSONResponse(
				status_code=400,
				content={
					"error": "credentials_missing",
					"expected_path": str(exc)
				},
			)

		headers = {
			"Content-Disposition": "attachment; filename=labels-minifigs.pdf",
			"X-Item-Warnings": _build_warnings_header(warnings),
		}
		return fastapi.Response(
			content=pdf_bytes,
			media_type="application/pdf",
			headers=headers
		)
	finally:
		_LABELS_JOB_LOCK.release()


#============================================
@router.post("/sets")
def post_set_labels(req: schemas.LabelRequest) -> fastapi.Response:
	"""
	Generate a 10-up set labels PDF.

	POST /api/labels/sets
	Content-Type: application/json

	{
	  "ids": ["10240", "10241"],
	  "debug": false,
	  "calibration": false
	}

	Returns:
	- 200 OK: PDF with X-Item-Warnings header (JSON array of warnings).
	- 400: credentials_missing error with expected file path.
	- 409: job_in_progress error if another label job is already running.
	"""
	if not _LABELS_JOB_LOCK.acquire(blocking=False):
		return fastapi.responses.JSONResponse(
			status_code=409,
			content={
				"error": "job_in_progress",
				"message": "another label job is already running on this worker",
			},
		)

	try:
		try:
			pdf_bytes, warnings = label_renderer.render_set_pdf(
				req.ids,
				req.debug,
				req.calibration
			)
		except bricklink_adapter.CredentialsMissingError as exc:
			return fastapi.responses.JSONResponse(
				status_code=400,
				content={
					"error": "credentials_missing",
					"expected_path": str(exc)
				},
			)

		headers = {
			"Content-Disposition": "attachment; filename=labels-sets.pdf",
			"X-Item-Warnings": _build_warnings_header(warnings),
		}
		return fastapi.Response(
			content=pdf_bytes,
			media_type="application/pdf",
			headers=headers
		)
	finally:
		_LABELS_JOB_LOCK.release()


#============================================
def _stream_minifig(
		minifig_pairs: list[tuple[str, str | None]],
		debug: bool,
		calibration: bool
):
	"""
	Generator that streams minifig label rendering progress as SSE.
	Runs renderer in a thread; yields SSE frames from a queue.
	Releases the module-level lock in finally block.
	"""
	try:
		q = queue.Queue()

		def render_thread():
			try:
				def on_progress(event):
					q.put(("progress", event))

				pdf_bytes, warnings = label_renderer.render_minifig_pdf(
					minifig_pairs,
					debug,
					calibration,
					on_progress=on_progress
				)
				q.put(("done", {
					"type": "done",
					"pdf_b64": base64.b64encode(pdf_bytes).decode("utf-8"),
					"warnings": warnings
				}))
			except bricklink_adapter.CredentialsMissingError as exc:
				q.put(("error", {
					"type": "error",
					"error": "credentials_missing",
					"expected_path": str(exc)
				}))
			except Exception as exc:
				q.put(("error", {
					"type": "error",
					"error": "rendering_failed",
					"message": str(exc)
				}))
			finally:
				q.put(("sentinel", None))

		thread = threading.Thread(target=render_thread, daemon=True)
		thread.start()

		while True:
			try:
				msg_type, msg_data = q.get(timeout=300)
			except queue.Empty:
				yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': 'timeout', 'message': 'no progress in 300s'})}\n\n"
				break

			if msg_type == "progress":
				yield f"event: progress\ndata: {json.dumps(msg_data)}\n\n"
			elif msg_type == "done":
				yield f"event: done\ndata: {json.dumps(msg_data)}\n\n"
				break
			elif msg_type == "error":
				yield f"event: error\ndata: {json.dumps(msg_data)}\n\n"
				break
			elif msg_type == "sentinel":
				break
	finally:
		_LABELS_JOB_LOCK.release()


def _stream_set(
		set_ids: list[str],
		debug: bool,
		calibration: bool
):
	"""
	Generator that streams set label rendering progress as SSE.
	Runs renderer in a thread; yields SSE frames from a queue.
	Releases the module-level lock in finally block.
	"""
	try:
		q = queue.Queue()

		def render_thread():
			try:
				def on_progress(event):
					q.put(("progress", event))

				pdf_bytes, warnings = label_renderer.render_set_pdf(
					set_ids,
					debug,
					calibration,
					on_progress=on_progress
				)
				q.put(("done", {
					"type": "done",
					"pdf_b64": base64.b64encode(pdf_bytes).decode("utf-8"),
					"warnings": warnings
				}))
			except bricklink_adapter.CredentialsMissingError as exc:
				q.put(("error", {
					"type": "error",
					"error": "credentials_missing",
					"expected_path": str(exc)
				}))
			except Exception as exc:
				q.put(("error", {
					"type": "error",
					"error": "rendering_failed",
					"message": str(exc)
				}))
			finally:
				q.put(("sentinel", None))

		thread = threading.Thread(target=render_thread, daemon=True)
		thread.start()

		while True:
			try:
				msg_type, msg_data = q.get(timeout=300)
			except queue.Empty:
				yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': 'timeout', 'message': 'no progress in 300s'})}\n\n"
				break

			if msg_type == "progress":
				yield f"event: progress\ndata: {json.dumps(msg_data)}\n\n"
			elif msg_type == "done":
				yield f"event: done\ndata: {json.dumps(msg_data)}\n\n"
				break
			elif msg_type == "error":
				yield f"event: error\ndata: {json.dumps(msg_data)}\n\n"
				break
			elif msg_type == "sentinel":
				break
	finally:
		_LABELS_JOB_LOCK.release()


#============================================
@router.post("/minifigs/stream")
def post_minifig_labels_stream(req: schemas.LabelRequest) -> fastapi.Response:
	"""
	Stream minifig labels PDF with per-item progress updates.

	POST /api/labels/minifigs/stream
	Content-Type: application/json

	Returns: text/event-stream with progress events, final done event carries PDF as base64.
	Or 409 if another label job is already running.
	"""
	if not _LABELS_JOB_LOCK.acquire(blocking=False):
		return fastapi.responses.JSONResponse(
			status_code=409,
			content={
				"error": "job_in_progress",
				"message": "another label job is already running on this worker",
			},
		)

	pairs = [(item_id, None) for item_id in req.ids]
	return fastapi.responses.StreamingResponse(
		_stream_minifig(pairs, req.debug, req.calibration),
		media_type="text/event-stream",
		headers={
			"Cache-Control": "no-cache",
			"X-Accel-Buffering": "no",
		}
	)


#============================================
@router.post("/sets/stream")
def post_set_labels_stream(req: schemas.LabelRequest) -> fastapi.Response:
	"""
	Stream set labels PDF with per-item progress updates.

	POST /api/labels/sets/stream
	Content-Type: application/json

	Returns: text/event-stream with progress events, final done event carries PDF as base64.
	Or 409 if another label job is already running.
	"""
	if not _LABELS_JOB_LOCK.acquire(blocking=False):
		return fastapi.responses.JSONResponse(
			status_code=409,
			content={
				"error": "job_in_progress",
				"message": "another label job is already running on this worker",
			},
		)

	return fastapi.responses.StreamingResponse(
		_stream_set(req.ids, req.debug, req.calibration),
		media_type="text/event-stream",
		headers={
			"Cache-Control": "no-cache",
			"X-Accel-Buffering": "no",
		}
	)
