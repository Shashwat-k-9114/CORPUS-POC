import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ProvenancePanel from "./ProvenancePanel";
import type { Region } from "@/lib/types";

const region: Region = {
  text: "Hello",
  bbox: { x0: 20, x1: 74.67, top: 80.97, bottom: 104.97 },
  page_number: 1,
  order_index: 0,
  extraction_method: "pdfplumber_extract_words",
  confidence: null,
};

describe("ProvenancePanel", () => {
  it("shows an empty-state prompt when nothing is selected", () => {
    render(<ProvenancePanel documentId="doc-1" region={null} />);
    expect(screen.getByText(/click a highlighted word/i)).toBeInTheDocument();
  });

  it("renders the selected word's text and provenance fields", () => {
    render(<ProvenancePanel documentId="doc-1" region={region} />);
    expect(screen.getByText(/"Hello"|"Hello"|Hello/)).toBeInTheDocument();
    expect(screen.getByText("doc-1")).toBeInTheDocument();
    expect(screen.getByText("pdfplumber_extract_words")).toBeInTheDocument();
    expect(screen.getByText("0")).toBeInTheDocument(); // order_index
  });

  it("never fabricates a confidence value -- shows an explicit not-provided message instead", () => {
    render(<ProvenancePanel documentId="doc-1" region={region} />);
    const confidenceValue = screen.getByTestId("confidence-value");
    expect(confidenceValue).toHaveTextContent(/not provided/i);
    expect(confidenceValue).not.toHaveTextContent(/^0(\.0+)?$/);
    expect(confidenceValue).not.toHaveTextContent(/^null$/);
  });

  it("displays a real confidence value when one is present, without inventing the null-case copy", () => {
    render(<ProvenancePanel documentId="doc-1" region={{ ...region, confidence: 0.92 }} />);
    const confidenceValue = screen.getByTestId("confidence-value");
    expect(confidenceValue).toHaveTextContent("0.92");
    expect(confidenceValue).not.toHaveTextContent(/not provided/i);
  });
});
