"""Tests for BrickLink adapter layer."""

# PIP3 modules
import pytest

# local repo modules
import backend.adapters.bricklink_adapter as bricklink_adapter


#============================================
@pytest.fixture(autouse=True)
def reset_bricklink_client():
	"""Reset the module-level _CLIENT singleton before each test."""
	bricklink_adapter._CLIENT = None
	yield
	bricklink_adapter._CLIENT = None


#============================================
def test_credentials_missing_raises_typed(monkeypatch):
	"""
	When a live call is needed and credentials absent,
	CredentialsMissingError is raised (not FileNotFoundError).
	"""
	class StubClient:
		def getMinifigData(self, minifig_id):
			raise FileNotFoundError("bricklink_api_private.yml not found")

	monkeypatch.setattr(bricklink_adapter, '_get_client', lambda: StubClient())

	with pytest.raises(bricklink_adapter.CredentialsMissingError):
		bricklink_adapter.get_minifig_record('sw1234')


#============================================
def test_minifig_record_has_required_keys(monkeypatch):
	"""
	get_minifig_record returns a dict with all required keys
	that reportlab_make_minifig_labels.make_minifig_label_data expects.
	"""
	canned_minifig_data = {
		'no': 'sw0001',
		'name': 'Stormtrooper',
		'year_released': 2014,
		'image_url': 'https://example.com/sw0001.jpg',
		'weight': '45',
		'category_id': 123,
	}

	class StubClient:
		def getMinifigData(self, minifig_id):
			return dict(canned_minifig_data)
		def getCategoryNameFromMinifigID(self, minifig_id):
			return 'Star Wars'
		def getSupersetFromMinifigID(self, minifig_id):
			return ['10240-1', '75101-1']

	monkeypatch.setattr(bricklink_adapter, '_get_client', lambda: StubClient())

	result = bricklink_adapter.get_minifig_record('sw0001', set_id='10240-1')

	# Verify required keys are present
	assert result['minifig_id'] == 'sw0001'
	assert result['name'] == 'Stormtrooper'
	assert result['year_released'] == 2014
	assert result['image_url'] == 'https://example.com/sw0001.jpg'
	assert result['weight'] == '45'
	assert result['category_name'] == 'Star Wars'
	assert result['set_id'] == '10240-1'
	assert result['superset_count'] == 2


#============================================
def test_safe_category_returns_none_on_lookup_error(monkeypatch):
	"""
	When getCategoryNameFromMinifigID raises LookupError,
	category_name in result is None (not an exception).
	"""
	class StubClient:
		def getMinifigData(self, minifig_id):
			return {
				'no': 'sw0001',
				'name': 'Stormtrooper',
				'year_released': 2014,
				'image_url': 'https://example.com/sw0001.jpg',
				'weight': '45',
				'category_id': 123,
			}
		def getCategoryNameFromMinifigID(self, minifig_id):
			raise LookupError("No category found")
		def getSupersetFromMinifigID(self, minifig_id):
			return ['10240-1']

	monkeypatch.setattr(bricklink_adapter, '_get_client', lambda: StubClient())

	result = bricklink_adapter.get_minifig_record('sw0001')

	assert result['category_name'] is None
	assert result['superset_count'] == 1


#============================================
def test_set_record_normalizes_id(monkeypatch):
	"""
	get_set_record normalizes set ID: "10240" becomes "10240-1" before calling vendor.
	"""
	call_log = []

	class StubClient:
		def getSetData(self, set_id):
			call_log.append(('getSetData', set_id))
			return {
				'no': '10240-1',
				'name': 'Colosseum',
				'year_released': 2014,
				'num_parts': 9036,
				'category_id': 1,
				'category_name': 'Buildings',
				'set_img_url': 'https://example.com/10240.jpg',
			}
		def getSetDataDetails(self, set_id):
			call_log.append(('getSetDataDetails', set_id))
			return {
				'price_data': {'avg_price': 50.0},
			}

	monkeypatch.setattr(bricklink_adapter, '_get_client', lambda: StubClient())

	result = bricklink_adapter.get_set_record('10240')

	# Verify vendor methods received normalized ID
	assert ('getSetData', '10240-1') in call_log
	assert ('getSetDataDetails', '10240-1') in call_log
	# Verify merge happened
	assert result['name'] == 'Colosseum'
	assert result['price_data'] == {'avg_price': 50.0}


#============================================
def test_set_record_merges_data(monkeypatch):
	"""
	get_set_record merges getSetData and getSetDataDetails results.
	"""
	class StubClient:
		def getSetData(self, set_id):
			return {
				'no': '10240-1',
				'name': 'Colosseum',
				'year_released': 2014,
				'num_parts': 9036,
				'category_id': 1,
				'category_name': 'Buildings',
				'set_img_url': 'https://example.com/10240.jpg',
			}
		def getSetDataDetails(self, set_id):
			return {
				'weight': 5000.0,
				'sku': 'xyz123',
			}

	monkeypatch.setattr(bricklink_adapter, '_get_client', lambda: StubClient())

	result = bricklink_adapter.get_set_record('10240-1')

	# Both base and detail fields present
	assert result['name'] == 'Colosseum'
	assert result['weight'] == 5000.0
	assert result['sku'] == 'xyz123'
