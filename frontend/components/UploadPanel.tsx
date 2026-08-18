"use client";

import { useRef, useState } from "react";
import { ApiError, extractDocument, type ExtractPhase } from "@/lib/api";
import type { DocumentExtractionResponse } from "@/lib/types";
import styles from "./UploadPanel.module.css";

type Status = "idle" | "uploading" | "extracting" | "error";

interface UploadPanelProps {
  onExtracted: (result: DocumentExtractionResponse) => void;
}

export default function UploadPanel({ onExtracted }: UploadPanelProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const busy = status === "uploading" || status === "extracting";

  function pickFile(file: File | undefined) {
    if (!file) return;
    setSelectedFile(file);
    setStatus("idle");
    setErrorMessage(null);
  }

  async function handleUpload() {
    if (!selectedFile) return;
    setStatus("uploading");
    setErrorMessage(null);
    try {
      const onPhaseChange = (phase: ExtractPhase) => setStatus(phase);
      const result = await extractDocument(selectedFile, onPhaseChange);
      onExtracted(result);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Something went wrong while uploading.";
      setStatus("error");
      setErrorMessage(message);
    }
  }

  return (
    <div className={styles.panel}>
      <h1 className={styles.title}>Corpus</h1>
      <p className={styles.subtitle}>Upload a native-text PDF to inspect its extraction and provenance.</p>

      <label
        className={styles.dropzone}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          pickFile(e.dataTransfer.files?.[0]);
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          hidden
          onChange={(e) => pickFile(e.target.files?.[0])}
        />
        {selectedFile ? (
          <div className={styles.fileName}>{selectedFile.name}</div>
        ) : (
          <div>Click to choose a PDF, or drag one here</div>
        )}
        <div className={styles.hint}>Up to 20&nbsp;MB. Native text PDFs only -- no OCR.</div>
      </label>

      <button
        type="button"
        className={styles.button}
        disabled={!selectedFile || busy}
        onClick={handleUpload}
      >
        {busy ? "Working…" : "Upload & Extract"}
      </button>

      {busy && (
        <div className={styles.statusRow}>
          <span className={styles.spinner} aria-hidden />
          <span>
            {status === "uploading"
              ? "Uploading…"
              : "Extracting… this can take over a minute for large documents."}
          </span>
        </div>
      )}

      {status === "error" && errorMessage && (
        <div className={styles.error} role="alert">
          {errorMessage}
        </div>
      )}
    </div>
  );
}
