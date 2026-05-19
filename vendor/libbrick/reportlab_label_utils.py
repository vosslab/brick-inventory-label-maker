# Standard Library
import dataclasses
import os

# PIP3 modules
import reportlab.lib.pagesizes
import reportlab.pdfbase.pdfmetrics


POINTS_PER_INCH = 72.0

DEFAULT_FONT_NAME = "Helvetica"
DEFAULT_BOLD_FONT_NAME = "Helvetica-Bold"


@dataclasses.dataclass(frozen=True)
class ImpositionConfig:
	"""
	Layout settings for an Avery label sheet.
	"""
	name: str
	label_width: float
	label_height: float
	columns: int
	rows: int
	left_margin: float
	top_margin: float
	h_gap: float
	v_gap: float
	content_inset: float
	draw_outlines: bool
	calibration_page: bool


# Avery 5163 (set labels), based on current LaTeX geometry.
AVERY_5163_SET_CONFIG = ImpositionConfig(
	name="Avery 5163",
	label_width=4.0 * POINTS_PER_INCH,
	label_height=2.0 * POINTS_PER_INCH,
	columns=2,
	rows=5,
	left_margin=0.16 * POINTS_PER_INCH,
	top_margin=0.5 * POINTS_PER_INCH,
	h_gap=0.18 * POINTS_PER_INCH,
	v_gap=0.0,
	content_inset=0.10 * POINTS_PER_INCH,
	draw_outlines=False,
	calibration_page=False,
)

# Avery 18260 (minifig labels), based on current LaTeX geometry.
AVERY_18260_MINIFIG_CONFIG = ImpositionConfig(
	name="Avery 18260",
	label_width=2.625 * POINTS_PER_INCH,
	label_height=0.98 * POINTS_PER_INCH,
	columns=3,
	rows=10,
	left_margin=0.28 * POINTS_PER_INCH,
	top_margin=0.5 * POINTS_PER_INCH,
	h_gap=0.1025 * POINTS_PER_INCH,
	v_gap=(0.1 / 9.0) * POINTS_PER_INCH,
	content_inset=0.05 * POINTS_PER_INCH,
	draw_outlines=False,
	calibration_page=False,
)


#============================================
def with_debug_flags(config: ImpositionConfig, draw_outlines: bool, calibration_page: bool) -> ImpositionConfig:
	"""
	Return a config with debug flags overridden from CLI args.
	"""
	return dataclasses.replace(
		config,
		draw_outlines=draw_outlines,
		calibration_page=calibration_page,
	)


#============================================
def validate_config(config: ImpositionConfig) -> None:
	"""
	Validate that label cells fit on a letter page.
	"""
	page_width, page_height = reportlab.lib.pagesizes.letter
	if config.columns <= 0 or config.rows <= 0:
		raise ValueError("columns and rows must be positive")
	if config.label_width <= 0 or config.label_height <= 0:
		raise ValueError("label dimensions must be positive")
	for row in range(config.rows):
		for col in range(config.columns):
			x0, y0, x1, y1 = slot_bbox(config, row, col)
			if x0 < 0 or y0 < 0 or x1 > page_width or y1 > page_height:
				raise ValueError(f"slot out of page bounds for {config.name}: row={row} col={col}")
	if config.content_inset * 2 >= config.label_width or config.content_inset * 2 >= config.label_height:
		raise ValueError("content_inset too large for label dimensions")


#============================================
def slots_per_page(config: ImpositionConfig) -> int:
	"""
	Number of labels on one sheet.
	"""
	return config.columns * config.rows


#============================================
def slot_position(config: ImpositionConfig, row: int, col: int) -> tuple[float, float]:
	"""
	Bottom-left position for a slot.
	"""
	page_width, page_height = reportlab.lib.pagesizes.letter
	_ = page_width
	x = config.left_margin + col * (config.label_width + config.h_gap)
	y = page_height - config.top_margin - config.label_height - row * (config.label_height + config.v_gap)
	return (x, y)


#============================================
def slot_bbox(config: ImpositionConfig, row: int, col: int) -> tuple[float, float, float, float]:
	"""
	Bounding box for a slot.
	"""
	x, y = slot_position(config, row, col)
	return (x, y, x + config.label_width, y + config.label_height)


#============================================
def content_bbox(config: ImpositionConfig, row: int, col: int) -> tuple[float, float, float, float]:
	"""
	Inner content area inside a slot.
	"""
	x0, y0, x1, y1 = slot_bbox(config, row, col)
	return (
		x0 + config.content_inset,
		y0 + config.content_inset,
		x1 - config.content_inset,
		y1 - config.content_inset,
	)


#============================================
def page_slot_indices(config: ImpositionConfig) -> list[tuple[int, int]]:
	"""
	Return row/col slot order for one page.
	"""
	indices = []
	for row in range(config.rows):
		for col in range(config.columns):
			indices.append((row, col))
	return indices


#============================================
def draw_debug_outlines(pdf, config: ImpositionConfig) -> None:
	"""
	Draw slot and content guides.
	"""
	pdf.saveState()
	for row, col in page_slot_indices(config):
		x0, y0, x1, y1 = slot_bbox(config, row, col)
		pdf.setLineWidth(0.35)
		pdf.setStrokeColorRGB(0.8, 0.0, 0.0)
		pdf.rect(x0, y0, x1 - x0, y1 - y0, stroke=1, fill=0)
		cx0, cy0, cx1, cy1 = content_bbox(config, row, col)
		pdf.setLineWidth(0.2)
		pdf.setStrokeColorRGB(0.1, 0.2, 0.8)
		pdf.rect(cx0, cy0, cx1 - cx0, cy1 - cy0, stroke=1, fill=0)
	pdf.restoreState()


#============================================
def draw_calibration_page(pdf, config: ImpositionConfig) -> None:
	"""
	Draw a calibration page with simple rulers and slot boxes.
	"""
	page_width, page_height = reportlab.lib.pagesizes.letter
	pdf.setFont(DEFAULT_BOLD_FONT_NAME, 11)
	pdf.drawString(24, page_height - 24, f"Calibration: {config.name}")
	pdf.setFont(DEFAULT_FONT_NAME, 9)
	pdf.drawString(24, page_height - 38, "Use this page to check print alignment before using label stock.")
	pdf.setLineWidth(0.6)
	pdf.line(24, page_height - 60, 24 + POINTS_PER_INCH, page_height - 60)
	pdf.drawString(24, page_height - 72, "1 inch")
	pdf.line(24, page_height - 90, 24, page_height - 90 + POINTS_PER_INCH)
	pdf.drawString(30, page_height - 90 + POINTS_PER_INCH + 4, "1 inch")
	draw_debug_outlines(pdf, config)
	pdf.showPage()


#============================================
def fit_font_size(text: str, font_name: str, max_width: float, preferred: list[float], minimum: float) -> float:
	"""
	Return the largest preferred size that fits max width.
	"""
	if text is None:
		return minimum
	for size in preferred:
		width = reportlab.pdfbase.pdfmetrics.stringWidth(text, font_name, size)
		if width <= max_width:
			return size
	size = preferred[-1] if preferred else minimum
	while size > minimum:
		width = reportlab.pdfbase.pdfmetrics.stringWidth(text, font_name, size)
		if width <= max_width:
			return size
		size -= 0.5
	return minimum


#============================================
def draw_fitted_text(pdf, text: str, x: float, y: float, max_width: float, font_name: str,
		preferred_sizes: list[float], minimum_size: float, line_gap: float = 0.0) -> tuple[float, float]:
	"""
	Draw one-line text with font-size fallback.
	"""
	size = fit_font_size(text, font_name, max_width, preferred_sizes, minimum_size)
	pdf.setFont(font_name, size)
	pdf.drawString(x, y, text)
	return (size, y - size - line_gap)


#============================================
def draw_image_fit(pdf, image_path: str, x: float, y: float, width: float, height: float) -> None:
	"""
	Draw image fitted to a target box while preserving aspect ratio.
	"""
	if image_path is None or not os.path.exists(image_path):
		return
	pdf.drawImage(
		image_path,
		x,
		y,
		width=width,
		height=height,
		mask="auto",
		preserveAspectRatio=True,
		anchor="c",
	)

