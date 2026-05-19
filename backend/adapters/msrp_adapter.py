# local repo modules
import libbrick.msrp_loader as msrp_loader


# Module-level MSRP cache, lazily loaded on first access.
# After first load, all access is read-only and requires no credentials.
_MSRP_CACHE: dict | None = None


#============================================
def _get_cache() -> dict:
	"""Lazily load the MSRP cache dict from vendor msrp_loader."""
	global _MSRP_CACHE
	if _MSRP_CACHE is None:
		_MSRP_CACHE = msrp_loader.load_msrp_cache()
	return _MSRP_CACHE


#============================================
def get_cents(set_id: str) -> int | None:
	"""
	Return MSRP cents for set_id from local cache, or None if absent.

	MSRP data is loaded once per process from a local YAML cache.
	No network calls or credentials required.

	Args:
		set_id: BrickLink set ID with or without dash, e.g. "10240" or "10240-1".

	Returns:
		Integer cents (e.g. 19999 for $199.99) or None if not in cache.
	"""
	cache = _get_cache()
	# normalize "10240" -> "10240-1"
	if '-' not in set_id:
		set_id = f'{set_id}-1'
	# MSRP is optional metadata; dict.get() is appropriate here per PYTHON_STYLE.
	# The key may not exist, and returning None is the intentional default.
	value = cache.get(set_id)
	if value is None:
		return None
	return int(value)
