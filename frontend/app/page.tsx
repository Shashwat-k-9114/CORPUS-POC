"use client";

import { useState } from "react";
import DocumentSummary from "@/components/DocumentSummary";
import PageViewer from "@/components/PageViewer";
import ProvenancePanel from "@/components/ProvenancePanel";
import UploadPanel from "@/components/UploadPanel";
import type { DocumentExtractionResponse, Region } from "@/lib/types";
import styles from "./page.module.css";

export default function Home() {
  const [documentData, setDocumentData] = useState<DocumentExtractionResponse | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedRegion, setSelectedRegion] = useState<Region | null>(null);

  function handleExtracted(result: DocumentExtractionResponse) {
    setDocumentData(result);
    setCurrentPage(1);
    setSelectedRegion(null);
  }

  function handlePageChange(page: number) {
    setCurrentPage(page);
    setSelectedRegion(null);
  }

  function handleReset() {
    setDocumentData(null);
    setCurrentPage(1);
    setSelectedRegion(null);
  }

  if (!documentData) {
    return (
      <main className={styles.page}>
        <UploadPanel onExtracted={handleExtracted} />
      </main>
    );
  }

  const currentPageData = documentData.pages[currentPage - 1];

  return (
    <main className={styles.page}>
      <DocumentSummary
        doc={documentData}
        currentPage={currentPage}
        onPageChange={handlePageChange}
        onReset={handleReset}
      />
      <div className={styles.workspace}>
        <PageViewer
          key={`${documentData.document_id}-${currentPage}`}
          documentId={documentData.document_id}
          pageNumber={currentPage}
          regions={currentPageData?.regions ?? []}
          selectedRegion={selectedRegion}
          onRegionSelect={setSelectedRegion}
        />
        <ProvenancePanel documentId={documentData.document_id} region={selectedRegion} />
      </div>
    </main>
  );
}
