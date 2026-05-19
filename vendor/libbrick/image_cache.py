# Standard Library
import os
import time
import random
import shutil
import subprocess

# PIP3 modules
import requests
import PIL.Image
import PIL.ImageChops

# local repo modules
import libbrick.path_utils

#============================
#============================
REMBG_MODEL = 'isnet-general-use'
LABEL_IMAGE_WIDTH_IN = 1.45
LABEL_IMAGE_HEIGHT_IN = 1.95
LABEL_MAX_CROP_FRACTION = 0.10

#============================
#============================
def ensure_images_directory(base_dir: str) -> None:
	"""
	Creates an 'images' directory with raw and processed subfolders.
	"""
	if not os.path.isdir(base_dir):
		os.mkdir(base_dir)
	for subdir in ('raw', 'processed'):
		subdir_path = os.path.join(base_dir, subdir)
		if not os.path.isdir(subdir_path):
			os.mkdir(subdir_path)

#============================

def ensure_image_tools_installed() -> None:
	"""
	Ensures required image tools are installed and available in PATH.
	"""
	if shutil.which('rembg') is None:
		raise FileNotFoundError("rembg not found in PATH")

#============================

def normalize_image_url(image_url: str) -> str:
	"""
	Ensure image URLs use https when missing a scheme.
	"""
	if image_url is None:
		return None
	if image_url.startswith('//'):
		return 'https:' + image_url
	return image_url

#============================

def download_image(image_url: str, filename: str) -> str:
	"""
	Download an image from a URL and save it locally.
	"""
	if image_url is None:
		raise TypeError
	if os.path.exists(filename):
		return filename
	image_url = normalize_image_url(image_url)
	time.sleep(random.random())
	r = requests.get(image_url, stream=True, timeout=15)
	if r.status_code == 200:
		r.raw.decode_content = True
		with open(filename, 'wb') as f:
			shutil.copyfileobj(r.raw, f)
		print(f'.. image successfully downloaded: {filename}')
	else:
		print(f"!! image couldn't be retrieved: {image_url}")
		raise FileNotFoundError
	return filename

#============================

def _get_background_color(image: PIL.Image.Image) -> tuple:
	"""
	Determine a likely background color by sampling corners.
	"""
	width, height = image.size
	max_x = max(0, width - 1)
	max_y = max(0, height - 1)
	x1 = min(1, max_x)
	y1 = min(1, max_y)
	x2 = max(0, max_x - 1)
	y2 = max(0, max_y - 1)
	sample_pixels = [
		image.getpixel((0, 0)), image.getpixel((x1, 0)),
		image.getpixel((0, y1)), image.getpixel((x1, y1)),
		image.getpixel((max_x, 0)), image.getpixel((x2, 0)),
		image.getpixel((max_x, y1)), image.getpixel((x2, y1)),
		image.getpixel((0, max_y)), image.getpixel((x1, max_y)),
		image.getpixel((0, y2)), image.getpixel((x1, y2)),
		image.getpixel((max_x, max_y)), image.getpixel((x2, max_y)),
		image.getpixel((max_x, y2)), image.getpixel((x2, y2)),
	]
	return max(set(sample_pixels), key=sample_pixels.count)

#============================

def _trim_image(image: PIL.Image.Image, tolerance: int = 3) -> PIL.Image.Image:
	"""
	Trim borders from an image based on alpha or background color.
	"""
	if 'A' in image.getbands():
		alpha = image.split()[-1]
		bbox = alpha.getbbox()
		if bbox:
			return image.crop(bbox)
		return image
	bg_color = _get_background_color(image)
	bg = PIL.Image.new(image.mode, image.size, bg_color)
	diff = PIL.ImageChops.difference(image, bg)
	diff = PIL.ImageChops.add(diff, diff, 2.0, -tolerance)
	bbox = diff.getbbox()
	if bbox:
		return image.crop(bbox)
	return image

#============================

def _crop_to_aspect(image: PIL.Image.Image, target_ratio: float,
		max_crop_fraction: float) -> PIL.Image.Image:
	"""
	Crop the image toward a target width/height ratio with a max crop limit.
	"""
	width, height = image.size
	if width <= 0 or height <= 0:
		return image
	current_ratio = width / float(height)
	if abs(current_ratio - target_ratio) < 0.01:
		return image
	if current_ratio > target_ratio:
		new_width = int(height * target_ratio)
		excess = max(0, width - new_width)
		max_crop = int(width * max_crop_fraction)
		crop_total = min(excess, max_crop)
		left = crop_total // 2
		right = width - (crop_total - left)
		return image.crop((left, 0, right, height))
	new_height = int(width / target_ratio)
	excess = max(0, height - new_height)
	max_crop = int(height * max_crop_fraction)
	crop_total = min(excess, max_crop)
	top = crop_total // 2
	bottom = height - (crop_total - top)
	return image.crop((0, top, width, bottom))

#============================

def process_image(raw_filename: str, processed_filename: str, model: str = None) -> str:
	"""
	Remove background and trim the image for label use.
	"""
	if os.path.exists(processed_filename):
		return processed_filename
	ensure_image_tools_installed()
	if model is None:
		model = REMBG_MODEL
	command = ['rembg', 'i']
	if model:
		command += ['-m', model]
	command += [raw_filename, processed_filename]
	subprocess.run(command, check=True)
	with PIL.Image.open(processed_filename) as image:
		trimmed = _trim_image(image)
		target_ratio = LABEL_IMAGE_WIDTH_IN / float(LABEL_IMAGE_HEIGHT_IN)
		trimmed = _crop_to_aspect(trimmed, target_ratio, LABEL_MAX_CROP_FRACTION)
		trimmed = trimmed.copy()
	trimmed.save(processed_filename)
	return processed_filename

#============================

def get_cached_image(image_url: str, image_prefix: str, item_id: str,
		raw_ext: str = 'jpg', processed_ext: str = 'png',
		relpath_from: str = None) -> str:
	"""
	Fetch, cache, and process an image, returning a path suitable for LaTeX.
	"""
	git_root = libbrick.path_utils.get_git_root()
	if git_root is None:
		images_dir = 'images'
	else:
		images_dir = os.path.join(git_root, 'images')
	ensure_images_directory(images_dir)
	raw_filename = os.path.join(images_dir, 'raw', f"{image_prefix}_{item_id}.{raw_ext}")
	processed_filename = os.path.join(
		images_dir, 'processed', f"{image_prefix}_{item_id}.{processed_ext}"
	)
	download_image(image_url, raw_filename)
	process_image(raw_filename, processed_filename)
	if relpath_from is not None:
		return os.path.relpath(processed_filename, relpath_from)
	if git_root is None:
		return processed_filename
	return os.path.relpath(processed_filename, git_root)
