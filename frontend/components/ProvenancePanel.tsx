import type { Region } from "@/lib/types";
import styles from "./ProvenancePanel.module.css";

interface ProvenancePanelProps {
  documentId: string;
  region: Region | null;
}

export default function ProvenancePanel({ documentId, region }: ProvenancePanelProps) {
  return (
    <div className={styles.panel}>
      <h2 className={styles.title}>Provenance</h2>

      {!region ? (
        <p className={styles.empty}>Click a highlighted word on the page to inspect where it came from.</p>
      ) : (
        <>
          <div className={styles.text}>&ldquo;{region.text}&rdquo;</div>
          <div className={styles.rows}>
            <span className={styles.label}>document_id</span>
            <span className={styles.value}>{documentId}</span>

            <span className={styles.label}>page_number</span>
            <span className={styles.value}>{region.page_number}</span>

            <span className={styles.label}>order_index</span>
            <span className={styles.value}>{region.order_index}</span>

            <span className={styles.label}>extraction_method</span>
            <span className={styles.value}>{region.extraction_method}</span>

            <span className={styles.label}>bbox.x0</span>
            <span className={styles.value}>{region.bbox.x0}</span>

            <span className={styles.label}>bbox.x1</span>
            <span className={styles.value}>{region.bbox.x1}</span>

            <span className={styles.label}>bbox.top</span>
            <span className={styles.value}>{region.bbox.top}</span>

            <span className={styles.label}>bbox.bottom</span>
            <span className={styles.value}>{region.bbox.bottom}</span>

            <span className={styles.label}>confidence</span>
            {region.confidence === null ? (
              <span
                className={`${styles.value} ${styles.confidenceNull}`}
                data-testid="confidence-value"
              >
                not provided (pdfplumber&apos;s native-text extraction has no confidence
                score -- never fabricated)
              </span>
            ) : (
              <span className={styles.value} data-testid="confidence-value">
                {region.confidence}
              </span>
            )}
          </div>
        </>
      )}
    </div>
  );
}
