"use client";

import { useState } from "react";
import type { ProductResponse, ProductStoreResponse } from "@/lib/api";
import { formatPrice } from "@/lib/formatPrice";
import { storeLabel } from "@/lib/stores";
import { SignalBadge } from "@/components/ui/SignalBadge";

interface Props {
  product: ProductResponse;
  bestStore: ProductStoreResponse | null;
}

const CARD_CONFIG = {
  IYI_FIYAT: {
    bg: "bg-[#EDFCF2]",
    border: "border-[#86EFAC]",
    badgeBg: "bg-success",
    textColor: "text-gray-700",
  },
  FIYAT_DUSEBILIR: {
    bg: "bg-[#FAEEDA]",
    border: "border-[#FAC775]",
    badgeBg: "bg-[#D97706]",
    textColor: "text-[#633806]",
  },
  FIYAT_YUKSELISTE: {
    bg: "bg-[#FAEEDA]",
    border: "border-[#FAC775]",
    badgeBg: "bg-[#D97706]",
    textColor: "text-[#633806]",
  },
} as const;

export function PredictionCard({ product, bestStore }: Props) {
  const rec = product.recommendation;
  const config = rec ? CARD_CONFIG[rec] : null;
  const [sliderOpen, setSliderOpen] = useState(false);

  const bestPrice = bestStore?.current_price ?? 0;
  // Slider min: l1y_lowest varsa ve mantıklıysa onu kullan, yoksa %70
  const l1yLowest = product.l1y_lowest_price ? Number(product.l1y_lowest_price) : null;
  const l1yValid = l1yLowest && l1yLowest >= bestPrice * 0.3; // saçma düşük değerleri filtrele
  const sliderMin = l1yValid ? Math.round(l1yLowest) : Math.round(bestPrice * 0.7);
  const sliderMax = Math.round(bestPrice);
  const defaultTarget = l1yValid
    ? Math.round(l1yLowest)
    : Math.round(bestPrice * 0.85);
  const [targetPrice, setTargetPrice] = useState(
    Math.max(sliderMin, Math.min(sliderMax, defaultTarget))
  );

  // Mock social proof — 0 ise gösterilmeyecek
  const campaignRequestCount = product.alarm_count || 0;

  // No prediction available
  if (!config) {
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

  const isIyiFiyat = rec === "IYI_FIYAT";
  const isDusebilirOrYukseliste = rec === "FIYAT_DUSEBILIR" || rec === "FIYAT_YUKSELISTE";

  return (
    <div>
      <div className={`rounded-xl border-2 ${config.border} ${config.bg} p-6`}>
        {/* Badge + Confidence */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <SignalBadge recommendation={rec!} size="lg" />
            {product.prediction_confidence != null && (
              <span className="text-xs text-gray-500">
                %{Math.round(product.prediction_confidence * 100)} güven
              </span>
            )}
          </div>
          <span className={`text-xs font-medium px-2 py-1 rounded-full ${config.badgeBg} text-white`}>
            AI Tavsiyesi
          </span>
        </div>

        {/* AI Reasoning — tek cümle */}
        {product.reasoning_text && (
          <p className={`text-sm ${config.textColor} leading-relaxed mb-4`}>
            {product.reasoning_text}
          </p>
        )}

        {/* AL → Best store link */}
        {isIyiFiyat && bestStore && (
          <div className="p-3 bg-white/80 rounded-xl border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">En ucuz fiyat</p>
                <p className="text-xl font-bold text-gray-900">
                  {formatPrice(bestStore.current_price)}
                </p>
                <p className="text-xs text-gray-500">
                  {storeLabel(bestStore.store)}
                </p>
              </div>
              <a
                href={bestStore.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 bg-success text-white font-semibold py-2.5 px-5 rounded-xl hover:bg-success/90 transition-colors text-sm"
              >
                Mağazaya Git
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            </div>
          </div>
        )}

        {/* BEKLE → Slider-based target price */}
        {isDusebilirOrYukseliste && (
          <div>
            {!sliderOpen ? (
              <button
                onClick={() => setSliderOpen(true)}
                className="w-full inline-flex items-center justify-center gap-1.5 bg-[#D97706] text-white font-semibold py-2 px-4 rounded-lg hover:bg-[#B45309] transition-colors text-xs"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z" />
                </svg>
                Fiyat Belirle
              </button>
            ) : (
              <div className="p-3 bg-white/80 rounded-lg border border-gray-100 space-y-2.5">
                {/* Selected price */}
                <div className="text-center">
                  <p className="text-[11px] text-gray-500">Hedef fiyat</p>
                  <p className="text-xl font-bold text-gray-900">
                    {formatPrice(targetPrice)}
                  </p>
                </div>

                {/* Slider */}
                <div>
                  <input
                    type="range"
                    min={sliderMin}
                    max={sliderMax}
                    step={Math.max(1, Math.round((sliderMax - sliderMin) / 100))}
                    value={targetPrice}
                    onChange={(e) => setTargetPrice(Number(e.target.value))}
                    className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-[#D97706]"
                  />
                  <div className="flex justify-between text-[11px] text-gray-400 mt-0.5">
                    <span>{formatPrice(sliderMin)}</span>
                    <span>{formatPrice(sliderMax)}</span>
                  </div>
                </div>

                {/* Kampanya Talep Et */}
                <a
                  href={`prial://product/${product.id}?action=alarm&target=${targetPrice}`}
                  className="w-full inline-flex items-center justify-center gap-1.5 bg-[#D97706] text-white font-semibold py-2 px-4 rounded-lg hover:bg-[#B45309] transition-colors text-xs"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z" />
                  </svg>
                  Kampanya Talep Et
                </a>

                {/* Social proof */}
                {campaignRequestCount > 0 && (
                  <p className="text-[11px] text-gray-500 text-center">
                    {campaignRequestCount} kişi bu ürün için kampanya talep etti
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Social proof for AL */}
        {isIyiFiyat && campaignRequestCount > 0 && (
          <p className="text-xs text-gray-500 text-center mt-3">
            {campaignRequestCount} kişi bu ürünü takip ediyor
          </p>
        )}
      </div>

      {/* Seasonal context — below the card */}
      <SeasonalContext />
    </div>
  );
}

/** Sezonsal bağlam satırı — yaklaşan kampanya varsa göster */
function SeasonalContext() {
  // Hardcoded for now — sonraki fazda dinamik
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

  // En yakın gelecek event'i bul
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
