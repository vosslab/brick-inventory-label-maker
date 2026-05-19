"""Pydantic request/response schemas for label generation endpoints."""

# PIP3 modules
import pydantic


class LabelRequest(pydantic.BaseModel):
	"""Request body for label generation."""
	ids: list[str]
	debug: bool = False
	calibration: bool = False


class ItemWarning(pydantic.BaseModel):
	"""One warning entry emitted in the X-Item-Warnings header."""
	id: str
	reason: str
	mean_lstar: float | None = None
