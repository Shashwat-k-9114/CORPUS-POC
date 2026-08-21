import type {
  AdmissionReceipt,
  Corpus,
  Custodian,
  DerivedRepresentation,
  DocumentExtractionResponse,
  Enrollment,
  PageCheckpoint,
  PaginatedJobs,
  PaginatedSources,
  ProcessingAttempt,
  ProcessingJob,
  ProcessingState,
  SourceArrival,
  SourceDetail,
  WorkerHeartbeat,
} from "./types";

export const API_BASE_URL =
  (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/$/, "");
export const REVIEW_TOKEN_STORAGE_KEY = "corpus.reviewToken";

export class ApiError extends Error {
  status: number;
  retryable: boolean;

  constructor(message: string, status: number, retryable = false) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.retryable = retryable;
  }
}

export function getReviewToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(REVIEW_TOKEN_STORAGE_KEY);
}

export function setReviewToken(token: string): void {
  window.sessionStorage.setItem(REVIEW_TOKEN_STORAGE_KEY, token);
}

export function forgetReviewToken(): void {
  window.sessionStorage.removeItem(REVIEW_TOKEN_STORAGE_KEY);
  window.dispatchEvent(new Event("corpus-review-token-changed"));
}

function requestUrl(path: string, params?: Record<string, string | number | undefined>): string {
  const query = new URLSearchParams();
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined) query.set(key, String(value));
  });
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return `${API_BASE_URL}${path}${suffix}`;
}

export function canonicalDownloadUrl(sourceId: string, custodianId: string) {
  return requestUrl(`/v1/sources/${sourceId}/canonical`, { custodian_id: custodianId });
}

export function representationDownloadUrl(representationId: string, custodianId: string) {
  return requestUrl(`/v1/representations/${representationId}/download`, { custodian_id: custodianId });
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  params?: Record<string, string | number | undefined>,
): Promise<T> {
  let response: Response;
  try {
    const token = getReviewToken();
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    if (token) headers.set("X-Corpus-Review-Token", token);
    response = await fetch(requestUrl(path, params), { ...init, headers });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError("The Corpus API is waking up or unavailable. Retry shortly.", 0, true);
  }
  const text = await response.text();
  if (!response.ok) {
    if (response.status === 401) {
      if (typeof window !== "undefined") window.dispatchEvent(new Event("corpus-review-token-invalid"));
      throw new ApiError("Review token rejected. Enter it again or forget the stored token.", response.status);
    }
    throw new ApiError(await readErrorDetail(text, response.status), response.status, response.status === 502 || response.status === 503 || response.status === 504);
  }
  if (!text) return undefined as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new ApiError("The Corpus API returned an unreadable response.", response.status);
  }
}

export function listCustodians(signal?: AbortSignal) {
  return apiRequest<unknown>("/v1/custodians", { signal }).then((value) => expectArray<Custodian>(value, "custodians"));
}

export function listCorpora(custodianId: string, signal?: AbortSignal) {
  return apiRequest<unknown>(`/v1/custodians/${custodianId}/corpora`, { signal }).then((value) => expectArray<Corpus>(value, "corpora"));
}

export function listSources(
  custodianId: string,
  corpusId: string,
  limit = 50,
  offset = 0,
  signal?: AbortSignal,
) {
  return apiRequest<unknown>("/v1/sources", { signal }, { custodian_id: custodianId, corpus_id: corpusId, limit, offset }).then((value) => expectPage<PaginatedSources>(value, "sources"));
}

export function getSource(sourceId: string, custodianId: string, signal?: AbortSignal) {
  return Promise.all([
    apiRequest<unknown>(`/v1/sources/${sourceId}`, { signal }, { custodian_id: custodianId }).then((value) => expectObject<Pick<SourceDetail, "source" | "canonical_object">>(value, "source detail")),
    getSourceArrivals(sourceId, custodianId, signal),
    getSourceEnrollments(sourceId, custodianId, signal),
  ]).then(([core, arrivals, enrollments]) => ({ ...core, arrivals, enrollments }));
}

export function getSourceArrivals(sourceId: string, custodianId: string, signal?: AbortSignal) {
  return apiRequest<unknown>(`/v1/sources/${sourceId}/arrivals`, { signal }, { custodian_id: custodianId }).then((value) => expectArray<SourceArrival>(value, "source arrivals"));
}

export function getSourceEnrollments(sourceId: string, custodianId: string, signal?: AbortSignal) {
  return apiRequest<unknown>(`/v1/sources/${sourceId}/enrollments`, { signal }, { custodian_id: custodianId }).then((value) => expectArray<Enrollment>(value, "source enrollments"));
}

export function listJobs(
  custodianId: string,
  state?: ProcessingState,
  limit = 100,
  offset = 0,
  signal?: AbortSignal,
) {
  return apiRequest<unknown>("/v1/processing-jobs", { signal }, { custodian_id: custodianId, state, limit, offset }).then((value) => expectPage<PaginatedJobs>(value, "processing jobs"));
}

export function getJob(jobId: string, custodianId: string, signal?: AbortSignal) {
  return apiRequest<ProcessingJob>(`/v1/processing-jobs/${jobId}`, { signal }, { custodian_id: custodianId });
}

export function listJobPages(jobId: string, custodianId: string, signal?: AbortSignal) {
  return apiRequest<PageCheckpoint[]>(`/v1/processing-jobs/${jobId}/pages`, { signal }, { custodian_id: custodianId });
}

export function listJobAttempts(jobId: string, custodianId: string, signal?: AbortSignal) {
  return apiRequest<ProcessingAttempt[]>(`/v1/processing-jobs/${jobId}/attempts`, { signal }, { custodian_id: custodianId });
}

export function retryJob(jobId: string, custodianId: string) {
  return apiRequest<ProcessingJob>(`/v1/processing-jobs/${jobId}/retry`, { method: "POST" }, { custodian_id: custodianId });
}

export function listWorkers(signal?: AbortSignal) {
  return apiRequest<unknown>("/v1/workers", { signal }).then((value) => expectArray<WorkerHeartbeat>(value, "worker heartbeats"));
}

export function listRepresentations(sourceId: string, custodianId: string, signal?: AbortSignal) {
  return apiRequest<unknown>(`/v1/sources/${sourceId}/representations`, { signal }, { custodian_id: custodianId }).then((value) => expectArray<DerivedRepresentation>(value, "derived representations"));
}

export function getRepresentation(representationId: string, custodianId: string, signal?: AbortSignal) {
  return apiRequest<DerivedRepresentation>(`/v1/representations/${representationId}`, { signal }, { custodian_id: custodianId });
}

export async function fetchRepresentationArtifact(representationId: string, custodianId: string, signal?: AbortSignal) {
  const response = await fetchAuthorized(`/v1/representations/${representationId}/download`, { custodian_id: custodianId }, { signal });
  if (!response.ok) throw new ApiError(await readErrorDetail(await response.text(), response.status), response.status);
  const blob = await response.blob();
  return { blobUrl: URL.createObjectURL(blob), contentSha256: response.headers.get("X-Content-SHA256") ?? "" };
}

export async function fetchCanonical(sourceId: string, custodianId: string, signal?: AbortSignal) {
  const response = await fetchAuthorized(`/v1/sources/${sourceId}/canonical`, { custodian_id: custodianId }, { signal });
  if (!response.ok) throw new ApiError(await readErrorDetail(await response.text(), response.status), response.status);
  return { blob: await response.blob(), contentSha256: response.headers.get("X-Content-SHA256") ?? "" };
}

export interface AdmissionUploadOptions {
  custodianId: string;
  corpusId: string;
  arrivalChannel: string;
  claimedOrigin?: string;
  obtainedFrom?: string;
  idempotencyKey?: string;
  onProgress?: (percent: number) => void;
  signal?: AbortSignal;
}

export function admitSource(file: File, options: AdmissionUploadOptions): Promise<AdmissionReceipt> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);
    formData.append("custodian_id", options.custodianId);
    formData.append("corpus_id", options.corpusId);
    formData.append("arrival_channel", options.arrivalChannel);
    if (options.claimedOrigin) formData.append("claimed_origin", options.claimedOrigin);
    if (options.obtainedFrom) formData.append("obtained_from", options.obtainedFrom);
    options.signal?.addEventListener("abort", () => xhr.abort(), { once: true });
    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) options.onProgress?.(Math.round((event.loaded / event.total) * 100));
    });
    xhr.addEventListener("load", async () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as AdmissionReceipt);
        } catch {
          reject(new ApiError("The admission receipt was unreadable.", xhr.status));
        }
      } else {
        reject(new ApiError(await readErrorDetail(xhr.responseText, xhr.status), xhr.status));
      }
    });
    xhr.addEventListener("error", () => reject(new ApiError("Network error while admitting the PDF.", 0)));
    xhr.addEventListener("abort", () => reject(new DOMException("Upload cancelled", "AbortError")));
    xhr.open("POST", requestUrl("/v1/admissions"));
    const token = getReviewToken();
    if (token) xhr.setRequestHeader("X-Corpus-Review-Token", token);
    if (options.idempotencyKey) xhr.setRequestHeader("Idempotency-Key", options.idempotencyKey);
    xhr.send(formData);
  });
}

async function readErrorDetail(responseText: string, status: number): Promise<string> {
  try {
    const body = JSON.parse(responseText);
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    // response wasn't JSON -- fall through to the generic message
  }
  return `Request failed with status ${status}.`;
}

async function fetchAuthorized(path: string, params: Record<string, string>, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const token = getReviewToken();
  if (token) headers.set("X-Corpus-Review-Token", token);
  try {
    return await fetch(requestUrl(path, params), { ...init, headers });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError("The Corpus API is waking up or unavailable. Retry shortly.", 0, true);
  }
}

function expectArray<T>(value: unknown, label: string): T[] {
  if (!Array.isArray(value)) throw new ApiError(`The Corpus API returned malformed ${label}.`, 502);
  return value as T[];
}

function expectObject<T>(value: unknown, label: string): T {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new ApiError(`The Corpus API returned malformed ${label}.`, 502);
  return value as T;
}

function expectPage<T extends { items: unknown[] }>(value: unknown, label: string): T {
  const page = expectObject<T>(value, label);
  if (!Array.isArray(page.items)) throw new ApiError(`The Corpus API returned malformed ${label} items.`, 502);
  return page;
}

export type ExtractPhase = "uploading" | "extracting";

/**
 * Uploads a PDF to POST /extract. Uses XMLHttpRequest (not fetch) so real
 * upload-progress events are available: onPhaseChange fires "uploading" while
 * bytes are still being sent, then "extracting" once the upload completes and
 * the server is processing the PDF (which can take over a minute for large,
 * complex documents -- see backend/README.md).
 */
export function extractDocument(
  file: File,
  onPhaseChange: (phase: ExtractPhase) => void,
): Promise<DocumentExtractionResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);

    xhr.upload.addEventListener("progress", () => onPhaseChange("uploading"));
    xhr.upload.addEventListener("load", () => onPhaseChange("extracting"));

    xhr.addEventListener("load", async () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          reject(new ApiError("Server returned an unreadable response.", xhr.status));
        }
      } else {
        reject(new ApiError(await readErrorDetail(xhr.responseText, xhr.status), xhr.status));
      }
    });

    xhr.addEventListener("error", () => {
      reject(new ApiError("Network error while uploading. Is the backend running?", 0));
    });

    xhr.open("POST", `${API_BASE_URL}/extract`);
    const token = getReviewToken();
    if (token) xhr.setRequestHeader("X-Corpus-Review-Token", token);
    xhr.send(formData);
  });
}

export interface PageImageResult {
  blobUrl: string;
  pageWidthPt: number;
  pageHeightPt: number;
  imageWidthPx: number;
  imageHeightPx: number;
  resolutionDpi: number;
}

/**
 * Fetches GET /documents/{documentId}/pages/{pageNumber}/image. Uses fetch (not
 * <img src=...> directly) because the coordinate-mapping headers
 * (X-Page-Width-Points etc.) must be read in JS -- a plain <img> tag never
 * exposes response headers to the page.
 */
export async function fetchPageImage(
  documentId: string,
  pageNumber: number,
): Promise<PageImageResult> {
  const response = await fetchAuthorized(`/documents/${documentId}/pages/${pageNumber}/image`, {});

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(await readErrorDetail(text, response.status), response.status);
  }

  const pageWidthPt = parseFloat(response.headers.get("X-Page-Width-Points") ?? "0");
  const pageHeightPt = parseFloat(response.headers.get("X-Page-Height-Points") ?? "0");
  const imageWidthPx = parseInt(response.headers.get("X-Image-Width-Px") ?? "0", 10);
  const imageHeightPx = parseInt(response.headers.get("X-Image-Height-Px") ?? "0", 10);
  const resolutionDpi = parseFloat(response.headers.get("X-Resolution-Dpi") ?? "0");

  const blob = await response.blob();
  const blobUrl = URL.createObjectURL(blob);

  return { blobUrl, pageWidthPt, pageHeightPt, imageWidthPx, imageHeightPx, resolutionDpi };
}
