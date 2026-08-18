import type { DocumentExtractionResponse } from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
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
  const response = await fetch(`${API_BASE_URL}/documents/${documentId}/pages/${pageNumber}/image`);

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
