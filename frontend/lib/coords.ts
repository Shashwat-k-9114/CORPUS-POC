import type { Region } from "./types";

// Backend contract (see backend/app/rendering.py and backend/README.md):
// pixel = point * (resolutionDpi / 72), same top-left origin as pdfplumber's own
// bbox convention, uniform scale on both axes -- no flip, no separate x/y factor.
export function pointToPixel(pointValue: number, resolutionDpi: number): number {
  return pointValue * (resolutionDpi / 72);
}

export interface PixelRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export function regionToPixelRect(region: Region, resolutionDpi: number): PixelRect {
  const x0 = pointToPixel(region.bbox.x0, resolutionDpi);
  const x1 = pointToPixel(region.bbox.x1, resolutionDpi);
  const top = pointToPixel(region.bbox.top, resolutionDpi);
  const bottom = pointToPixel(region.bbox.bottom, resolutionDpi);
  return { x: x0, y: top, width: x1 - x0, height: bottom - top };
}
