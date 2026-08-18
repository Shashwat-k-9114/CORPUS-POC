"use client";

import { useEffect, useRef, useState } from "react";
import { ApiError, fetchPageImage, type PageImageResult } from "@/lib/api";
import { regionToPixelRect } from "@/lib/coords";
import type { Region } from "@/lib/types";
import styles from "./PageViewer.module.css";

type ImageState = "loading" | "success" | "error";

interface PageViewerProps {
  documentId: string;
  pageNumber: number;
  regions: Region[];
  selectedRegion: Region | null;
  onRegionSelect: (region: Region) => void;
}

// The caller must remount this component (e.g. key={`${documentId}-${pageNumber}`})
// whenever documentId/pageNumber changes, so state resets via a fresh mount instead
// of a synchronous setState at the top of the effect below.
export default function PageViewer({
  documentId,
  pageNumber,
  regions,
  selectedRegion,
  onRegionSelect,
}: PageViewerProps) {
  const [state, setState] = useState<ImageState>("loading");
  const [image, setImage] = useState<PageImageResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const blobUrlRef = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    fetchPageImage(documentId, pageNumber)
      .then((result) => {
        if (cancelled) {
          URL.revokeObjectURL(result.blobUrl);
          return;
        }
        if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = result.blobUrl;
        setImage(result);
        setState("success");
      })
      .catch((err) => {
        if (cancelled) return;
        const message = err instanceof ApiError ? err.message : "Unable to load this page.";
        setErrorMessage(message);
        setState("error");
      });

    return () => {
      cancelled = true;
    };
  }, [documentId, pageNumber]);

  useEffect(() => {
    return () => {
      if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
    };
  }, []);

  if (state === "loading") {
    return (
      <div className={styles.container}>
        <div className={styles.centerMessage}>
          <span className={styles.spinner} aria-hidden />
          <span>Loading page {pageNumber}…</span>
        </div>
      </div>
    );
  }

  if (state === "error" || !image) {
    return (
      <div className={styles.container}>
        <div className={styles.centerMessage}>
          <span className={styles.errorMessage} role="alert">
            {errorMessage ?? "Unable to load this page."}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.imageWrap}>
        {/* eslint-disable-next-line @next/next/no-img-element -- source is a
            same-session blob: URL from an authenticated-by-origin fetch, not a
            static/remote asset next/image is built to optimize */}
        <img
          className={styles.pageImage}
          src={image.blobUrl}
          alt={`Page ${pageNumber} of the uploaded document`}
        />
        <svg
          className={styles.overlay}
          viewBox={`0 0 ${image.imageWidthPx} ${image.imageHeightPx}`}
          preserveAspectRatio="none"
        >
          {regions.map((region) => {
            const rect = regionToPixelRect(region, image.resolutionDpi);
            const isSelected = selectedRegion?.order_index === region.order_index;
            return (
              <rect
                key={region.order_index}
                x={rect.x}
                y={rect.y}
                width={rect.width}
                height={rect.height}
                className={isSelected ? styles.regionSelected : styles.region}
                onClick={() => onRegionSelect(region)}
              >
                <title>{region.text}</title>
              </rect>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
