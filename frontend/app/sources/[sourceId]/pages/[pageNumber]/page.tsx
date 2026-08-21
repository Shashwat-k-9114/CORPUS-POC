"use client";

import { useParams, useSearchParams } from "next/navigation";
import DerivedInspectorView from "@/components/corpus/DerivedInspectorView";

export default function DerivedPage() {
  const params = useParams<{ sourceId: string; pageNumber: string }>();
  const search = useSearchParams();
  return <DerivedInspectorView sourceId={params.sourceId} pageNumber={Number(params.pageNumber)} custodianId={search.get("custodian_id") ?? ""} corpusId={search.get("corpus_id") ?? ""} />;
}
