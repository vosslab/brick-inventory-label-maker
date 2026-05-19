"""HTTP endpoints for PDF label generation."""

# Standard Library
import json

# PIP3 modules
import fastapi
import fastapi.responses

# local repo modules
import backend.schemas as schemas
import backend.adapters.label_renderer as label_renderer
import backend.adapters.bricklink_adapter as bricklink_adapter


router = fastapi.APIRouter(prefix="/api/labels", tags=["labels"])

_WARNINGS_HEADER_LIMIT = 32


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
	"""
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
	"""
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
