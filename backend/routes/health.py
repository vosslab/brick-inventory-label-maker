"""Health check endpoint for brick inventory label maker."""

# PIP3 modules
import fastapi

# local repo modules
import backend.config


router = fastapi.APIRouter()


#============================================
@router.get('/api/health')
def get_health() -> dict:
	"""
	Health check endpoint.

	Returns JSON dict with four keys:
	- ok: always true
	- config_present: true if bricklink_api_private.yml exists and parses correctly
	- vendor_commit: source commit SHA of vendored files
	- offline_fixture_mode: true if LABELS_OFFLINE environment variable is "1"
	"""
	offline_mode = backend.config.LABELS_OFFLINE == '1'

	health_response = {
		'ok': True,
		'config_present': backend.config.credentials_present(),
		'vendor_commit': backend.config.vendor_commit(),
		'offline_fixture_mode': offline_mode,
	}

	return health_response
