"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { admitSource, ApiError, getJob } from "@/lib/api";
import { useCorpusContext } from "@/lib/useCorpusContext";
import type { AdmissionReceipt, ProcessingJob } from "@/lib/types";
import ContextBar from "./ContextBar";
import StatusBadge from "./StatusBadge";
import styles from "./Corpus.module.css";

interface FileResult { file: File; progress: number; receipt: AdmissionReceipt | null; job: ProcessingJob | null; error: string | null; }

export default function AdmissionView() {
  const context = useCorpusContext();
  const [files, setFiles] = useState<FileResult[]>([]);
  const [arrivalChannel, setArrivalChannel] = useState("reviewer-upload");
  const [claimedOrigin, setClaimedOrigin] = useState("");
  const [obtainedFrom, setObtainedFrom] = useState("");
  const [busy, setBusy] = useState(false);
  const query = `custodian_id=${context.custodianId}&corpus_id=${context.corpusId}`;

  const canAdmit = Boolean(context.custodianId && context.corpusId && files.length && !busy);
  const selectedNames = useMemo(() => new Set(files.map((item) => item.file.name)), [files]);

  function selectFiles(value: FileList | null) {
    const next = Array.from(value ?? []).filter((file) => file.name.toLowerCase().endsWith(".pdf") && !selectedNames.has(file.name));
    setFiles((current) => [...current, ...next.map((file) => ({ file, progress: 0, receipt: null, job: null, error: null }))]);
  }

  async function admitAll() {
    if (!canAdmit) return;
    setBusy(true);
    await Promise.all(files.map(async (entry, index) => {
      try {
        const receipt = await admitSource(entry.file, { custodianId: context.custodianId, corpusId: context.corpusId, arrivalChannel, claimedOrigin: claimedOrigin || undefined, obtainedFrom: obtainedFrom || undefined, idempotencyKey: `ui-${crypto.randomUUID()}`, onProgress: (progress) => setFiles((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, progress } : item)) });
        setFiles((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, progress: 100, receipt } : item));
        let job = receipt.processing_job;
        for (let attempt = 0; attempt < 40 && (job.state === "queued" || job.state === "processing"); attempt += 1) {
          await new Promise((resolve) => setTimeout(resolve, 2000));
          job = await getJob(job.id, context.custodianId);
          setFiles((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, job } : item));
        }
        setFiles((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, job } : item));
      } catch (reason: unknown) {
        setFiles((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, error: reason instanceof ApiError ? reason.message : "Admission failed." } : item));
      }
    }));
    setBusy(false);
  }

  return <main className={styles.shell}>
    <header className={styles.header}><div><div className={styles.eyebrow}>Admit sources</div><h1 className={styles.title}>Preserve first. Process later.</h1><p className={styles.subtitle}>Each PDF is streamed into canonical storage and immediately receives durable source, enrollment, arrival and queued-job identities.</p></div><nav className={styles.nav} aria-label="Primary"><Link href={`/?${query}`}>Register</Link><Link href={`/admit?${query}`}>Admit sources</Link><Link href={`/monitor?custodian_id=${context.custodianId}`}>Processing monitor</Link></nav></header>
    <ContextBar {...context} onCustodianChange={context.setCustodianId} onCorpusChange={context.setCorpusId} />
    <section className={styles.card}>
      <div className={styles.toolbar}><div><h2 className={styles.cardTitle}>Admission context</h2><p className={styles.muted}>A successful admission does not wait for extraction.</p></div><button type="button" className={styles.button} disabled={!canAdmit} onClick={() => void admitAll()}>{busy ? "Admitting…" : `Admit ${files.length || "selected"} PDF${files.length === 1 ? "" : "s"}`}</button></div>
      <div className={styles.context}>
        <label className={styles.field}><span className={styles.label}>Arrival channel</span><input className={styles.input} value={arrivalChannel} onChange={(event) => setArrivalChannel(event.target.value)} /></label>
        <label className={styles.field}><span className={styles.label}>Claimed origin <span className={styles.muted}>(optional)</span></span><input className={styles.input} value={claimedOrigin} onChange={(event) => setClaimedOrigin(event.target.value)} /></label>
        <label className={styles.field}><span className={styles.label}>Obtained from <span className={styles.muted}>(optional)</span></span><input className={styles.input} value={obtainedFrom} onChange={(event) => setObtainedFrom(event.target.value)} /></label>
      </div>
      <label className={styles.dropzone}><strong>Choose one or more PDFs</strong><span className={styles.muted}>The browser sends each file independently; no extraction runs in this request.</span><input type="file" accept="application/pdf,.pdf" multiple onChange={(event) => selectFiles(event.target.files)} /></label>
      {files.length === 0 && <div className={styles.empty}>No files selected.</div>}
      <ul className={styles.list}>{files.map((entry, index) => <li className={styles.fileRow} key={`${entry.file.name}-${entry.file.lastModified}-${index}`}><div><strong>{entry.file.name}</strong><div className={styles.muted}>{(entry.file.size / 1024 / 1024).toFixed(2)} MB · upload {entry.progress}%</div><div className={styles.progress}><span style={{ width: `${entry.progress}%` }} /></div>{entry.error && <div className={styles.error} role="alert">{entry.error}</div>}{entry.receipt && <div className={styles.notice}>Source <span className={styles.mono}>{entry.receipt.source.id}</span> · {entry.receipt.exact_duplicate ? "exact duplicate reused" : "new canonical object"} · enrollment recorded</div>}</div><div>{entry.job ? <StatusBadge state={entry.job.state} /> : entry.receipt ? <StatusBadge state="queued" /> : <span className={styles.muted}>Waiting</span>}</div></li>)}</ul>
    </section>
    {files.some((entry) => entry.receipt) && <section className={styles.card}><div className={styles.cardHeader}><h2 className={styles.cardTitle}>Admission receipts</h2><Link href={`/?${query}`}>Open register</Link></div><ul className={styles.list}>{files.filter((entry) => entry.receipt).map((entry, index) => { const receipt = entry.receipt!; return <li className={styles.listItem} key={`${receipt.source.id}:${index}`}><strong>{entry.file.name}</strong><div className={styles.muted}>source <span className={styles.mono}>{receipt.source.id}</span> · job <span className={styles.mono}>{receipt.processing_job.id}</span></div><div className={styles.toolbarGroup}><span>{receipt.exact_duplicate ? "Exact duplicate: canonical reused" : "Canonical object created"}</span><span>{receipt.idempotent_replay ? "Idempotent replay" : "Arrival recorded"}</span><Link href={`/sources/${receipt.source.id}?${query}`}>Inspect source</Link></div></li>; })}</ul></section>}
  </main>;
}
