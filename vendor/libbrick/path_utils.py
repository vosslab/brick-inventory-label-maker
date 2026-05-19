# Standard Library
import os
import subprocess

#============================
#============================
def get_git_root(path: str = None) -> str:
	"""
	Return the absolute path of the repository root.
	"""
	if path is None:
		path = os.path.dirname(os.path.abspath(__file__))
	try:
		base = subprocess.check_output(
			['git', 'rev-parse', '--show-toplevel'],
			cwd=path,
			universal_newlines=True
		).strip()
		return base
	except subprocess.CalledProcessError:
		# Not inside a git repository
		return None

#============================

def get_output_dir(path: str = None, create: bool = True, subdir: str = None) -> str:
	"""
	Return the output directory path, creating it if requested.
	"""
	if path is None:
		path = os.getcwd()
	git_root = get_git_root(path)
	base_dir = git_root if git_root is not None else path
	output_dir = os.path.join(base_dir, 'output')
	if subdir:
		output_dir = os.path.join(output_dir, subdir)
	if create and not os.path.isdir(output_dir):
		os.makedirs(output_dir, exist_ok=True)
	return output_dir
