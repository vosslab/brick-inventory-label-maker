"""Configuration loader for brick inventory label maker."""

import os

# PIP3 modules
import yaml


# Environment variables with defaults
BRICKLINK_API_FILE = os.environ.get('BRICKLINK_API_FILE', './bricklink_api_private.yml')
BRICK_CACHE_DIR = os.environ.get('BRICK_CACHE_DIR', './cache')
DARK_IMAGE_ACTION = os.environ.get('DARK_IMAGE_ACTION', 'warn')
DARK_IMAGE_LSTAR_THRESHOLD = int(os.environ.get('DARK_IMAGE_LSTAR_THRESHOLD', '35'))
LABELS_OFFLINE = os.environ.get('LABELS_OFFLINE', '0')


#============================================
def credentials_present() -> bool:
	"""
	Check if BrickLink credentials file exists and parses to valid structure.
	Returns True only if file exists, is readable, and parses to a dict with four expected keys.
	Never raises.
	"""
	if not os.path.isfile(BRICKLINK_API_FILE):
		return False

	try:
		with open(BRICKLINK_API_FILE) as f:
			creds = yaml.safe_load(f)

		if not isinstance(creds, dict):
			return False

		required_keys = {'consumer_key', 'consumer_secret', 'token', 'token_secret'}
		return required_keys.issubset(creds.keys())
	except Exception:
		return False


#============================================
def load_credentials() -> dict:
	"""
	Load BrickLink credentials from YAML file.
	Raises FileNotFoundError or KeyError if file missing or invalid.
	"""
	if not os.path.isfile(BRICKLINK_API_FILE):
		raise FileNotFoundError(f"Credentials file not found: {BRICKLINK_API_FILE}")

	with open(BRICKLINK_API_FILE) as f:
		creds = yaml.safe_load(f)

	required_keys = {'consumer_key', 'consumer_secret', 'token', 'token_secret'}
	if not required_keys.issubset(creds.keys()):
		raise KeyError(f"Credentials file missing required keys: {required_keys}")

	return creds


#============================================
def vendor_commit() -> str:
	"""
	Extract source commit SHA from vendor/VENDOR_SOURCE.md.
	Returns "unknown" if not present.
	"""
	vendor_source_path = 'vendor/VENDOR_SOURCE.md'
	if not os.path.isfile(vendor_source_path):
		return 'unknown'

	try:
		with open(vendor_source_path) as f:
			for line in f:
				if 'Source commit:' in line:
					# Extract SHA from line like: Source commit: `f33bddee...`
					if '`' in line:
						parts = line.split('`')
						if len(parts) >= 2:
							return parts[1]
	except Exception:
		pass

	return 'unknown'
