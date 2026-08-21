"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, getSourceArrivals, listJobs, listSources } from "@/lib/api";
import { useCorpusContext } from "@/lib/useCorpusContext";
import type { ProcessingJob, ProcessingState, SourceListItem } from "@/lib/types";
import ContextBar from "./ContextBar";
import StatusBadge from "./StatusBadge";
import styles from "./Corpus.module.css";

const PAGE_SIZE = 20;
const STATES: ProcessingState[] = ["queued", "processing", "completed", "partial", "failed"];

function shortId(value: string) { return `${value.slice(0, 8)}…${value.slice(-4)}`; }
function formatSize(bytes: number) { return `${(bytes / 1024 / 1024).toFixed(2)} MB`; }
function formatDate(value: string) { return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)); }

export default function RegisterView() {
  const context = useCorpusContext();
  const [sources, setSources] = useState<SourceListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [jobs, setJobs] = useState<ProcessingJob[]>([]);
  const [arrivals, setArrivals] = useState<Record<string, number>>({});
  const [page, setPage] = useState(0);
  const [stateFilter, setStateFilter] = useState<ProcessingState | "">("");
  const [nameFilter, setNameFilter] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    if (!context.custodianId || !context.corpusId) return false;
    try {
      const [sourcePage, jobPage] = await Promise.all([
        listSources(context.custodianId, context.corpusId, PAGE_SIZE, page * PAGE_SIZE, signal),
        listJobs(context.custodianId, undefined, 100, 0, signal),
      ]);
      setSources(sourcePage.items);
      setTotal(sourcePage.total);
      setJobs(jobPage.items);
      setError(null);
      const counts = await Promise.all(sourcePage.items.map(async (item) => [item.source.id, (await getSourceArrivals(item.source.id, context.custodianId, signal)).length] as const));
      setArrivals(Object.fromEntries(counts));
      return jobPage.items.some((job) => job.state === "queued" || job.state === "processing");
    } catch (reason: unknown) {
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      setError(reason instanceof ApiError ? reason.message : "Unable to refresh the register.");
      return false;
    }
  }, [context.corpusId, context.custodianId, page]);

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    const refresh = async () => {
      const active = await load(controller.signal);
      timer = setTimeout(refresh, active ? 3000 : 12000);
    };
    void refresh();
    return () => { controller.abort(); if (timer) clearTimeout(timer); };
  }, [load]);

  const jobBySource = useMemo(() => new Map(jobs.map((job) => [job.source_id, job])), [jobs]);
  const filteredSources = sources.filter((item) => item.source.display_name.toLowerCase().includes(nameFilter.toLowerCase())).filter((item) => {
    const job = jobBySource.get(item.source.id);
    return !stateFilter || job?.state === stateFilter;
  });
  const counts = STATES.reduce<Record<string, number>>((result, state) => { result[state] = jobs.filter((job) => job.state === state).length; return result; }, {});
  const query = `custodian_id=${context.custodianId}&corpus_id=${context.corpusId}`;

  return <main className={styles.shell}>
    <header className={styles.header}>
      <div><div className={styles.eyebrow}>Corpus register</div><h1 className={styles.title}>Durable evidence register</h1><p className={styles.subtitle}>Canonical sources stay preserved while page processing advances independently. Every status below is read from PostgreSQL-backed APIs.</p></div>
      <nav className={styles.nav} aria-label="Primary"><Link href={`/?${query}`}>Register</Link><Link href={`/admit?${query}`}>Admit sources</Link><Link href={`/monitor?custodian_id=${context.custodianId}`}>Processing monitor</Link></nav>
    </header>
    <ContextBar {...context} onCustodianChange={context.setCustodianId} onCorpusChange={context.setCorpusId} />
    {context.error && <div className={styles.error} role="alert">{context.error}</div>}
    {error && <div className={styles.error} role="alert">{error} <button className={styles.buttonSecondary} type="button" onClick={() => void load()}>Retry</button></div>}
    {!context.loading && context.custodianId && context.corpusId && <>
      <div className={styles.grid}>
        <div className={styles.metric}><span className={styles.metricValue}>{total}</span><span className={styles.metricLabel}>Enrolled sources</span></div>
        {STATES.map((state) => <div className={styles.metric} key={state}><span className={styles.metricValue}>{counts[state] ?? 0}</span><span className={styles.metricLabel}>{state}</span></div>)}
      </div>
      <section className={styles.card}>
        <div className={styles.toolbar}><div><h2 className={styles.cardTitle}>Source register</h2><span className={styles.muted}>Page {page + 1} · {total} total</span></div><div className={styles.toolbarGroup}><input className={styles.input} placeholder="Filter source name" value={nameFilter} onChange={(event) => setNameFilter(event.target.value)} aria-label="Filter source name" /><select className={styles.select} value={stateFilter} onChange={(event) => { setStateFilter(event.target.value as ProcessingState | ""); setPage(0); }} aria-label="Filter processing state"><option value="">All states</option>{STATES.map((state) => <option key={state} value={state}>{state}</option>)}</select></div></div>
        {filteredSources.length === 0 ? <div className={styles.empty}>{total === 0 ? "No sources are enrolled in this corpus yet." : "No sources match the current filters."}</div> : <div className={styles.tableWrap}><table className={styles.table}><thead><tr><th>Source</th><th>Canonical</th><th>Admission</th><th>Arrivals</th><th>Processing</th><th>Activity</th><th /></tr></thead><tbody>{filteredSources.map((item) => { const job = jobBySource.get(item.source.id); return <tr key={item.source.id}><td><Link href={`/sources/${item.source.id}?custodian_id=${context.custodianId}&corpus_id=${context.corpusId}`}>{item.source.display_name}</Link><div className={`${styles.muted} ${styles.mono}`}>{shortId(item.source.id)}</div></td><td>{formatSize(item.canonical_object.byte_size)}<div className={`${styles.muted} ${styles.mono}`}>{shortId(item.canonical_object.sha256)}</div></td><td>{formatDate(item.source.created_at)}</td><td>{arrivals[item.source.id] ?? "—"}</td><td>{job ? <><StatusBadge state={job.state} /><div className={styles.muted}>{job.completed_pages} / {job.total_pages ?? "?"} pages</div></> : <span className={styles.muted}>No job</span>}</td><td className={styles.muted}>{job ? formatDate(job.updated_at) : "—"}</td><td><Link href={`/sources/${item.source.id}?custodian_id=${context.custodianId}&corpus_id=${context.corpusId}`}>Inspect</Link></td></tr>; })}</tbody></table></div>}
        <div className={styles.pagination}><button className={styles.buttonSecondary} disabled={page === 0} onClick={() => setPage((current) => current - 1)}>Previous</button><span className={styles.muted}>{page + 1} / {Math.max(1, Math.ceil(total / PAGE_SIZE))}</span><button className={styles.buttonSecondary} disabled={(page + 1) * PAGE_SIZE >= total} onClick={() => setPage((current) => current + 1)}>Next</button></div>
      </section>
    </>}
    {(context.loading || !context.custodianId) && <div className={styles.notice}>Loading persistent custodian context…</div>}
  </main>;
}
