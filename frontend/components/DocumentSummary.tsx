"use client";

import { useState } from "react";
import type { DocumentExtractionResponse } from "@/lib/types";
import styles from "./DocumentSummary.module.css";

// Representative pages named in the Phase 3/4 research: page 22 was the worst
// reading-order failure, page 81 the worst table failure (see ../poc-01
// Experiment 1). Surfaced here as one-click demo shortcuts.
const NOTABLE_PAGES = [
  { page: 22, label: "Page 22 (harder layout)" },
  { page: 81, label: "Page 81 (harder tables)" },
];

interface DocumentSummaryProps {
  doc: DocumentExtractionResponse;
  currentPage: number;
  onPageChange: (page: number) => void;
  onReset: () => void;
}

export default function DocumentSummary({
  doc,
  currentPage,
  onPageChange,
  onReset,
}: DocumentSummaryProps) {
  const [pageInput, setPageInput] = useState(String(currentPage));

  function commitPageInput() {
    const parsed = parseInt(pageInput, 10);
    if (Number.isFinite(parsed) && parsed >= 1 && parsed <= doc.page_count) {
      onPageChange(parsed);
    } else {
      setPageInput(String(currentPage));
    }
  }

  function goTo(page: number) {
    const clamped = Math.min(Math.max(page, 1), doc.page_count);
    setPageInput(String(clamped));
    onPageChange(clamped);
  }

  return (
    <div className={styles.bar}>
      <div>
        <div className={styles.filename}>{doc.filename}</div>
        <div className={styles.meta}>
          <span data-testid="page-count">
            <strong>{doc.page_count}</strong> pages
          </span>
          <span>
            method: <strong>{doc.extraction_method}</strong> (pdfplumber{" "}
            {doc.extraction_engine_version})
          </span>
          <span className="mono" data-testid="document-id">
            id: {doc.document_id}
          </span>
        </div>
      </div>

      <div className={styles.nav}>
        <div className={styles.quickJumps}>
          {NOTABLE_PAGES.filter((n) => n.page <= doc.page_count).map((n) => (
            <button
              key={n.page}
              type="button"
              className={`${styles.quickJump} ${currentPage === n.page ? styles.quickJumpActive : ""}`}
              onClick={() => goTo(n.page)}
            >
              {n.label}
            </button>
          ))}
        </div>

        <button
          type="button"
          className={styles.navButton}
          disabled={currentPage <= 1}
          onClick={() => goTo(currentPage - 1)}
          aria-label="Previous page"
        >
          &larr;
        </button>
        <input
          className={styles.pageInput}
          value={pageInput}
          onChange={(e) => setPageInput(e.target.value)}
          onBlur={commitPageInput}
          onKeyDown={(e) => {
            if (e.key === "Enter") commitPageInput();
          }}
          inputMode="numeric"
          aria-label="Page number"
        />
        <span className={styles.pageCount}>/ {doc.page_count}</span>
        <button
          type="button"
          className={styles.navButton}
          disabled={currentPage >= doc.page_count}
          onClick={() => goTo(currentPage + 1)}
          aria-label="Next page"
        >
          &rarr;
        </button>

        <button type="button" className={styles.resetButton} onClick={onReset}>
          New document
        </button>
      </div>
    </div>
  );
}
