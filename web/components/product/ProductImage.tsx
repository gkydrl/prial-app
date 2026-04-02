"use client";

import { useState } from "react";
import Image from "next/image";

interface ProductImageProps {
  src: string | null | undefined;
  alt: string;
  className?: string;
  width?: number;
  height?: number;
  fill?: boolean;
  sizes?: string;
  priority?: boolean;
}

function needsProxy(url: string): boolean {
  return (
    url.includes("cdn.dsmcdn.com") ||
    url.includes("trendyol.com") ||
    url.includes("hepsiburada.net") ||
    url.includes("hepsiburada.com") ||
    url.includes("mediamarkt")
  );
}

function resolveImageSrc(src: string): string {
  return needsProxy(src) ? `/api/img?url=${encodeURIComponent(src)}` : src;
}

export function ProductImage({
  src,
  alt,
  className = "",
  width,
  height,
  fill,
  sizes,
  priority = false,
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

  const imgSrc = resolveImageSrc(src);

  if (fill) {
    return (
      <Image
        src={imgSrc}
        alt={alt}
        fill
        className={className}
        sizes={sizes ?? "(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 20vw"}
        priority={priority}
        onError={() => setError(true)}
      />
    );
  }

  return (
    <Image
      src={imgSrc}
      alt={alt}
      className={className}
      width={width ?? 400}
      height={height ?? 400}
      sizes={sizes}
      priority={priority}
      onError={() => setError(true)}
    />
  );
}
