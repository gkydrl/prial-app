"use client";

import Link from "next/link";
import type { ProductResponse } from "@/lib/api";
import { formatPrice, formatDiscount } from "@/lib/formatPrice";
import { productSlug } from "@/lib/slugify";
import { storeLabel } from "@/lib/stores";
import { ProductImage } from "./ProductImage";
import { SignalBadge } from "@/components/ui/SignalBadge";

export function ProductCard({ product, categorySlug }: { product: ProductResponse; categorySlug?: string }) {
  const catSlug = categorySlug ?? product.category_slug ?? "urun";
  const slug = productSlug(product.title, product.id);
  const href = `/${catSlug}/${slug}`;

  const activeStores = product.stores.filter(
    (s) => s.current_price != null && s.in_stock
  );
  const bestStore = activeStores.length
    ? activeStores.reduce((a, b) =>
        (a.current_price ?? Infinity) < (b.current_price ?? Infinity) ? a : b
      )
    : null;

  const bestPrice = bestStore?.current_price ?? null;
  const discount = bestStore?.discount_percent;

  return (
    <div className="group relative flex flex-col bg-white border border-gray-200 rounded-xl overflow-hidden hover:shadow-lg hover:border-brand/30 transition-all">
      {/* Quick add alarm button */}
      <button
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          // TODO: alarm oluşturma modal'ı veya /giris yönlendirmesi
          window.location.href = href;
        }}
        className="absolute top-2 right-2 z-10 w-8 h-8 rounded-full bg-white/90 border border-gray-200 flex items-center justify-center text-gray-400 hover:text-brand hover:border-brand hover:bg-brand/5 transition-all opacity-0 group-hover:opacity-100"
        title="Kampanya talebi oluştur"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
      </button>

      <Link href={href} className="flex flex-col flex-1">
        {/* Image */}
        <div className="relative aspect-square bg-white p-4 flex items-center justify-center">
          <ProductImage
            src={product.image_url}
            alt={`${product.brand ? product.brand + " " : ""}${product.title} - fiyat karşılaştırma`}
            className="max-w-full max-h-full object-contain group-hover:scale-105 transition-transform"
          />
          {discount && discount > 0 && (
            <span className="absolute top-2 left-2 bg-danger text-white text-xs font-bold px-2 py-1 rounded-md">
              {formatDiscount(discount)}
            </span>
          )}
        </div>

        {/* Info */}
        <div className="p-3 flex flex-col justify-end flex-1">
          <h3 className="text-sm font-medium text-gray-900 line-clamp-2">
            {product.short_title || product.title}
          </h3>

          {product.brand && (
            <p className="text-xs text-gray-500 mt-1">{product.brand}</p>
          )}

          {product.reasoning_text && (
            <p className="text-xs text-gray-400 mt-1.5 line-clamp-1 italic">
              {product.reasoning_text.split(".")[0]}.
            </p>
          )}

          <div className="mt-2">
            <p className="text-lg font-bold text-gray-900">
              {formatPrice(bestPrice)}
            </p>
            {bestStore?.original_price &&
              bestStore.original_price > (bestPrice ?? 0) && (
                <p className="text-xs text-gray-400 line-through">
                  {formatPrice(bestStore.original_price)}
                </p>
              )}
          </div>

          {/* Bottom row */}
          <div className="mt-2 flex items-center justify-between">
            {activeStores.length > 1 ? (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-brand bg-brand/5 px-2 py-0.5 rounded-full">
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 100 4 2 2 0 000-4z" />
                </svg>
                {activeStores.length} mağaza
              </span>
            ) : bestStore ? (
              <span className="text-xs text-gray-500">
                {storeLabel(bestStore.store)}
              </span>
            ) : <span />}

            {product.recommendation && (
              <SignalBadge recommendation={product.recommendation} size="sm" />
            )}
          </div>
        </div>
      </Link>
    </div>
  );
}
