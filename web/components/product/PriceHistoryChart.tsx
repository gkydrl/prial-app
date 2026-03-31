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

export function PriceHistoryChart({ data }: Props) {
  // Outlier filtresi: negatif ve medyandan %90+ sapan değerleri kaldır
  const rawPrices = data.map((d) => d.price).filter((p) => p > 0);
  const sorted = [...rawPrices].sort((a, b) => a - b);
  const median = sorted[Math.floor(sorted.length / 2)] || 0;
  const lowerBound = median * 0.1;
  const upperBound = median * 3;

  const cleanData = useMemo(() => {
    const filtered = data.filter(
      (d) => d.price > lowerBound && d.price < upperBound
    );
    return filtered.length > 1 ? filtered : data;
  }, [data, lowerBound, upperBound]);

  // Varsayılan aralık: veri 90 günden azsa tümünü göster, yoksa 6A
  const defaultRange = cleanData.length <= 90 ? 365 : 180;
  const [rangeDays, setRangeDays] = useState(defaultRange);

  const displayData = useMemo(() => {
    const now = new Date();
    const cutoff = new Date(now.getTime() - rangeDays * 24 * 60 * 60 * 1000);
    const inRange = cleanData.filter(
      (d) => new Date(d.recorded_at) >= cutoff
    );
    // Tarihe göre sırala (eskiden yeniye)
    return inRange.sort(
      (a, b) =>
        new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime()
    );
  }, [cleanData, rangeDays]);

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
            className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
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
