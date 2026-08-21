"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, listJobs, listWorkers, retryJob } from "@/lib/api";
import { useCorpusContext } from "@/lib/useCorpusContext";
import type { ProcessingJob, ProcessingState, WorkerHeartbeat } from "@/lib/types";
import ContextBar from "./ContextBar";
import StatusBadge from "./StatusBadge";
import styles from "./Corpus.module.css";

const STATES: Array<ProcessingState | ""> = ["", "queued", "processing", "completed", "partial", "failed"];
function formatDate(value: string | null) { return value ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "—"; }

export default function MonitorView() {
  const context = useCorpusContext();
  const [jobs, setJobs] = useState<ProcessingJob[]>([]);
  const [workers, setWorkers] = useState<WorkerHeartbeat[]>([]);
  const [filter, setFilter] = useState<ProcessingState | "">("");
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState<string | null>(null);
  const load = useCallback(async (signal?: AbortSignal) => {
    if (!context.custodianId) return false;
    try {
      const [jobPage, workerRows] = await Promise.all([listJobs(context.custodianId, filter || undefined, 100, 0, signal), listWorkers(signal)]);
      setJobs(jobPage.items); setWorkers(workerRows); setError(null);
      return jobPage.items.some((job) => job.state === "queued" || job.state === "processing");
    } catch (reason: unknown) {
      if (reason instanceof DOMException && reason.name === "AbortError") return false;
      setError(reason instanceof ApiError ? reason.message : "Unable to refresh processing status.");
      return false;
    }
  }, [context.custodianId, filter]);
  useEffect(() => {
    const controller = new AbortController(); let timer: ReturnType<typeof setTimeout> | undefined;
    const refresh = async () => { const active = await load(controller.signal); timer = setTimeout(refresh, active ? 3000 : 12000); };
    void refresh(); return () => { controller.abort(); if (timer) clearTimeout(timer); };
  }, [load]);
  const activeWorkers = useMemo(() => workers.filter((worker) => worker.status === "processing"), [workers]);
  async function doRetry(jobId: string) { setRetrying(jobId); try { await retryJob(jobId, context.custodianId); await load(); } catch (reason: unknown) { setError(reason instanceof ApiError ? reason.message : "Retry could not be queued."); } finally { setRetrying(null); } }
  const query = `custodian_id=${context.custodianId}&corpus_id=${context.corpusId}`;
  return <main className={styles.shell}><header className={styles.header}><div><div className={styles.eyebrow}>Processing monitor</div><h1 className={styles.title}>Operational queue</h1><p className={styles.subtitle}>The monitor reports durable job state, checkpoints, attempts, leases and worker heartbeats. It never manufactures progress.</p></div><nav className={styles.nav} aria-label="Primary"><Link href={`/?${query}`}>Register</Link><Link href={`/admit?${query}`}>Admit sources</Link><Link href={`/monitor?custodian_id=${context.custodianId}`}>Monitor</Link></nav></header><ContextBar {...context} onCustodianChange={context.setCustodianId} onCorpusChange={context.setCorpusId} />{error && <div className={styles.error} role="alert">{error}</div>}<div className={styles.grid}><div className={styles.metric}><span className={styles.metricValue}>{jobs.filter((job) => job.state === "queued").length}</span><span className={styles.metricLabel}>Queued</span></div><div className={styles.metric}><span className={styles.metricValue}>{jobs.filter((job) => job.state === "processing").length}</span><span className={styles.metricLabel}>Active</span></div><div className={styles.metric}><span className={styles.metricValue}>{activeWorkers.length}</span><span className={styles.metricLabel}>Active workers</span></div><div className={styles.metric}><span className={styles.metricValue}>{jobs.filter((job) => job.state === "partial").length}</span><span className={styles.metricLabel}>Partial</span></div><div className={styles.metric}><span className={styles.metricValue}>{jobs.filter((job) => job.state === "failed").length}</span><span className={styles.metricLabel}>Failed</span></div></div><section className={styles.card}><div className={styles.toolbar}><div><h2 className={styles.cardTitle}>Jobs</h2><span className={styles.muted}>{jobs.length} durable jobs in this view</span></div><select className={styles.select} value={filter} onChange={(event) => setFilter(event.target.value as ProcessingState | "")} aria-label="Filter jobs by state">{STATES.map((state) => <option key={state} value={state}>{state || "All states"}</option>)}</select></div>{jobs.length === 0 ? <div className={styles.empty}>No processing jobs match this filter.</div> : <div className={styles.tableWrap}><table className={styles.table}><thead><tr><th>Job / source</th><th>State</th><th>Progress</th><th>Lease / heartbeat</th><th>Attempts</th><th>Latest error</th><th /></tr></thead><tbody>{jobs.map((job) => <tr key={job.id}><td><span className={styles.mono}>{job.id.slice(0, 12)}…</span><div className={styles.muted}>source {job.source_id.slice(0, 12)}…</div></td><td><StatusBadge state={job.state} /></td><td>{job.completed_pages} / {job.total_pages ?? "?"}<div className={styles.muted}>{job.failed_pages ? `${job.failed_pages} failed` : ""}</div></td><td>{job.lease_owner ? <><span className={styles.mono}>{job.lease_owner}</span><div className={styles.muted}>heartbeat {formatDate(job.heartbeat_at)}</div></> : <span className={styles.muted}>not leased</span>}</td><td>{job.attempt_count} attempts · {job.retry_count} retries</td><td>{job.last_error ? <span className={styles.error}>{job.last_error}</span> : <span className={styles.muted}>—</span>}</td><td><div className={styles.toolbarGroup}><Link href={`/sources/${job.source_id}?${query}`}>Source</Link>{(job.state === "failed" || job.state === "partial") && <button className={`${styles.buttonSecondary} ${styles.buttonDanger}`} disabled={retrying === job.id} onClick={() => void doRetry(job.id)}>{retrying === job.id ? "Retrying…" : "Retry"}</button>}</div></td></tr>)}</tbody></table></div>}</section><section className={styles.card}><div className={styles.cardHeader}><h2 className={styles.cardTitle}>Worker heartbeats</h2><span className={styles.muted}>Persisted status; stale workers remain visible</span></div><ul className={styles.list}>{workers.length === 0 ? <li className={styles.empty}>No worker heartbeat has been recorded.</li> : workers.map((worker) => <li className={styles.listItem} key={worker.worker_id}><strong className={styles.mono}>{worker.worker_id}</strong><div className={styles.muted}>{worker.status} · last seen {formatDate(worker.last_seen_at)} {worker.active_job_id ? `· job ${worker.active_job_id}` : ""}</div></li>)}</ul></section></main>;
}
