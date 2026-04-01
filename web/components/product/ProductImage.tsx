"use client";

import { useState } from "react";

interface ProductImageProps {
  src: string | null | undefined;
  alt: string;
  className?: string;
  width?: number;
  height?: number;
}

export function ProductImage({
  src,
  alt,
  className = "",
  width,
  height,
}: ProductImageProps) {
  const [error, setError] = useState(false);

  if (!src || error) {
    return (
      <div
        className={`flex items-center justify-center bg-gray-100 text-gray-300 ${className}`}
        style={{ width, height }}
      >
        <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1}
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
      </div>
    );
  }

  // Use our image proxy for CDN images that need Referer headers
  const needsProxy =
    src.includes("cdn.dsmcdn.com") ||
    src.includes("trendyol.com") ||
    src.includes("hepsiburada.net") ||
    src.includes("hepsiburada.com") ||
    src.includes("mediamarkt");

  const imgSrc = needsProxy
    ? `/api/img?url=${encodeURIComponent(src)}`
    : src;

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={imgSrc}
      alt={alt}
      className={className}
      width={width}
      height={height}
      loading="lazy"
      onError={() => setError(true)}
    />
  );
}
