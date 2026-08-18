import io
from pathlib import Path

import pdfplumber

DEFAULT_RESOLUTION_DPI = 150  # matches ../poc-01/scripts/render_pages.py's default


class PageRenderError(Exception):
    pass


def render_page_png(
    pdf_path: Path, page_number: int, resolution: int = DEFAULT_RESOLUTION_DPI
) -> tuple[bytes, int, int, float, float]:
    """Render a 1-indexed page of the PDF at pdf_path to PNG bytes.

    Returns (png_bytes, image_width_px, image_height_px, page_width_pt, page_height_pt).

    Coordinate relationship: pdfplumber's word bounding boxes (as returned by
    POST /extract) and page.width/page.height are both in PDF points, with the origin
    at the top-left of the page and "top"/"bottom" increasing downward. page.to_image()
    renders in that same top-left-origin space at a uniform scale of resolution/72 in
    both axes, so pixel_x = point_x * (resolution / 72) and pixel_y = point_y *
    (resolution / 72) with no flip and no separate x/y scale -- aspect ratio is
    preserved by construction, not by any extra transformation here.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[page_number - 1]
            page_image = page.to_image(resolution=resolution)
            buffer = io.BytesIO()
            page_image.original.save(buffer, format="PNG")
            width_px, height_px = page_image.original.size
            return buffer.getvalue(), width_px, height_px, page.width, page.height
    except IndexError as exc:
        raise PageRenderError("Page number out of range.") from exc
    except Exception as exc:
        raise PageRenderError("Unable to render the requested page.") from exc
