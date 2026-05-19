#!/usr/bin/env python3

# Standard Library
import argparse
import os

# PIP3 modules
import reportlab.lib.pagesizes
import reportlab.pdfbase.pdfmetrics
import reportlab.pdfgen.canvas

# local repo modules
import libbrick.common
import libbrick.image_cache
import libbrick.msrp_loader
import libbrick.path_utils
import libbrick.reportlab_label_utils
import libbrick.wrappers.bricklink_wrapper as bricklink_wrapper
import libbrick.wrappers.rebrick_wrapper as rebrick_wrapper


SET_IMAGE_WIDTH_IN = 1.45
SET_IMAGE_HEIGHT_IN = 1.95


#============================================
def parse_args() -> argparse.Namespace:
	"""
	Parse CLI args for reportlab set-label generation.
	"""
	parser = argparse.ArgumentParser(description="Generate set labels PDF with ReportLab.")
	parser.add_argument("set_id_file", help="Path to set ID input file.")
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
def choose_set_name_size(set_name: str) -> float:
	"""
	Choose set-name font size based on name length.
	"""
	if set_name is None:
		return 12.0
	length = len(set_name)
	if length > 38:
		return 10.0
	if length > 28:
		return 11.0
	return 12.0


#============================================
def make_set_label_data(set_dict: dict, msrp_cache: dict) -> dict:
	"""
	Build derived fields used for one set label.
	"""
	set_id = set_dict.get("set_id")
	if set_id is None:
		raise ValueError("set_id is required")
	lego_id = int(str(set_id).split("-")[0])
	set_name = str(set_dict.get("name", "UNKNOWN")).replace("#", "").replace(" & ", " and ")
	name_size = choose_set_name_size(set_name)
	msrp_value = msrp_cache.get(str(set_id))
	pieces_line = f"{set_dict.get('num_parts')} pieces"
	if msrp_value is not None and msrp_value > 0:
		pieces_line += f"   MSRP: ${msrp_value/100:.2f}"
	return {
		"set_id": set_id,
		"lego_id": lego_id,
		"set_name": set_name,
		"name_size": name_size,
		"category_name": str(set_dict.get("category_name", "")),
		"year_released": str(set_dict.get("year_released", "")),
		"pieces_line": pieces_line,
		"theme_name": str(set_dict.get("theme_name", "")),
		"year": str(set_dict.get("year", "")),
		"set_img_url": set_dict.get("set_img_url"),
	}


#============================================
def resolve_image_path(image_url: str, set_id: str, output_dir: str) -> str:
	"""
	Get a cached image path and resolve it absolute for ReportLab.
	"""
	filename = libbrick.image_cache.get_cached_image(
		image_url, "set", set_id, relpath_from=output_dir
	)
	if os.path.isabs(filename):
		return filename
	return os.path.abspath(os.path.join(output_dir, filename))


#============================================
def draw_set_label(pdf, config: libbrick.reportlab_label_utils.ImpositionConfig,
		slot_row: int, slot_col: int, label_data: dict, image_path: str) -> None:
	"""
	Draw a single set label in the target slot.
	"""
	cx0, cy0, cx1, cy1 = libbrick.reportlab_label_utils.content_bbox(config, slot_row, slot_col)
	content_width = cx1 - cx0
	content_height = cy1 - cy0

	image_width = min(SET_IMAGE_WIDTH_IN * 72.0, content_width * 0.42)
	image_height = min(SET_IMAGE_HEIGHT_IN * 72.0, content_height)
	image_x = cx0
	image_y = cy0 + (content_height - image_height) / 2.0
	libbrick.reportlab_label_utils.draw_image_fit(pdf, image_path, image_x, image_y, image_width, image_height)

	text_x = image_x + image_width + 8.0
	max_text_width = max(30.0, cx1 - text_x)
	y = cy1 - 12.0

	pdf.setFillColorRGB(0.0, 0.0, 0.0)
	pdf.setFont("Helvetica-Bold", 20)
	pdf.drawString(text_x, y, str(label_data["lego_id"]))

	y -= 16.0
	pdf.setFont("Helvetica", float(label_data["name_size"]))
	pdf.drawString(text_x, y, label_data["set_name"][:120])

	y -= 14.0
	pdf.setFillColorRGB(0.0, 0.0, 0.4)
	pdf.setFont("Helvetica-Bold", 10)
	pdf.drawString(text_x, y, label_data["category_name"][:48])

	y -= 12.0
	pdf.setFillColorRGB(0.0, 0.0, 0.0)
	pdf.setFont("Helvetica-Bold", 10)
	pdf.drawString(text_x, y, f"({label_data['year_released']})")

	y -= 12.0
	pdf.setFont("Helvetica", 10)
	pieces_text = label_data["pieces_line"]
	if reportlab.pdfbase.pdfmetrics.stringWidth(pieces_text, "Helvetica", 10) > max_text_width:
		pieces_text = pieces_text[:64]
	pdf.drawString(text_x, y, pieces_text)


#============================================
def render_set_labels_pdf(labels: list[dict], image_paths: list[str], output_pdf: str,
		config: libbrick.reportlab_label_utils.ImpositionConfig) -> None:
	"""
	Render set labels to a PDF file using the given config.
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
		draw_set_label(pdf, config, row, col, label_data, image_paths[index])

	pdf.showPage()
	pdf.save()


#============================================
def build_pdf(set_data_tree: list[dict], msrp_cache: dict, output_dir: str, output_pdf: str,
		config: libbrick.reportlab_label_utils.ImpositionConfig) -> None:
	"""
	Build all label records and render the PDF.
	"""
	labels = []
	image_paths = []
	for set_dict in set_data_tree:
		label_data = make_set_label_data(set_dict, msrp_cache)
		labels.append(label_data)
		image_path = resolve_image_path(label_data["set_img_url"], label_data["set_id"], output_dir)
		image_paths.append(image_path)
		print(
			f"{label_data['lego_id']} -- {label_data['theme_name']} "
			f"({label_data['year']}) -- {label_data['set_name']}"
		)
	render_set_labels_pdf(labels, image_paths, output_pdf, config)


#============================================
def main() -> None:
	"""
	Main entry point for reportlab set-label generation.
	"""
	args = parse_args()
	if not os.path.isfile(args.set_id_file):
		raise FileNotFoundError(f"set ID file not found: {args.set_id_file}")

	config = libbrick.reportlab_label_utils.with_debug_flags(
		libbrick.reportlab_label_utils.AVERY_5163_SET_CONFIG,
		args.draw_outlines,
		args.calibration_page,
	)
	libbrick.reportlab_label_utils.validate_config(config)

	set_ids = libbrick.common.read_setIDs_from_file(args.set_id_file)
	if not set_ids:
		raise ValueError("No valid set IDs found")

	blw = bricklink_wrapper.BrickLink()
	rbw = rebrick_wrapper.Rebrick()
	msrp_cache = libbrick.msrp_loader.load_msrp_cache()

	set_data_tree = []
	for set_id in set_ids:
		normalized = set_id
		if "-" not in normalized:
			normalized = str(normalized) + "-1"
		set_data = blw.getSetData(normalized)
		rebrick_data = rbw.getSetData(normalized)
		set_data.update(rebrick_data)
		extra_set_data = blw.getSetDataDetails(normalized)
		set_data.update(extra_set_data)
		set_data_tree.append(set_data)

	set_data_tree = sorted(set_data_tree, key=lambda item: int(item["set_id"].split("-")[0]))
	print(f"Found {len(set_data_tree)} Lego Sets to process")

	filename_root = os.path.splitext(os.path.basename(args.set_id_file))[0]
	output_dir = libbrick.path_utils.get_output_dir(subdir="super_make")
	output_pdf = os.path.join(output_dir, f"labels-{filename_root}.pdf")
	build_pdf(set_data_tree, msrp_cache, output_dir, output_pdf, config)

	blw.close()
	rbw.close()
	print(f'open "{output_pdf}"')


if __name__ == "__main__":
	main()
