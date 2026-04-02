"use client";

import { useState } from "react";
import Image from "next/image";
import type { ProductResponse, ProductStoreResponse } from "@/lib/api";
import { formatPrice } from "@/lib/formatPrice";
import { storeLabel, storeLogo, storeShipping, storeInstallment } from "@/lib/stores";
import { SignalBadge } from "@/components/ui/SignalBadge";

interface PrialSaysProps {
  product: ProductResponse;
  bestStore: ProductStoreResponse | null;
  secondBestStore: ProductStoreResponse | null;
}

const CTA_THEME = {
  IYI_FIYAT: "bg-success hover:bg-success/90 text-white",
  FIYAT_DUSEBILIR: "bg-bekle-dark hover:bg-bekle-dark/90 text-white",
  FIYAT_YUKSELISTE: "bg-danger hover:bg-danger/90 text-white",
} as const;

function buildPrialParagraph(product: ProductResponse, bestPrice: number | null): string {
  const parts: string[] = [];

  if (product.reasoning_text) {
    parts.push(product.reasoning_text);
  }

  if (product.reasoning_pros && product.reasoning_pros.length > 0) {
    const prosText =
      product.reasoning_pros.length === 1
        ? product.reasoning_pros[0]
        : `${product.reasoning_pros[0]} ve ${product.reasoning_pros[1]}`;
    parts.push(`Özellikle ${prosText} önemli avantajlar.`);
  }

  if (product.reasoning_cons && product.reasoning_cons.length > 0) {
    parts.push(`Öte yandan, ${product.reasoning_cons[0]} konusunda dikkatli olunmalı.`);
  }

  if (bestPrice && product.l1y_lowest_price) {
    const diff = bestPrice - product.l1y_lowest_price;
    const pct = (diff / product.l1y_lowest_price) * 100;
    if (pct <= 5) {
      parts.push("Mevcut fiyat son 1 yılın en düşüğüne oldukça yakın.");
    } else if (pct <= 15) {
      parts.push(`Mevcut fiyat son 1 yılın en düşüğünden %${Math.round(pct)} daha yüksek.`);
    }
  }

  if (product.recommendation === "IYI_FIYAT") {
    parts.push("Şimdi alabilirsiniz.");
  } else if (product.recommendation === "FIYAT_DUSEBILIR") {
    parts.push("Biraz beklemenizi öneriyoruz.");
  } else if (product.recommendation === "FIYAT_YUKSELISTE") {
    parts.push("Fiyat yükselişte, kaçırmayın.");
  }

  return parts.join(" ");
}

export function PrialSays({ product, bestStore, secondBestStore }: PrialSaysProps) {
  const rec = product.recommendation;

  const bestPrice = bestStore?.current_price ?? 0;
  const l1yLowest = product.l1y_lowest_price ? Number(product.l1y_lowest_price) : null;
  const l1yValid = l1yLowest && l1yLowest >= bestPrice * 0.3;
  const sliderMin = l1yValid ? Math.round(l1yLowest) : Math.round(bestPrice * 0.7);
  const sliderMax = Math.round(bestPrice);
  const defaultTarget = l1yValid ? Math.round(l1yLowest) : Math.round(bestPrice * 0.85);
  const [targetPrice, setTargetPrice] = useState(
    Math.max(sliderMin, Math.min(sliderMax, defaultTarget))
  );
  const [sliderOpen, setSliderOpen] = useState(false);

  const campaignRequestCount = product.alarm_count || 0;

  if (!rec) {
    return (
      <div className="rounded-xl border border-gray-200 bg-gray-50 p-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center">
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <div>
            <p className="font-semibold text-gray-700">AI Analizi Bekleniyor</p>
            <p className="text-sm text-gray-500">Bu ürün için tahmin henüz oluşturulmadı.</p>
          </div>
        </div>
      </div>
    );
  }

  const ctaClass = CTA_THEME[rec];
  const paragraph = buildPrialParagraph(product, bestStore?.current_price ?? null);
  const isIyiFiyat = rec === "IYI_FIYAT";
  const stores = [bestStore, secondBestStore].filter(Boolean) as ProductStoreResponse[];

  return (
    <div>
      <div className="rounded-xl border border-gray-200 shadow-sm bg-white p-5 animate-[prial-fade-in_0.4s_ease-out]">
        {/* Header: Prial logo + der ki + SignalBadge */}
        <div className="flex items-center justify-between mb-3">
          <span className="text-lg font-bold text-gray-900 flex items-center gap-1.5">
            <Image src="/logo-icon.png" alt="Prial" width={56} height={20} className="inline-block" />
            <span className="text-gray-400 font-normal">der ki:</span>
          </span>
          <SignalBadge recommendation={rec} size="md" />
        </div>

        {/* Paragraph */}
        {paragraph && (
          <p className="text-sm text-gray-700 leading-relaxed mb-4">{paragraph}</p>
        )}

        {/* Store Cards */}
        <div className="space-y-2 mb-4">
          {stores.map((store, i) => {
            const logo = storeLogo(store.store);
            const shipping = store.delivery_text || storeShipping(store.store);
            const installment = store.installment_text || storeInstallment(store.store);

            return (
              <a
                key={store.id}
                href={store.url}
                target="_blank"
                rel="noopener noreferrer"
                className={`block p-3 rounded-lg border transition-all ${
                  i === 0
                    ? "border-gray-200 shadow-sm hover:shadow-md"
                    : "border-gray-100 hover:shadow-sm"
                } hover:border-brand/30 bg-white`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    {logo && (
                      <img
                        src={`/api/img?url=${encodeURIComponent(logo)}`}
                        alt={storeLabel(store.store)}
                        width={20}
                        height={20}
                        className="w-5 h-5 rounded object-contain flex-shrink-0"
                      />
                    )}
                    <span className="text-sm font-semibold text-gray-800">
                      {storeLabel(store.store)}
                    </span>
                  </div>
                  <span className="text-base font-bold text-gray-900">
                    {formatPrice(store.current_price)}
                  </span>
                </div>
                {/* Shipping + Installment details */}
                <div className="flex items-center gap-3 mt-1.5 ml-[30px]">
                  {shipping && (
                    <span className="text-xs text-gray-400 flex items-center gap-1">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8" />
                      </svg>
                      {shipping}
                    </span>
                  )}
                  {installment && (
                    <span className="text-xs text-gray-400 flex items-center gap-1">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                      </svg>
                      {installment}
                    </span>
                  )}
                </div>
              </a>
            );
          })}
        </div>

        {/* Social Proof + CTA */}
        <div className="space-y-3">
          {isIyiFiyat && (
            <a
              href={`prial://product/${product.id}?action=alarm`}
              className={`w-full inline-flex items-center justify-center gap-2 ${ctaClass} font-semibold py-3 px-5 rounded-xl transition-colors text-sm`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z" />
              </svg>
              Kampanya Talep Et
            </a>
          )}

          {!isIyiFiyat && (
            <>
              {!sliderOpen ? (
                <button
                  onClick={() => setSliderOpen(true)}
                  className={`w-full inline-flex items-center justify-center gap-2 ${ctaClass} font-semibold py-3 px-5 rounded-xl transition-colors text-sm`}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z" />
                  </svg>
                  Kampanya Talep Et
                </button>
              ) : (
                <div className="p-4 bg-gray-50 rounded-xl border border-gray-100 space-y-3">
                  <div className="text-center">
                    <p className="text-xs text-gray-500">Hedef fiyat</p>
                    <p className="text-xl font-bold text-gray-900">{formatPrice(targetPrice)}</p>
                  </div>
                  <div>
                    <input
                      type="range"
                      min={sliderMin}
                      max={sliderMax}
                      step={Math.max(1, Math.round((sliderMax - sliderMin) / 100))}
                      value={targetPrice}
                      onChange={(e) => setTargetPrice(Number(e.target.value))}
                      aria-label="Hedef fiyat seçici"
                      className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-bekle-dark"
                    />
                    <div className="flex justify-between text-xs text-gray-400 mt-1">
                      <span>{formatPrice(sliderMin)}</span>
                      <span>{formatPrice(sliderMax)}</span>
                    </div>
                  </div>
                  <a
                    href={`prial://product/${product.id}?action=alarm&target=${targetPrice}`}
                    className={`w-full inline-flex items-center justify-center gap-2 ${ctaClass} font-semibold py-3 px-5 rounded-xl transition-colors text-sm`}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z" />
                    </svg>
                    Kampanya Talep Et
                  </a>
                </div>
              )}
            </>
          )}

          {campaignRequestCount > 0 && (
            <p className="text-sm text-gray-500 text-center">
              {campaignRequestCount} kişi bu ürün için fiyat talep etti
            </p>
          )}
        </div>
      </div>

      <SeasonalContext />
    </div>
  );
}

function SeasonalContext() {
  const now = new Date();
  const events = [
    { name: "23 Nisan İndirimleri", date: new Date(now.getFullYear(), 3, 23) },
    { name: "Yaz İndirimleri", date: new Date(now.getFullYear(), 5, 21) },
    { name: "Kurban Bayramı İndirimleri", date: new Date(now.getFullYear(), 5, 6) },
    { name: "Ekim İndirimleri", date: new Date(now.getFullYear(), 9, 29) },
    { name: "11.11 İndirimleri", date: new Date(now.getFullYear(), 10, 11) },
    { name: "Black Friday", date: new Date(now.getFullYear(), 10, 28) },
    { name: "Yılbaşı İndirimleri", date: new Date(now.getFullYear(), 11, 25) },
  ];

  const upcoming = events
    .map((e) => {
      let date = e.date;
      if (date < now) {
        date = new Date(date.getFullYear() + 1, date.getMonth(), date.getDate());
      }
      const daysLeft = Math.ceil((date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
      return { ...e, daysLeft };
    })
    .filter((e) => e.daysLeft > 0 && e.daysLeft <= 45)
    .sort((a, b) => a.daysLeft - b.daysLeft)[0];

  if (!upcoming) return null;

  return (
    <div className="mt-2 flex items-center gap-2 text-xs text-gray-500 px-1">
      <span>🗓</span>
      <span>
        Bu ürün {upcoming.name} döneminde tarihi olarak indirime giriyor. {upcoming.daysLeft} gün kaldı.
      </span>
    </div>
  );
}
