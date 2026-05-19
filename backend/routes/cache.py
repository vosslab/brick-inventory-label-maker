"""Static cache route for serving cached images (raw and processed)."""

# Standard Library
import os
import re

# PIP3 modules
import fastapi
import fastapi.responses

# local repo modules
import libbrick.path_utils


#============================================
router = fastapi.APIRouter(prefix="/api/cache", tags=["cache"])

# Validate item_id to prevent path traversal attacks
_ITEM_ID_OK = re.compile(r'^[A-Za-z0-9_-]+$')


def _get_images_dir() -> str:
	"""Compute images directory path the same way vendor does."""
	git_root = libbrick.path_utils.get_git_root()
	if git_root is None:
		return 'images'
	return os.path.join(git_root, 'images')


#============================================


@router.get("/{kind}/{item_id}/raw.jpg")
async def get_raw_image(kind: str, item_id: str) -> fastapi.responses.FileResponse:
	"""
	Retrieve raw cached image (JPG) before rembg processing.

	Args:
		kind: Image kind ('minifig' or 'set').
		item_id: Item ID.

	Returns:
		FileResponse with content-type image/jpeg.

	Raises:
		HTTPException 400 if kind is invalid.
		HTTPException 404 if file not found.
	"""
	if kind not in ('minifig', 'set'):
		raise fastapi.HTTPException(status_code=400, detail="kind must be 'minifig' or 'set'")

	if not _ITEM_ID_OK.match(item_id):
		raise fastapi.HTTPException(status_code=400, detail="invalid item_id")

	images_dir = _get_images_dir()
	file_path = os.path.join(images_dir, 'raw', f"{kind}_{item_id}.jpg")

	if not os.path.isfile(file_path):
		raise fastapi.HTTPException(status_code=404, detail="raw image not found")

	return fastapi.responses.FileResponse(
		path=file_path,
		media_type="image/jpeg",
		headers={"Cache-Control": "public, max-age=86400"}
	)


#============================================


@router.get("/{kind}/{item_id}/processed.png")
async def get_processed_image(kind: str, item_id: str) -> fastapi.responses.FileResponse:
	"""
	Retrieve processed cached image (PNG) after rembg background removal.

	Args:
		kind: Image kind ('minifig' or 'set').
		item_id: Item ID.

	Returns:
		FileResponse with content-type image/png.

	Raises:
		HTTPException 400 if kind is invalid.
		HTTPException 404 if file not found.
	"""
	if kind not in ('minifig', 'set'):
		raise fastapi.HTTPException(status_code=400, detail="kind must be 'minifig' or 'set'")

	if not _ITEM_ID_OK.match(item_id):
		raise fastapi.HTTPException(status_code=400, detail="invalid item_id")

	images_dir = _get_images_dir()
	file_path = os.path.join(images_dir, 'processed', f"{kind}_{item_id}.png")

	if not os.path.isfile(file_path):
		raise fastapi.HTTPException(status_code=404, detail="processed image not found")

	return fastapi.responses.FileResponse(
		path=file_path,
		media_type="image/png",
		headers={"Cache-Control": "public, max-age=86400"}
	)
