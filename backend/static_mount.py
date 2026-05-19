"""Static file serving for frontend assets (placeholder for M4+)."""

import os


#============================================
def get_frontend_dist_path() -> str:
	"""
	Get the path to frontend/dist if it exists, None otherwise.
	"""
	dist_path = 'frontend/dist'
	if os.path.isdir(dist_path):
		return dist_path
	return None
