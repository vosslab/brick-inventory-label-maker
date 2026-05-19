# local repo modules
import libbrick.wrappers.bricklink_wrapper as bricklink_wrapper


class CredentialsMissingError(RuntimeError):
	"""Raised when a live BrickLink call is required but credentials are absent."""


# Process-wide BrickLink client, constructed once and cached.
# Lazy-loading ensures construction succeeds even without credentials;
# only the first live HTTP call triggers FileNotFoundError.
_CLIENT: bricklink_wrapper.BrickLink | None = None


#============================================
def _get_client() -> bricklink_wrapper.BrickLink:
	"""Return process-wide BrickLink client, constructing on first call."""
	global _CLIENT
	if _CLIENT is None:
		_CLIENT = bricklink_wrapper.BrickLink()
	return _CLIENT


#============================================
def _call_with_creds_translation(fn, *args, **kwargs):
	"""
	Translate upstream FileNotFoundError into CredentialsMissingError.

	The vendored BrickLink wrapper raises FileNotFoundError from _ensure_api_client()
	when no credentials file is found. This helper translates that to a typed exception
	suitable for FastAPI error handling.
	"""
	try:
		return fn(*args, **kwargs)
	except FileNotFoundError as exc:
		raise CredentialsMissingError(str(exc)) from exc


#============================================
def _safe_category(client, minifig_id: str) -> str | None:
	"""Return category name or None if upstream raises LookupError."""
	try:
		return _call_with_creds_translation(client.getCategoryNameFromMinifigID, minifig_id)
	except LookupError:
		return None


#============================================
def _safe_superset_count(client, minifig_id: str) -> int | None:
	"""Return superset count or None if upstream raises LookupError."""
	try:
		ids = _call_with_creds_translation(client.getSupersetFromMinifigID, minifig_id)
	except LookupError:
		return None
	if ids is None:
		return None
	return len(ids)


#============================================
def get_minifig_record(minifig_id: str, set_id: str | None = None) -> dict | None:
	"""
	Return a dict with the same keys reportlab_make_minifig_labels.make_minifig_label_data consumes.

	Keys produced (matching vendor gather_minifig_data flow):
		minifig_id, name, year_released, image_url, weight, category_name,
		superset_count, set_id, no, time.

	Args:
		minifig_id: BrickLink minifig ID, e.g. "sw0001".
		set_id: optional LEGO set ID to associate with this minifig.

	Returns:
		Dict with minifig data from BrickLink. None if the ID is unknown to
		BrickLink (vendor wrapper raises LookupError on 404).

	Raises:
		CredentialsMissingError: if a live BrickLink call is needed and yml absent.
	"""
	client = _get_client()
	try:
		minifig_data = _call_with_creds_translation(client.getMinifigData, minifig_id)
	except LookupError:
		return None
	# category and superset are optional in vendor flow (LookupError -> None)
	category_name = _safe_category(client, minifig_id)
	superset_count = _safe_superset_count(client, minifig_id)
	minifig_data['category_name'] = category_name
	minifig_data['set_id'] = set_id
	minifig_data['superset_count'] = superset_count
	minifig_data['minifig_id'] = minifig_id
	return minifig_data


#============================================
def get_set_record(set_id: str) -> dict | None:
	"""
	Return a dict the vendored reportlab_make_set_labels code can consume.

	Vendor flow combines BrickLink set data + rebrick set data + BL set details.
	This adapter uses BrickLink only (rebrick step dropped). Missing field:
		- theme_name: not available from BL category; must fall back to category_name.
	  The route layer (Patch 4) handles this fallback for labels.

	Args:
		set_id: BrickLink set ID with or without dash, e.g. "10240" or "10240-1".

	Returns:
		Dict with merged BrickLink base + details.

	Raises:
		CredentialsMissingError: if a live BrickLink call is needed and yml absent.
		LookupError: if BrickLink has no data for this set ID.
	"""
	client = _get_client()
	# normalize "10240" -> "10240-1" (matches vendor)
	if '-' not in set_id:
		set_id = f'{set_id}-1'
	try:
		base = _call_with_creds_translation(client.getSetData, set_id)
	except LookupError:
		return None
	try:
		detail = _call_with_creds_translation(client.getSetDataDetails, set_id)
	except LookupError:
		detail = {}
	base.update(detail)
	return base
