# Standard Library
import os

# PIP3 modules
import yaml

# local repo modules
import libbrick.path_utils

#============================
#============================
def load_msrp_cache(cache_path: str = None) -> dict:
	"""
	Load the MSRP cache from a YAML file.
	"""
	if cache_path is None:
		git_root = libbrick.path_utils.get_git_root()
		if git_root is None:
			cache_path = os.path.join('CACHE', 'msrp_cache.yml')
		else:
			cache_path = os.path.join(git_root, 'CACHE', 'msrp_cache.yml')
	if not os.path.isfile(cache_path):
		return {}
	with open(cache_path, 'r') as f:
		cache_data = yaml.safe_load(f)
	if cache_data is None:
		return {}
	return cache_data
