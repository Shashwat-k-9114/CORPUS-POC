import type { ProcessingState } from "@/lib/types";
import styles from "./Corpus.module.css";

export const STATUS_MEANINGS: Record<ProcessingState, string> = {
  queued: "Safely admitted and awaiting processing",
  processing: "Worker is actively processing the source",
  completed: "All pages produced durable representations",
  partial: "Some pages are available and some failed",
  failed: "Processing failed; the canonical source remains preserved",
};

export default function StatusBadge({ state }: { state: ProcessingState }) {
  return <span className={`${styles.status} ${styles[state]}`} title={STATUS_MEANINGS[state]}>{state}</span>;
}
