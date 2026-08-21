"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, fetchCanonical, getSource, listJobAttempts, listJobPages, listJobs, listRepresentations, retryJob } from "@/lib/api";
import type { DerivedRepresentation, PageCheckpoint, ProcessingAttempt, ProcessingJob, SourceDetail } from "@/lib/types";
import StatusBadge from "./StatusBadge";
import styles from "./Corpus.module.css";

interface Props { sourceId: string; custodianId: string; corpusId: string; }
function formatDate(value: string | null) { return value ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "—"; }
function formatSize(bytes: number) { return `${(bytes / 1024 / 1024).toFixed(2)} MB`; }

export default function SourceDetailView({ sourceId, custodianId, corpusId }: Props) {
  const [detail, setDetail] = useState<SourceDetail | null>(null);
  const [job, setJob] = useState<ProcessingJob | null>(null);
  const [pages, setPages] = useState<PageCheckpoint[]>([]);
  const [attempts, setAttempts] = useState<ProcessingAttempt[]>([]);
  const [representations, setRepresentations] = useState<DerivedRepresentation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const query = `custodian_id=${custodianId}&corpus_id=${corpusId}`;

  const load = useCallback(async (signal?: AbortSignal) => {
    try {
      const source = await getSource(sourceId, custodianId, signal);
      const jobs = await listJobs(custodianId, undefined, 100, 0, signal);
      const sourceJob = jobs.items.filter((item) => item.source_id === sourceId).sort((a, b) => b.created_at.localeCompare(a.created_at))[0] ?? null;
      setDetail(source); setJob(sourceJob);
      if (sourceJob) {
        const [checkpointRows, attemptRows] = await Promise.all([listJobPages(sourceJob.id, custodianId, signal), listJobAttempts(sourceJob.id, custodianId, signal)]);
        setPages(checkpointRows); setAttempts(attemptRows);
      } else { setPages([]); setAttempts([]); }
      setRepresentations(await listRepresentations(sourceId, custodianId, signal));
      setError(null);
      return Boolean(sourceJob && (sourceJob.state === "queued" || sourceJob.state === "processing"));
    } catch (reason: unknown) {
      if (reason instanceof DOMException && reason.name === "AbortError") return false;
      setError(reason instanceof ApiError ? reason.message : "Unable to load this source.");
      return false;
    }
  }, [custodianId, sourceId]);

  useEffect(() => { const controller = new AbortController(); let timer: ReturnType<typeof setTimeout> | undefined; const refresh = async () => { const active = await load(controller.signal); timer = setTimeout(refresh, active ? 3000 : 12000); }; void refresh(); return () => { controller.abort(); if (timer) clearTimeout(timer); }; }, [load]);
  const repsByPage = useMemo(() => new Map<number, DerivedRepresentation[]>(representations.reduce<Map<number, DerivedRepresentation[]>>((map, representation) => { if (representation.page_number !== null) map.set(representation.page_number, [...(map.get(representation.page_number) ?? []), representation]); return map; }, new Map())), [representations]);
  async function doRetry() { if (!job) return; setRetrying(true); try { await retryJob(job.id, custodianId); await load(); } catch (reason: unknown) { setError(reason instanceof ApiError ? reason.message : "Retry could not be queued."); } finally { setRetrying(false); } }
  async function downloadCanonical() { setDownloading(true); try { const result = await fetchCanonical(sourceId, custodianId); const url = URL.createObjectURL(result.blob); const anchor = document.createElement("a"); anchor.href = url; anchor.download = detail?.source.display_name || "canonical.pdf"; anchor.click(); URL.revokeObjectURL(url); } catch (reason: unknown) { setError(reason instanceof ApiError ? reason.message : "Canonical download failed."); } finally { setDownloading(false); } }
  if (!detail) return <main className={styles.shell}><div className={styles.notice}>{error ?? "Loading source record…"}</div></main>;
  const arrivals = detail.arrivals ?? [];
  const enrollments = detail.enrollments ?? [];
  return <main className={styles.shell}><header className={styles.header}><div><div className={styles.eyebrow}>Source detail</div><h1 className={styles.title}>{detail.source.display_name}</h1><p className={styles.subtitle}>Canonical identity, provenance, enrollment and derived lineage remain separate records.</p></div><nav className={styles.nav}><Link href={`/?${query}`}>Back to register</Link><Link href={`/monitor?custodian_id=${custodianId}`}>Processing monitor</Link></nav></header>{error && <div className={styles.error} role="alert">{error}</div>}<div className={styles.split}><div><section className={styles.card}><div className={styles.cardHeader}><h2 className={styles.cardTitle}>Identity</h2><button className={styles.button} type="button" disabled={downloading} onClick={() => void downloadCanonical()}>{downloading ? "Downloading…" : "Download canonical PDF"}</button></div><dl className={styles.detailGrid}><dt>Source ID</dt><dd className={styles.mono}>{detail.source.id}</dd><dt>Canonical SHA-256</dt><dd className={styles.mono}>{detail.canonical_object.sha256}</dd><dt>Byte size</dt><dd>{formatSize(detail.canonical_object.byte_size)}</dd><dt>Media type</dt><dd>{detail.canonical_object.media_type}</dd><dt>Preservation state</dt><dd><span className={`${styles.status} ${styles.completed}`}>canonical preserved</span></dd></dl></section><section className={styles.card}><h2 className={styles.cardTitle}>Provenance and arrivals</h2>{arrivals.length === 0 ? <div className={styles.empty}>No arrival evidence is recorded.</div> : <ul className={styles.list}>{arrivals.map((arrival) => <li className={styles.listItem} key={arrival.id}><strong>{arrival.original_filename ?? detail.source.display_name}</strong><div className={styles.muted}>{arrival.arrival_channel} · received {formatDate(arrival.received_at)}</div><div>claimed origin: {arrival.claimed_origin || "—"} · obtained from: {arrival.obtained_from || "—"}</div><div className={styles.mono}>{arrival.id}</div></li>)}</ul>}</section><section className={styles.card}><h2 className={styles.cardTitle}>Corpus enrollment</h2>{enrollments.length === 0 ? <div className={styles.empty}>This source has no visible enrollment in the selected custodian boundary.</div> : <ul className={styles.list}>{enrollments.map((enrollment) => <li className={styles.listItem} key={enrollment.id}><strong>Corpus {enrollment.corpus_id}</strong><div className={styles.muted}>Enrollment {enrollment.id} · {formatDate(enrollment.enrolled_at)}</div></li>)}</ul>}</section></div><aside><section className={styles.card}><div className={styles.cardHeader}><h2 className={styles.cardTitle}>Processing</h2>{job && <StatusBadge state={job.state} />}</div>{job ? <><dl className={styles.detailGrid}><dt>Progress</dt><dd>{job.completed_pages} / {job.total_pages ?? "?"} pages</dd><dt>Attempts</dt><dd>{job.attempt_count} · retries {job.retry_count}</dd><dt>Lease</dt><dd className={styles.mono}>{job.lease_owner ?? "not leased"}</dd><dt>Heartbeat</dt><dd>{formatDate(job.heartbeat_at)}</dd><dt>Updated</dt><dd>{formatDate(job.updated_at)}</dd></dl>{job.last_error && <div className={styles.error}>{job.last_error}</div>}{(job.state === "failed" || job.state === "partial") && <button className={`${styles.buttonSecondary} ${styles.buttonDanger}`} disabled={retrying} onClick={() => void doRetry()}>{retrying ? "Retrying…" : "Retry processing"}</button>}</> : <div className={styles.notice}>No processing job is visible for this source.</div>}</section>{attempts.length > 0 && <section className={styles.card}><h2 className={styles.cardTitle}>Processing history</h2><ul className={styles.list}>{attempts.map((attempt) => <li className={styles.listItem} key={attempt.id}><strong>Attempt {attempt.attempt_number} · {attempt.outcome ?? "active"}</strong><div className={styles.muted}>{attempt.worker_id} · claimed {formatDate(attempt.claimed_at)}</div>{attempt.error && <div className={styles.error}>{attempt.error}</div>}</li>)}</ul></section>}</aside></div><section className={styles.card}><div className={styles.cardHeader}><h2 className={styles.cardTitle}>Derived representations</h2><span className={styles.muted}>{representations.length} immutable artifacts</span></div>{pages.length === 0 ? <div className={styles.empty}>Page checkpoints will appear when the worker discovers the document.</div> : <div className={styles.pageGrid}>{pages.map((checkpoint) => { const pageReps = repsByPage.get(checkpoint.page_number) ?? []; return <Link className={styles.pageTile} key={`${sourceId}:${checkpoint.page_number}`} href={`/sources/${sourceId}/pages/${checkpoint.page_number}?${query}`}><strong>Page {checkpoint.page_number}</strong><div><StatusBadge state={checkpoint.state === "completed" ? "completed" : checkpoint.state === "failed" ? "failed" : checkpoint.state === "processing" ? "processing" : "queued"} /></div><div className={styles.muted}>{pageReps.length} representations</div></Link>; })}</div>}</section></main>;
}
