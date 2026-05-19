"""Label PDF renderer adapter wrapping vendored ReportLab modules."""

# Standard Library
import io
import os
import tempfile

# PIP3 modules
import reportlab.lib.pagesizes
import reportlab.pdfbase.pdfmetrics
import reportlab.pdfgen.canvas

# local repo modules (vendor via PYTHONPATH)
import libbrick.reportlab_label_utils as label_utils
import reportlab_make_minifig_labels as minifig_module
# NOTE: reportlab_make_set_labels.py imports rebrick_wrapper which is NOT vendored.
# Rather than import that module, we inline-port its draw_set_label() and
# make_set_label_data() functions below. This keeps vendor untouched.

import backend.adapters.bricklink_adapter as bricklink_adapter
import backend.adapters.image_pipeline as image_pipeline
import backend.adapters.msrp_adapter as msrp_adapter


#============================================
# Inline-ported set label helpers (from reportlab_make_set_labels.py)
# Ported to avoid importing rebrick_wrapper which is not vendored.

def _choose_set_name_size(set_name: str) -> float:
	"""Choose set-name font size based on name length."""
	if set_name is None:
		return 12.0
	length = len(set_name)
	if length > 38:
		return 10.0
	if length > 28:
		return 11.0
	return 12.0


def _make_set_label_data(set_dict: dict, msrp_cache: dict) -> dict:
	"""Build derived fields used for one set label."""
	set_id = set_dict.get("set_id")
	if set_id is None:
		raise ValueError("set_id is required")
	lego_id = int(str(set_id).split("-")[0])
	set_name = str(set_dict.get("name", "UNKNOWN")).replace("#", "").replace(" & ", " and ")
	name_size = _choose_set_name_size(set_name)
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


def _draw_set_label(pdf, config: label_utils.ImpositionConfig,
		slot_row: int, slot_col: int, label_data: dict, image_path: str) -> None:
	"""Draw a single set label in the target slot."""
	SET_IMAGE_WIDTH_IN = 1.45
	SET_IMAGE_HEIGHT_IN = 1.95

	cx0, cy0, cx1, cy1 = label_utils.content_bbox(config, slot_row, slot_col)
	content_width = cx1 - cx0
	content_height = cy1 - cy0

	image_width = min(SET_IMAGE_WIDTH_IN * 72.0, content_width * 0.42)
	image_height = min(SET_IMAGE_HEIGHT_IN * 72.0, content_height)
	image_x = cx0
	image_y = cy0 + (content_height - image_height) / 2.0
	label_utils.draw_image_fit(pdf, image_path, image_x, image_y, image_width, image_height)

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
def render_minifig_pdf(
		minifig_id_pairs: list[tuple[str, str | None]],
		debug: bool,
		calibration: bool,
		) -> tuple[bytes, list[dict]]:
	"""
	Build a minifig labels PDF.

	Args:
		minifig_id_pairs: list of (minifig_id, optional set_id) tuples.
		debug: draw debug outlines on each page.
		calibration: prepend a calibration page.

	Returns:
		Tuple of (pdf_bytes, warnings_list). warnings_list is a list of
		{"id": str, "reason": str, "mean_lstar": float | None}.

	Raises:
		bricklink_adapter.CredentialsMissingError: if BrickLink call needs yml.
	"""
	config = label_utils.with_debug_flags(
		label_utils.AVERY_18260_MINIFIG_CONFIG,
		draw_outlines=debug,
		calibration_page=calibration,
	)
	label_utils.validate_config(config)

	records = []
	image_paths = []
	warnings = []

	with tempfile.TemporaryDirectory() as tmpdir:
		for minifig_id, set_id in minifig_id_pairs:
			record = bricklink_adapter.get_minifig_record(minifig_id, set_id)
			if record is None:
				warnings.append({
					"id": minifig_id,
					"reason": "bricklink_lookup_failed",
					"mean_lstar": None
				})
				continue

			label_data = minifig_module.make_minifig_label_data(
				record,
				record.get('superset_count')
			)

			image_url = record.get('image_url')
			if image_url is None:
				warnings.append({
					"id": minifig_id,
					"reason": "image_url_missing",
					"mean_lstar": None
				})
				continue

			# Fetch and classify image
			result = image_pipeline.fetch_and_classify(image_url, 'minifig', minifig_id)

			if isinstance(result, image_pipeline.MissingImage):
				warnings.append({
					"id": minifig_id,
					"reason": f"image_missing: {result.reason}",
					"mean_lstar": None
				})
				continue

			if isinstance(result, image_pipeline.DarkImage):
				warnings.append({
					"id": minifig_id,
					"reason": f"dark_image_{result.action}",
					"mean_lstar": result.mean_lstar
				})
				if result.action == 'reject':
					# Skip this item entirely
					continue
				image_bytes = result.image_bytes
			else:
				# Trimmed bright image
				image_bytes = result.image_bytes

			# Write trimmed PNG to temp file for ReportLab
			image_path = os.path.join(tmpdir, f"{minifig_id}.png")
			with open(image_path, 'wb') as f:
				f.write(image_bytes)

			records.append(label_data)
			image_paths.append(image_path)

		# Render to BytesIO
		buf = io.BytesIO()
		pdf = reportlab.pdfgen.canvas.Canvas(buf, pagesize=reportlab.lib.pagesizes.letter)

		if calibration:
			label_utils.draw_calibration_page(pdf, config)

		slots = label_utils.page_slot_indices(config)
		page_slots = len(slots)

		if not records:
			if debug:
				label_utils.draw_debug_outlines(pdf, config)
			pdf.setFont("Helvetica", 12)
			pdf.drawString(32, 32, "No labels to render.")
			pdf.showPage()
		else:
			for index, label_data in enumerate(records):
				if index % page_slots == 0:
					if index != 0:
						pdf.showPage()
					if debug:
						label_utils.draw_debug_outlines(pdf, config)
				slot_index = index % page_slots
				row, col = slots[slot_index]
				minifig_module.draw_minifig_label(
					pdf,
					config,
					row,
					col,
					label_data,
					image_paths[index]
				)
			pdf.showPage()

		pdf.save()
		pdf_bytes = buf.getvalue()

	return pdf_bytes, warnings


#============================================
def render_set_pdf(
		set_ids: list[str],
		debug: bool,
		calibration: bool,
		) -> tuple[bytes, list[dict]]:
	"""
	Build a set labels PDF.

	Args:
		set_ids: list of LEGO set IDs (with or without dash).
		debug: draw debug outlines on each page.
		calibration: prepend a calibration page.

	Returns:
		Tuple of (pdf_bytes, warnings_list). warnings_list is a list of
		{"id": str, "reason": str, "mean_lstar": float | None}.

	Raises:
		bricklink_adapter.CredentialsMissingError: if BrickLink call needs yml.
	"""
	config = label_utils.with_debug_flags(
		label_utils.AVERY_5163_SET_CONFIG,
		draw_outlines=debug,
		calibration_page=calibration,
	)
	label_utils.validate_config(config)

	# Load MSRP cache once for all sets
	msrp_cache = msrp_adapter._get_cache()

	records = []
	image_paths = []
	warnings = []

	with tempfile.TemporaryDirectory() as tmpdir:
		for set_id in set_ids:
			try:
				set_record = bricklink_adapter.get_set_record(set_id)
			except bricklink_adapter.CredentialsMissingError:
				raise
			except LookupError:
				warnings.append({
					"id": set_id,
					"reason": "bricklink_lookup_failed",
					"mean_lstar": None
				})
				continue
			except Exception as e:
				warnings.append({
					"id": set_id,
					"reason": f"error: {str(e)}",
					"mean_lstar": None
				})
				continue

			label_data = _make_set_label_data(set_record, msrp_cache)

			image_url = set_record.get('set_img_url')
			if image_url is None:
				warnings.append({
					"id": set_id,
					"reason": "image_url_missing",
					"mean_lstar": None
				})
				continue

			# Fetch and classify image
			result = image_pipeline.fetch_and_classify(image_url, 'set', set_id)

			if isinstance(result, image_pipeline.MissingImage):
				warnings.append({
					"id": set_id,
					"reason": f"image_missing: {result.reason}",
					"mean_lstar": None
				})
				continue

			if isinstance(result, image_pipeline.DarkImage):
				warnings.append({
					"id": set_id,
					"reason": f"dark_image_{result.action}",
					"mean_lstar": result.mean_lstar
				})
				if result.action == 'reject':
					# Skip this item entirely
					continue
				image_bytes = result.image_bytes
			else:
				# Trimmed bright image
				image_bytes = result.image_bytes

			# Write trimmed PNG to temp file for ReportLab
			image_path = os.path.join(tmpdir, f"{set_id}.png")
			with open(image_path, 'wb') as f:
				f.write(image_bytes)

			records.append(label_data)
			image_paths.append(image_path)

		# Render to BytesIO
		buf = io.BytesIO()
		pdf = reportlab.pdfgen.canvas.Canvas(buf, pagesize=reportlab.lib.pagesizes.letter)

		if calibration:
			label_utils.draw_calibration_page(pdf, config)

		slots = label_utils.page_slot_indices(config)
		page_slots = len(slots)

		if not records:
			if debug:
				label_utils.draw_debug_outlines(pdf, config)
			pdf.setFont("Helvetica", 12)
			pdf.drawString(32, 32, "No labels to render.")
			pdf.showPage()
		else:
			for index, label_data in enumerate(records):
				if index % page_slots == 0:
					if index != 0:
						pdf.showPage()
					if debug:
						label_utils.draw_debug_outlines(pdf, config)
				slot_index = index % page_slots
				row, col = slots[slot_index]
				_draw_set_label(
					pdf,
					config,
					row,
					col,
					label_data,
					image_paths[index]
				)
			pdf.showPage()

		pdf.save()
		pdf_bytes = buf.getvalue()

	return pdf_bytes, warnings
