"use client";

import Link from "next/link";
import type { Corpus, Custodian } from "@/lib/types";
import styles from "./Corpus.module.css";

interface ContextBarProps {
  custodians: Custodian[];
  corpora: Corpus[];
  custodianId: string;
  corpusId: string;
  onCustodianChange: (value: string) => void;
  onCorpusChange: (value: string) => void;
}

export default function ContextBar({
  custodians,
  corpora,
  custodianId,
  corpusId,
  onCustodianChange,
  onCorpusChange,
}: ContextBarProps) {
  const query = custodianId && corpusId ? `?custodian_id=${custodianId}&corpus_id=${corpusId}` : "";
  return (
    <div className={styles.context} aria-label="Corpus context">
      <label className={styles.field}>
        <span className={styles.label}>Custodian</span>
        <select className={styles.select} value={custodianId} onChange={(event) => onCustodianChange(event.target.value)}>
          <option value="">Select custodian</option>
          {custodians.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.slug}</option>)}
        </select>
      </label>
      <label className={styles.field}>
        <span className={styles.label}>Custodian corpus</span>
        <select className={styles.select} value={corpusId} onChange={(event) => onCorpusChange(event.target.value)} disabled={!custodianId}>
          <option value="">Select corpus</option>
          {corpora.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
        {query && <span className={styles.muted}><Link href={`/${query}`}>Register context link</Link></span>}
      </label>
    </div>
  );
}
