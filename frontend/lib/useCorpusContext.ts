"use client";

import { useEffect, useState } from "react";
import { listCorpora, listCustodians } from "./api";
import type { Corpus, Custodian } from "./types";

export function useCorpusContext() {
  const [custodians, setCustodians] = useState<Custodian[]>([]);
  const [corpora, setCorpora] = useState<Corpus[]>([]);
  const [custodianId, setCustodianId] = useState("");
  const [corpusId, setCorpusId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [requested] = useState<{ custodianId?: string; corpusId?: string }>(() => {
    if (typeof window === "undefined") return {};
    const params = new URLSearchParams(window.location.search);
    return { custodianId: params.get("custodian_id") ?? undefined, corpusId: params.get("corpus_id") ?? undefined };
  });

  useEffect(() => {
    const controller = new AbortController();
    listCustodians(controller.signal)
      .then((items) => {
        setCustodians(items);
        const first = items.find((item) => item.slug === "demo") ?? items.find((item) => item.slug === "default") ?? items[0];
        const requestedCustodian = requested.custodianId && items.some((item) => item.id === requested.custodianId) ? requested.custodianId : undefined;
        if (first) setCustodianId((current) => current || requestedCustodian || first.id);
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError(reason instanceof Error ? reason.message : "Unable to load custodians.");
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [requested.custodianId]);

  useEffect(() => {
    if (!custodianId) return;
    const controller = new AbortController();
    listCorpora(custodianId, controller.signal)
      .then((items) => {
        setCorpora(items);
        const requestedCorpus = requested.corpusId && items.some((item) => item.id === requested.corpusId) ? requested.corpusId : undefined;
        setCorpusId((current) => items.some((item) => item.id === current) ? current : (requestedCorpus ?? items[0]?.id ?? ""));
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError(reason instanceof Error ? reason.message : "Unable to load corpora.");
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [custodianId, requested.corpusId]);

  return {
    custodians,
    corpora,
    custodianId,
    corpusId,
    setCustodianId: (value: string) => {
      setCustodianId(value);
      setCorpusId("");
      setLoading(true);
    },
    setCorpusId,
    loading,
    error,
  };
}
