import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import DocumentSummary from "./DocumentSummary";
import type { DocumentExtractionResponse } from "@/lib/types";

function makeDoc(pageCount: number): DocumentExtractionResponse {
  return {
    document_id: "doc-123",
    filename: "test.pdf",
    page_count: pageCount,
    extraction_method: "pdfplumber_extract_words",
    extraction_engine_version: "0.11.10",
    pages: Array.from({ length: pageCount }, (_, i) => ({
      page_number: i + 1,
      width: 200,
      height: 200,
      word_count: 0,
      regions: [],
    })),
  };
}

describe("DocumentSummary", () => {
  it("shows the page-22 and page-81 quick jumps for a large document like the RIL report", () => {
    render(
      <DocumentSummary doc={makeDoc(147)} currentPage={1} onPageChange={vi.fn()} onReset={vi.fn()} />,
    );
    expect(screen.getByRole("button", { name: /page 22/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /page 81/i })).toBeInTheDocument();
  });

  it("hides quick jumps that exceed the document's actual page count", () => {
    render(
      <DocumentSummary doc={makeDoc(5)} currentPage={1} onPageChange={vi.fn()} onReset={vi.fn()} />,
    );
    expect(screen.queryByRole("button", { name: /page 22/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /page 81/i })).not.toBeInTheDocument();
  });

  it("displays document metadata", () => {
    render(
      <DocumentSummary doc={makeDoc(147)} currentPage={1} onPageChange={vi.fn()} onReset={vi.fn()} />,
    );
    expect(screen.getByText("test.pdf")).toBeInTheDocument();
    expect(screen.getByTestId("page-count")).toHaveTextContent("147");
    expect(screen.getByTestId("document-id")).toHaveTextContent("doc-123");
  });
});
