"use client";

import { useParams, useSearchParams } from "next/navigation";
import SourceDetailView from "@/components/corpus/SourceDetailView";

export default function SourcePage() {
  const params = useParams<{ sourceId: string }>();
  const search = useSearchParams();
  return <SourceDetailView sourceId={params.sourceId} custodianId={search.get("custodian_id") ?? ""} corpusId={search.get("corpus_id") ?? ""} />;
}
