"use client";

import { useState, useMemo } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import type { PriceHistoryPoint } from "@/lib/api";
import { formatPrice } from "@/lib/formatPrice";

interface Props {
  data: PriceHistoryPoint[];
}

const RANGES = [
  { label: "1A", days: 30 },
  { label: "3A", days: 90 },
  { label: "6A", days: 180 },
  { label: "1Y", days: 365 },
] as const;

/** Tekrarlayan sahte fiyat tespiti (222222, 999999 gibi) */
function isPlaceholderPrice(price: number): boolean {
  const s = String(Math.round(price));
  if (s.length >= 5 && new Set(s).size === 1) return true; // 11111, 22222, ...
  if (s.length >= 6 && /^(\d)\1+$/.test(s)) return true; // 999999 vb.
  return false;
}

/** IQR tabanlı outlier sınırları hesapla */
function computeIQRBounds(prices: number[]): { lower: number; upper: number } {
  const sorted = [...prices].sort((a, b) => a - b);
  const n = sorted.length;
  if (n < 4) {
    // Yeterli veri yoksa gevşek sınır
    const median = sorted[Math.floor(n / 2)] || 0;
    return { lower: median * 0.3, upper: median * 2.5 };
  }
  const q1 = sorted[Math.floor(n * 0.25)];
  const q3 = sorted[Math.floor(n * 0.75)];
  const iqr = q3 - q1;
  // 2.5x IQR — 1.5x çok agresif olabilir gerçek fiyat değişimlerinde
  return {
    lower: Math.max(q1 - 2.5 * iqr, 0),
    upper: q3 + 2.5 * iqr,
  };
}

export function PriceHistoryChart({ data }: Props) {
  // Outlier filtresi: IQR yöntemi + placeholder fiyat tespiti
  const cleanData = useMemo(() => {
    // 1. Negatif/sıfır ve placeholder fiyatları çıkar
    const valid = data.filter((d) => d.price > 0 && !isPlaceholderPrice(d.price));
    if (valid.length < 2) return data;

    // 2. IQR sınırlarını hesapla
    const prices = valid.map((d) => d.price);
    const { lower, upper } = computeIQRBounds(prices);

    // 3. Sınırlar içinde kalan verileri filtrele
    const filtered = valid.filter((d) => d.price >= lower && d.price <= upper);
    return filtered.length > 1 ? filtered : valid;
  }, [data]);

  // En son veri noktasının tarihini bul — aralık filtresi buna göre çalışsın
  const latestDate = useMemo(() => {
    if (!cleanData.length) return new Date();
    return cleanData.reduce((max, d) => {
      const t = new Date(d.recorded_at);
      return t > max ? t : max;
    }, new Date(0));
  }, [cleanData]);

  // Varsayılan aralık: veri aralığına göre belirle
  const dataSpanDays = useMemo(() => {
    if (cleanData.length < 2) return 0;
    const earliest = cleanData.reduce((min, d) => {
      const t = new Date(d.recorded_at);
      return t < min ? t : min;
    }, new Date());
    return Math.ceil((latestDate.getTime() - earliest.getTime()) / (1000 * 60 * 60 * 24));
  }, [cleanData, latestDate]);

  const defaultRange = dataSpanDays <= 90 ? 365 : 180;
  const [rangeDays, setRangeDays] = useState(defaultRange);

  const displayData = useMemo(() => {
    // Aralık filtresini en son veri noktasına göre hesapla (bugüne göre değil)
    const cutoff = new Date(latestDate.getTime() - rangeDays * 24 * 60 * 60 * 1000);
    const inRange = cleanData.filter(
      (d) => new Date(d.recorded_at) >= cutoff
    );
    const result = inRange.length > 0 ? inRange : cleanData;
    // Tarihe göre sırala (eskiden yeniye)
    return result.sort(
      (a, b) =>
        new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime()
    );
  }, [cleanData, rangeDays, latestDate]);

  const chartData = useMemo(
    () =>
      displayData.map((d) => ({
        date: new Date(d.recorded_at).toLocaleDateString("tr-TR", {
          day: "numeric",
          month: "short",
        }),
        price: d.price,
        fullDate: new Date(d.recorded_at).toLocaleDateString("tr-TR", {
          day: "numeric",
          month: "long",
          year: "numeric",
        }),
      })),
    [displayData]
  );

  const prices = displayData.map((d) => d.price);
  const minPrice = prices.length ? Math.min(...prices) : 0;
  const maxPrice = prices.length ? Math.max(...prices) : 0;
  const padding = (maxPrice - minPrice) * 0.1 || 100;

  if (!displayData.length) return null;

  return (
    <div className="bg-surface rounded-xl border border-gray-100 p-4">
      {/* Zaman aralığı seçici */}
      <div className="flex items-center justify-end gap-1 mb-3">
        {RANGES.map((r) => (
          <button
            key={r.label}
            onClick={() => setRangeDays(r.days)}
            className={`px-2.5 py-1 text-xs font-medium rounded-lg transition-colors ${
              rangeDays === r.days
                ? "bg-brand text-white"
                : "bg-gray-100 text-gray-500 hover:bg-gray-200"
            }`}
          >
            {r.label}
          </button>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#1D4ED8" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#1D4ED8" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: "#6B7280" }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[minPrice - padding, maxPrice + padding]}
            tick={{ fontSize: 11, fill: "#6B7280" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => formatPrice(v)}
            width={80}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const item = payload[0].payload;
              return (
                <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
                  <p className="text-xs text-gray-500">{item.fullDate}</p>
                  <p className="text-sm font-bold text-brand">
                    {formatPrice(item.price)}
                  </p>
                </div>
              );
            }}
          />
          <Area
            type="monotone"
            dataKey="price"
            stroke="#1D4ED8"
            strokeWidth={2}
            fill="url(#priceGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>

      {/* Summary below chart */}
      <div className="mt-3 flex gap-6 text-sm border-t border-gray-100 pt-3">
        <div>
          <span className="text-gray-500">En Düşük: </span>
          <span className="font-semibold text-success">
            {formatPrice(minPrice)}
          </span>
        </div>
        <div>
          <span className="text-gray-500">En Yüksek: </span>
          <span className="font-semibold text-danger">
            {formatPrice(maxPrice)}
          </span>
        </div>
        <div>
          <span className="text-gray-500">{displayData.length} veri noktası</span>
        </div>
      </div>
    </div>
  );
}
