// Mirrors backend/app/models.py exactly. Keep in sync by hand -- there is no
// schema-generation step in this prototype (see DECISIONS.md if that changes).

export interface BoundingBox {
  x0: number;
  x1: number;
  top: number;
  bottom: number;
}

export interface Region {
  text: string;
  bbox: BoundingBox;
  page_number: number;
  order_index: number;
  extraction_method: string;
  confidence: number | null;
}

export interface PageExtraction {
  page_number: number;
  width: number;
  height: number;
  word_count: number;
  regions: Region[];
}

export interface DocumentExtractionResponse {
  document_id: string;
  filename: string;
  page_count: number;
  extraction_method: string;
  extraction_engine_version: string;
  pages: PageExtraction[];
}

export type ProcessingState = "queued" | "processing" | "completed" | "partial" | "failed";

export interface Custodian {
  id: string;
  slug: string;
  name: string;
  created_at: string;
}

export interface Corpus {
  id: string;
  custodian_id: string;
  name: string;
  kind: string;
  created_at: string;
}

export interface CanonicalObject {
  id: string;
  custodian_id: string;
  sha256: string;
  byte_size: number;
  media_type: string;
  storage_key: string;
  created_at: string;
}

export interface Source {
  id: string;
  custodian_id: string;
  canonical_object_id: string;
  display_name: string;
  created_at: string;
}

export interface SourceListItem {
  source: Source;
  canonical_object: CanonicalObject;
}

export interface SourceArrival {
  id: string;
  source_id: string;
  claimed_origin: string;
  obtained_from: string;
  arrival_channel: string;
  original_filename: string | null;
  received_at: string;
}

export interface Enrollment {
  id: string;
  corpus_id: string;
  source_id: string;
  enrolled_at: string;
}

export interface ProcessingJob {
  id: string;
  source_id: string;
  pipeline_name: string;
  pipeline_version: string;
  state: ProcessingState;
  priority: number;
  total_pages: number | null;
  completed_pages: number;
  failed_pages: number;
  retry_count: number;
  attempt_count: number;
  next_attempt_at: string | null;
  lease_owner: string | null;
  lease_acquired_at: string | null;
  lease_expires_at: string | null;
  heartbeat_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface PageCheckpoint {
  id: string;
  job_id: string;
  page_number: number;
  state: "pending" | "queued" | "processing" | "completed" | "failed";
  attempt_count: number;
  representation_id: string | null;
  json_representation_id: string | null;
  render_representation_id: string | null;
  last_error: string | null;
  next_attempt_at: string | null;
  updated_at: string;
}

export interface ProcessingAttempt {
  id: string;
  job_id: string;
  attempt_number: number;
  worker_id: string;
  claimed_at: string;
  heartbeat_at: string;
  ended_at: string | null;
  outcome: string | null;
  error: string | null;
}

export interface WorkerHeartbeat {
  worker_id: string;
  started_at: string;
  last_seen_at: string;
  status: string;
  active_job_id: string | null;
  updated_at: string;
}

export interface DerivedRepresentation {
  id: string;
  source_id: string;
  custodian_id: string;
  canonical_object_id: string;
  canonical_sha256: string;
  job_id: string;
  representation_kind: "page-json" | "page-render" | string;
  schema_version: string;
  storage_key: string;
  content_sha256: string;
  byte_size: number;
  page_number: number | null;
  extractor_name: string;
  extractor_version: string;
  settings: Record<string, unknown>;
  settings_digest: string;
  created_at: string;
}

export interface AdmissionReceipt {
  source: Source;
  canonical_object: CanonicalObject;
  arrival: SourceArrival;
  enrollment: Enrollment;
  processing_job: ProcessingJob;
  exact_duplicate: boolean;
  idempotent_replay: boolean;
}

export interface SourceDetail {
  source: Source;
  canonical_object: CanonicalObject;
  arrivals: SourceArrival[];
  enrollments: Enrollment[];
}

export interface PaginatedSources {
  items: SourceListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface PaginatedJobs {
  items: ProcessingJob[];
  total: number;
  limit: number;
  offset: number;
}
