"use client";
/* The durable render is a blob URL returned by the API; next/image cannot optimize it. */
/* eslint-disable @next/next/no-img-element */

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ApiError, fetchRepresentationArtifact, getSource, listRepresentations } from "@/lib/api";
import type { DerivedRepresentation, PageExtraction, Region, SourceDetail } from "@/lib/types";
import styles from "./Corpus.module.css";

interface Props { sourceId: string; custodianId: string; corpusId: string; pageNumber: number; }
function Lineage({ source, json, region }: { source: SourceDetail; json: DerivedRepresentation | null; region: Region | null }) {
  if (!region || !json) return <div className={styles.empty}>Select a word region to inspect its durable lineage.</div>;
  return <div><div className={styles.notice}>“{region.text}” · page {region.page_number}</div><dl className={styles.detailGrid}><dt>Source ID</dt><dd className={styles.mono}>{source.source.id}</dd><dt>Canonical SHA-256</dt><dd className={styles.mono}>{source.canonical_object.sha256}</dd><dt>Page number</dt><dd>{region.page_number}</dd><dt>Processing job</dt><dd className={styles.mono}>{json.job_id}</dd><dt>Representation ID</dt><dd className={styles.mono}>{json.id}</dd><dt>Processor</dt><dd>{json.extractor_name} {json.extractor_version}</dd><dt>Schema version</dt><dd>{json.schema_version}</dd><dt>Representation SHA-256</dt><dd className={styles.mono}>{json.content_sha256}</dd><dt>Bounding box</dt><dd className={styles.mono}>{JSON.stringify(region.bbox)}</dd></dl></div>;
}

export default function DerivedInspectorView({ sourceId, custodianId, corpusId, pageNumber }: Props) {
  const [source, setSource] = useState<SourceDetail | null>(null);
  const [jsonRepresentation, setJsonRepresentation] = useState<DerivedRepresentation | null>(null);
  const [renderRepresentation, setRenderRepresentation] = useState<DerivedRepresentation | null>(null);
  const [page, setPage] = useState<PageExtraction | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [selected, setSelected] = useState<Region | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController(); let currentUrl: string | null = null;
    async function load() {
      try {
        const [sourceDetail, representations] = await Promise.all([getSource(sourceId, custodianId, controller.signal), listRepresentations(sourceId, custodianId, controller.signal)]);
        const json = representations.find((item) => item.page_number === pageNumber && item.representation_kind === "page-json") ?? null;
        const render = representations.find((item) => item.page_number === pageNumber && item.representation_kind === "page-render") ?? null;
        setSource(sourceDetail); setJsonRepresentation(json); setRenderRepresentation(render); setSelected(null);
        if (!json || !render) return;
        const [jsonArtifact, renderArtifact] = await Promise.all([fetchRepresentationArtifact(json.id, custodianId, controller.signal), fetchRepresentationArtifact(render.id, custodianId, controller.signal)]);
        currentUrl = renderArtifact.blobUrl;
        const parsed = JSON.parse(await (await fetch(jsonArtifact.blobUrl, { signal: controller.signal })).text()) as PageExtraction;
        URL.revokeObjectURL(jsonArtifact.blobUrl);
        setPage(parsed); setImageUrl(renderArtifact.blobUrl); setError(null);
      } catch (reason: unknown) {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError(reason instanceof ApiError ? reason.message : "Unable to load this derived page.");
      }
    }
    void load(); return () => { controller.abort(); if (currentUrl) URL.revokeObjectURL(currentUrl); };
  }, [custodianId, pageNumber, sourceId]);
  const query = `custodian_id=${custodianId}&corpus_id=${corpusId}`;
  const regions = useMemo(() => page?.regions ?? [], [page]);
  if (error) return <main className={styles.shell}><div className={styles.error} role="alert">{error}</div><Link href={`/sources/${sourceId}?${query}`}>Back to source</Link></main>;
  if (source && !jsonRepresentation && !renderRepresentation) return <main className={styles.shell}><div className={styles.notice}>Page {pageNumber} has no durable derived representations yet. The source is preserved and may still be queued, processing, partial, or failed.</div><Link href={`/sources/${sourceId}?${query}`}>Back to source</Link></main>;
  if (!source || !page || !imageUrl) return <main className={styles.shell}><div className={styles.notice}>Loading one durable page…</div></main>;
  return <main className={styles.shell}><header className={styles.header}><div><div className={styles.eyebrow}>Derived output inspector</div><h1 className={styles.title}>{source.source.display_name} · page {pageNumber}</h1><p className={styles.subtitle}>This view fetches one page JSON artifact and one page render artifact. It never calls the legacy extraction endpoint.</p></div><nav className={styles.nav}><Link href={`/sources/${sourceId}?${query}`}>Back to source</Link><Link href={`/?${query}`}>Register</Link></nav></header><div className={styles.toolbar}><div className={styles.toolbarGroup}><Link className={styles.buttonSecondary} href={`/sources/${sourceId}/pages/${Math.max(1, pageNumber - 1)}?${query}`}>Previous page</Link><span className={styles.muted}>Page {pageNumber}</span><Link className={styles.buttonSecondary} href={`/sources/${sourceId}/pages/${pageNumber + 1}?${query}`}>Next page</Link></div><span className={styles.muted}>Coordinate contract: PDF points, top-left origin</span></div><div className={styles.inspector}><section className={styles.card}><div className={styles.inspectorImage}><img src={imageUrl} alt={`Derived render of page ${pageNumber}`} /><svg viewBox={`0 0 ${page.width} ${page.height}`} preserveAspectRatio="none" aria-label="Word region overlay">{regions.map((region) => <rect key={`${region.order_index}-${region.text}`} className={selected?.order_index === region.order_index ? "selected" : ""} x={region.bbox.x0} y={region.bbox.top} width={region.bbox.x1 - region.bbox.x0} height={region.bbox.bottom - region.bbox.top} onClick={() => setSelected(region)}><title>{region.text}</title></rect>)}</svg></div></section><aside className={styles.card}><h2 className={styles.cardTitle}>Region lineage</h2><Lineage source={source} json={jsonRepresentation} region={selected} /><div className={styles.cardHeader} style={{ marginTop: "1rem" }}><span className={styles.muted}>Render artifact</span><span className={styles.mono}>{renderRepresentation?.content_sha256}</span></div></aside></div></main>;
}
