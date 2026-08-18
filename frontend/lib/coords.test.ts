import { describe, expect, it } from "vitest";
import { pointToPixel, regionToPixelRect } from "./coords";
import type { Region } from "./types";

describe("pointToPixel", () => {
  it("applies the documented pixel = point * (dpi / 72) formula", () => {
    expect(pointToPixel(72, 150)).toBeCloseTo(150);
    expect(pointToPixel(0, 150)).toBe(0);
    expect(pointToPixel(1190.55, 150)).toBeCloseTo(2480.3125, 4);
  });

  it("scales to 1:1 at 72 dpi (native PDF point space)", () => {
    expect(pointToPixel(841.89, 72)).toBeCloseTo(841.89);
  });
});

describe("regionToPixelRect", () => {
  const region: Region = {
    text: "Integrated",
    bbox: { x0: 51.0, x1: 108.06, top: 44.34, bottom: 53.34 },
    page_number: 22,
    order_index: 0,
    extraction_method: "pdfplumber_extract_words",
    confidence: null,
  };

  it("maps a bbox to a pixel rect at the given resolution", () => {
    const rect = regionToPixelRect(region, 150);
    const scale = 150 / 72;
    expect(rect.x).toBeCloseTo(51.0 * scale);
    expect(rect.y).toBeCloseTo(44.34 * scale);
    expect(rect.width).toBeCloseTo((108.06 - 51.0) * scale);
    expect(rect.height).toBeCloseTo((53.34 - 44.34) * scale);
  });

  it("produces a positive-area rect for a well-formed bbox", () => {
    const rect = regionToPixelRect(region, 150);
    expect(rect.width).toBeGreaterThan(0);
    expect(rect.height).toBeGreaterThan(0);
  });
});
