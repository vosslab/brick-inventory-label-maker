#!/usr/bin/env python3

# Standard Library
import argparse
import os
import re
import time
import random

# PIP3 modules
import reportlab.lib.pagesizes
import reportlab.pdfbase.pdfmetrics
import reportlab.pdfgen.canvas

# local repo modules
import libbrick.common
import libbrick.image_cache
import libbrick.path_utils
import libbrick.reportlab_label_utils
import libbrick.wrappers.bricklink_wrapper as bricklink_wrapper


MINIFIG_IMAGE_WIDTH_IN = 0.45
MINIFIG_IMAGE_HEIGHT_IN = 0.65


#============================================
def parse_args() -> argparse.Namespace:
	"""
	Parse CLI args for reportlab minifig-label generation.
	"""
	parser = argparse.ArgumentParser(description="Generate minifig labels PDF with ReportLab.")
	parser.add_argument("minifig_id_file", help="Path to minifig ID input file.")
	parser.add_argument(
		"-d", "--draw-outlines", dest="draw_outlines",
		action="store_true", help="Draw label and content outlines for debugging."
	)
	parser.add_argument(
		"-D", "--no-draw-outlines", dest="draw_outlines",
		action="store_false", help="Disable debug outlines."
	)
	parser.add_argument(
		"-c", "--calibration-page", dest="calibration_page",
		action="store_true", help="Prepend a calibration page."
	)
	parser.add_argument(
		"-C", "--no-calibration-page", dest="calibration_page",
		action="store_false", help="Disable calibration page."
	)
	parser.set_defaults(
		draw_outlines=False,
		calibration_page=False,
	)
	return parser.parse_args()


#============================================
def format_minifig_name(name: str) -> str:
	"""
	Normalize and shorten long minifig names.
	"""
	name = str(name).replace("#", "")
	name = re.sub(r"\([^\)]+\)", "", name).strip()
	if len(name) > 64:
		new_name = ""
		bits = name.split(" ")
		index = 0
		while index < len(bits) and len(new_name) < 58:
			new_name += bits[index] + " "
			index += 1
		name = new_name.strip()
	return name


#============================================
def determine_name_size(name: str) -> float:
	"""
	Map minifig name length to font size.
	"""
	length = len(name)
	if length < 18:
		return 9.0
	if length < 26:
		return 8.0
	if length < 34:
		return 7.0
	if length < 50:
		return 6.5
	return 5.5


#============================================
def get_set_num(minifig_dict: dict) -> str:
	"""
	Extract set number from minifig dictionary.
	"""
	set_num = minifig_dict.get("set_num")
	if set_num is None:
		set_id = minifig_dict.get("set_id")
		if set_id is not None:
			set_num = str(set_id).split("-")[0]
	return str(set_num)


#============================================
def resolve_image_path(minifig_dict: dict, minifig_id: str, output_dir: str) -> str:
	"""
	Resolve cached minifig image path to absolute path.
	"""
	image_url = minifig_dict.get("image_url")
	filename = libbrick.image_cache.get_cached_image(
		image_url, "minifig", minifig_id, relpath_from=output_dir
	)
	if os.path.isabs(filename):
		return filename
	return os.path.abspath(os.path.join(output_dir, filename))


#============================================
def make_minifig_label_data(minifig_dict: dict, superset_count: int) -> dict:
	"""
	Build derived fields used for one minifig label.
	"""
	minifig_id = str(minifig_dict.get("minifig_id"))
	minifig_name = format_minifig_name(minifig_dict.get("name", "UNKNOWN"))
	name_size = determine_name_size(minifig_name)
	return {
		"minifig_id": minifig_id,
		"name": minifig_name,
		"name_size": name_size,
		"year_released": str(minifig_dict.get("year_released", "")),
		"category_name": minifig_dict.get("category_name"),
		"superset_count": superset_count,
		"set_num": get_set_num(minifig_dict),
	}


#============================================
def draw_minifig_label(pdf, config: libbrick.reportlab_label_utils.ImpositionConfig,
		slot_row: int, slot_col: int, label_data: dict, image_path: str) -> None:
	"""
	Draw one minifig label in the target slot.
	"""
	cx0, cy0, cx1, cy1 = libbrick.reportlab_label_utils.content_bbox(config, slot_row, slot_col)
	content_width = cx1 - cx0
	content_height = cy1 - cy0

	image_width = min(MINIFIG_IMAGE_WIDTH_IN * 72.0, content_width * 0.22)
	image_height = min(MINIFIG_IMAGE_HEIGHT_IN * 72.0, content_height * 0.9)
	image_x = cx0 + 1.5
	image_y = cy0 + (content_height - image_height) / 2.0
	libbrick.reportlab_label_utils.draw_image_fit(pdf, image_path, image_x, image_y, image_width, image_height)

	text_x = image_x + image_width + 4.0
	max_text_width = max(20.0, cx1 - text_x)
	y = cy1 - 7.0

	pdf.setFillColorRGB(0.0, 0.0, 0.4)
	pdf.setFont("Helvetica-Bold", 9 if len(label_data["minifig_id"]) < 10 else 8)
	pdf.drawString(text_x, y, label_data["minifig_id"][:20])

	y -= 9.0
	pdf.setFillColorRGB(0.0, 0.0, 0.0)
	pdf.setFont("Helvetica", float(label_data["name_size"]))
	pdf.drawString(text_x, y, label_data["name"][:80])

	y -= 8.5
	pdf.setFont("Helvetica", 6.5)
	pdf.drawString(text_x, y, f"release year: {label_data['year_released']}")

	category_name = label_data["category_name"]
	if category_name is not None:
		y -= 7.0
		pdf.setFont("Helvetica", 5.8)
		pdf.drawString(text_x, y, f"category: {str(category_name)[:36]}")

	superset_count = label_data["superset_count"]
	if superset_count is not None and superset_count > 0:
		y -= 6.5
		pdf.setFont("Helvetica", 5.8)
		line = f"appears in {superset_count} sets"
		if reportlab.pdfbase.pdfmetrics.stringWidth(line, "Helvetica", 5.8) > max_text_width:
			line = f"appears in {superset_count}"
		pdf.drawString(text_x, y, line)


#============================================
def render_minifig_labels_pdf(labels: list[dict], image_paths: list[str], output_pdf: str,
		config: libbrick.reportlab_label_utils.ImpositionConfig) -> None:
	"""
	Render minifig labels to a PDF file.
	"""
	libbrick.reportlab_label_utils.validate_config(config)
	slots = libbrick.reportlab_label_utils.page_slot_indices(config)
	page_slots = len(slots)
	pdf = reportlab.pdfgen.canvas.Canvas(output_pdf, pagesize=reportlab.lib.pagesizes.letter)

	if config.calibration_page:
		libbrick.reportlab_label_utils.draw_calibration_page(pdf, config)

	if not labels:
		if config.draw_outlines:
			libbrick.reportlab_label_utils.draw_debug_outlines(pdf, config)
		pdf.setFont("Helvetica", 12)
		pdf.drawString(32, 32, "No labels to render.")
		pdf.showPage()
		pdf.save()
		return

	for index, label_data in enumerate(labels):
		if index % page_slots == 0:
			if index != 0:
				pdf.showPage()
			if config.draw_outlines:
				libbrick.reportlab_label_utils.draw_debug_outlines(pdf, config)
		slot_index = index % page_slots
		row, col = slots[slot_index]
		draw_minifig_label(pdf, config, row, col, label_data, image_paths[index])

	pdf.showPage()
	pdf.save()


#============================================
def build_pdf(minifig_info_tree: list[dict], output_dir: str, output_pdf: str,
		config: libbrick.reportlab_label_utils.ImpositionConfig) -> None:
	"""
	Build label records and render minifig labels PDF.
	"""
	labels = []
	image_paths = []
	for minifig_dict in minifig_info_tree:
		superset_count = minifig_dict.get("superset_count")
		label_data = make_minifig_label_data(minifig_dict, superset_count)
		labels.append(label_data)
		image_path = resolve_image_path(minifig_dict, label_data["minifig_id"], output_dir)
		image_paths.append(image_path)
		print(
			f"{label_data['minifig_id']} -- {label_data['set_num']} "
			f"({label_data['year_released']}) -- {label_data['name'][:60]}"
		)
	render_minifig_labels_pdf(labels, image_paths, output_pdf, config)


#============================================
def gather_minifig_data(minifig_id_pairs: list[tuple[str, str]]) -> list[dict]:
	"""
	Fetch minifig data from BrickLink and apply current filtering behavior.
	"""
	blw = bricklink_wrapper.BrickLink()
	line = 0
	minifig_info_tree = []
	for pair in minifig_id_pairs:
		minifig_id, set_id = pair
		line += 1
		try:
			minifig_data = blw.getMinifigData(minifig_id)
		except LookupError:
			continue

		try:
			category_name = blw.getCategoryNameFromMinifigID(minifig_id)
		except LookupError:
			time.sleep(random.random())
			category_name = None

		try:
			superset_ids = blw.getSupersetFromMinifigID(minifig_id)
		except LookupError:
			time.sleep(random.random())
			superset_ids = None

		superset_count = None
		if superset_ids is not None:
			superset_count = len(superset_ids)

		minifig_data["category_name"] = category_name
		minifig_data["set_id"] = set_id
		minifig_data["superset_count"] = superset_count
		total_data = {**minifig_data}
		total_data["minifig_id"] = minifig_id

		if total_data.get("weight") is None:
			raise KeyError("Missing key: weight")
		if float(total_data["weight"]) > 1000:
			print(
				f"TOO BIG: weight {total_data['weight']} skipping {total_data['no']} "
				f"from set {total_data.get('set_num')}: {total_data['name'][:60]}"
			)
			continue
		minifig_info_tree.append(total_data)
		if line % 50 == 0:
			blw.save_cache()

	blw.close()
	return minifig_info_tree


#============================================
def main() -> None:
	"""
	Main entry point for reportlab minifig-label generation.
	"""
	args = parse_args()
	if not os.path.isfile(args.minifig_id_file):
		raise FileNotFoundError(f"minifig ID file not found: {args.minifig_id_file}")

	config = libbrick.reportlab_label_utils.with_debug_flags(
		libbrick.reportlab_label_utils.AVERY_18260_MINIFIG_CONFIG,
		args.draw_outlines,
		args.calibration_page,
	)
	libbrick.reportlab_label_utils.validate_config(config)

	minifig_id_pairs = libbrick.common.read_minifigIDpairs_from_file(args.minifig_id_file)
	if not minifig_id_pairs:
		raise ValueError("No valid minifig ID pairs found")

	minifig_info_tree = gather_minifig_data(minifig_id_pairs)
	minifig_info_tree = sorted(minifig_info_tree, key=lambda item: item.get("minifig_id"))
	print(f"Found {len(minifig_info_tree)} Minifigs to process")

	filename_root = os.path.splitext(os.path.basename(args.minifig_id_file))[0]
	output_dir = libbrick.path_utils.get_output_dir(subdir="super_make")
	output_pdf = os.path.join(output_dir, f"labels-{filename_root}.pdf")
	build_pdf(minifig_info_tree, output_dir, output_pdf, config)
	print(f'open "{output_pdf}"')


if __name__ == "__main__":
	main()
