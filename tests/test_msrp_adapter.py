"""Tests for MSRP adapter layer."""

# PIP3 modules
import pytest

# local repo modules
import backend.adapters.msrp_adapter as msrp_adapter


#============================================
@pytest.fixture(autouse=True)
def reset_msrp_cache():
	"""Reset the module-level _MSRP_CACHE singleton before each test."""
	msrp_adapter._MSRP_CACHE = None
	yield
	msrp_adapter._MSRP_CACHE = None


#============================================
def test_get_cents_known_set(monkeypatch):
	"""get_cents returns the correct value for a known set ID."""
	cache_data = {
		'10240-1': 19999,
		'75101-1': 14999,
	}
	monkeypatch.setattr(msrp_adapter, '_get_cache', lambda: cache_data)

	result = msrp_adapter.get_cents('10240-1')

	assert result == 19999


#============================================
def test_get_cents_unknown_returns_none(monkeypatch):
	"""get_cents returns None for an unknown set ID."""
	cache_data = {
		'10240-1': 19999,
		'75101-1': 14999,
	}
	monkeypatch.setattr(msrp_adapter, '_get_cache', lambda: cache_data)

	result = msrp_adapter.get_cents('99999-1')

	assert result is None


#============================================
def test_get_cents_normalizes_id(monkeypatch):
	"""get_cents normalizes "10240" to "10240-1" before lookup."""
	cache_data = {
		'10240-1': 19999,
	}
	monkeypatch.setattr(msrp_adapter, '_get_cache', lambda: cache_data)

	result = msrp_adapter.get_cents('10240')

	assert result == 19999


#============================================
def test_get_cents_returns_int(monkeypatch):
	"""get_cents always returns an int when value is found."""
	# Even if cache stores strings, get_cents converts to int
	cache_data = {
		'10240-1': '19999',
	}
	monkeypatch.setattr(msrp_adapter, '_get_cache', lambda: cache_data)

	result = msrp_adapter.get_cents('10240-1')

	assert isinstance(result, int)
	assert result == 19999


#============================================
def test_get_cents_empty_cache(monkeypatch):
	"""get_cents returns None when cache is empty."""
	cache_data = {}
	monkeypatch.setattr(msrp_adapter, '_get_cache', lambda: cache_data)

	result = msrp_adapter.get_cents('10240-1')

	assert result is None
