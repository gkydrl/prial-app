"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { isLoggedIn, getAccessToken } from "@/lib/auth";
import { formatPrice } from "@/lib/formatPrice";
import { productSlug } from "@/lib/slugify";
import { storeLabel } from "@/lib/stores";
import { ProductImage } from "@/components/product/ProductImage";
import { ProductCard } from "@/components/product/ProductCard";
import type { ProductResponse } from "@/lib/api";
import { filterDisplayable } from "@/lib/api";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "https://prial-app-production.up.railway.app/api/v1";

interface AlarmResponse {
  id: string;
  target_price: number;
  status: "ACTIVE" | "TRIGGERED" | "PAUSED" | "DELETED";
  triggered_price: number | null;
  triggered_at: string | null;
  created_at: string;
  product: ProductResponse;
}

export default function KampanyalarPage() {
  const router = useRouter();
  const [alarms, setAlarms] = useState<AlarmResponse[]>([]);
  const [popular, setPopular] = useState<ProductResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/giris");
      return;
    }

    const token = getAccessToken();

    Promise.all([
      fetch(`${API_BASE}/alarms/`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((r) => (r.ok ? r.json() : []))
        .catch(() => []),
      fetch(`${API_BASE}/home/most-alarmed`)
        .then((r) => (r.ok ? r.json() : []))
        .catch(() => []),
    ]).then(([alarmsData, popularData]) => {
      setAlarms(alarmsData);
      setPopular(filterDisplayable(popularData).slice(0, 8));
      setLoading(false);
    });
  }, [router]);

  const activeAlarms = alarms.filter(
    (a) => a.status === "ACTIVE" || a.status === "PAUSED"
  );
  const triggeredAlarms = alarms.filter((a) => a.status === "TRIGGERED");

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-16 text-center">
        <div className="animate-pulse text-gray-400">Yükleniyor...</div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">
        Kampanya Taleplerim
      </h1>

      {/* Active alarms */}
      {activeAlarms.length > 0 && (
        <section className="mb-10">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
            Aktif Talepler ({activeAlarms.length})
          </h2>
          <div className="space-y-3">
            {activeAlarms.map((alarm) => (
              <AlarmCard key={alarm.id} alarm={alarm} />
            ))}
          </div>
        </section>
      )}

      {/* Triggered alarms */}
      {triggeredAlarms.length > 0 && (
        <section className="mb-10">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
            Tetiklenen Talepler ({triggeredAlarms.length})
          </h2>
          <div className="space-y-3">
            {triggeredAlarms.map((alarm) => (
              <AlarmCard key={alarm.id} alarm={alarm} />
            ))}
          </div>
        </section>
      )}

      {/* Empty state */}
      {alarms.length === 0 && (
        <div className="text-center py-12 mb-10">
          <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
            <svg
              className="w-8 h-8 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
              />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-gray-900 mb-1">
            Henüz kampanya talebin yok
          </h2>
          <p className="text-sm text-gray-500 mb-6">
            Ürün sayfalarından fiyat düşüşü talebi oluşturabilirsin
          </p>
        </div>
      )}

      {/* Popular products */}
      {popular.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
            En Çok Talep Edilen Ürünler
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
            {popular.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function AlarmCard({ alarm }: { alarm: AlarmResponse }) {
  const product = alarm.product;
  const catSlug = product.category_slug ?? "urun";
  const slug = productSlug(product.title, product.id);
  const href = `/${catSlug}/${slug}`;

  const activeStores = product.stores.filter(
    (s) => s.current_price != null && s.in_stock
  );
  const currentPrice = activeStores.length
    ? Math.min(...activeStores.map((s) => s.current_price!))
    : null;

  const progress =
    currentPrice && alarm.target_price
      ? Math.min((alarm.target_price / currentPrice) * 100, 100)
      : 0;

  const isTriggered = alarm.status === "TRIGGERED";
  const isPaused = alarm.status === "PAUSED";

  return (
    <Link
      href={href}
      className="flex items-center gap-4 bg-white border border-gray-200 rounded-xl p-4 hover:shadow-md hover:border-brand/30 transition-all"
    >
      {/* Product image */}
      <div className="relative w-16 h-16 flex-shrink-0 bg-white rounded-lg overflow-hidden">
        <ProductImage
          src={product.image_url}
          alt={product.title}
          fill
          className="object-contain"
          sizes="64px"
        />
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <h3 className="text-sm font-medium text-gray-900 line-clamp-1">
          {product.short_title || product.title}
        </h3>

        <div className="flex items-center gap-3 mt-1">
          <span className="text-sm font-bold text-gray-900">
            {formatPrice(currentPrice)}
          </span>
          <span className="text-xs text-gray-400">
            Hedef: {formatPrice(alarm.target_price)}
          </span>
        </div>

        {/* Progress bar */}
        {!isTriggered && (
          <div className="mt-2 h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-brand rounded-full transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}

        {isTriggered && (
          <p className="text-xs text-green-600 font-medium mt-1">
            Fiyat {formatPrice(alarm.triggered_price)} seviyesine düştü!
          </p>
        )}
      </div>

      {/* Status badge */}
      <div className="flex-shrink-0">
        {isTriggered ? (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-green-50 text-green-700">
            Düştü
          </span>
        ) : isPaused ? (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-500">
            Durduruldu
          </span>
        ) : (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-brand">
            Aktif
          </span>
        )}
      </div>
    </Link>
  );
}
