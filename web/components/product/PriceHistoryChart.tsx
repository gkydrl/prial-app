"use client";

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

export function PriceHistoryChart({ data }: Props) {
  // Outlier filtresi: negatif ve medyandan %90+ sapan değerleri kaldır
  const rawPrices = data.map((d) => d.price).filter((p) => p > 0);
  const sorted = [...rawPrices].sort((a, b) => a - b);
  const median = sorted[Math.floor(sorted.length / 2)] || 0;
  const lowerBound = median * 0.1;
  const upperBound = median * 3;

  const filtered = data.filter(
    (d) => d.price > lowerBound && d.price < upperBound
  );
  const displayData = filtered.length > 1 ? filtered : data;

  const chartData = displayData.map((d) => ({
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
  }));

  const prices = displayData.map((d) => d.price);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const padding = (maxPrice - minPrice) * 0.1 || 100;

  return (
    <div className="bg-surface rounded-xl border border-gray-100 p-4">
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
            tick={{ fontSize: 12, fill: "#6B7280" }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            domain={[minPrice - padding, maxPrice + padding]}
            tick={{ fontSize: 12, fill: "#6B7280" }}
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
      <div className="mt-4 flex gap-6 text-sm border-t border-gray-100 pt-3">
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
          <span className="text-gray-500">Son {displayData.length} veri noktası</span>
        </div>
      </div>
    </div>
  );
}
