import { useState, useMemo } from 'react';
import { View, Text, TouchableOpacity, Dimensions } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LineChart } from 'react-native-gifted-charts';
import type { PriceHistoryPoint } from '@/types/api';

const CARD = '#1E293B';
const WHITE = '#FFFFFF';
const MUTED = '#64748B';
const BRAND = '#1D4ED8';

const RANGES = [
  { label: '1A', days: 30 },
  { label: '3A', days: 90 },
  { label: '6A', days: 180 },
  { label: '1Y', days: 365 },
];

function isPlaceholderPrice(price: number): boolean {
  const s = String(Math.round(price));
  if (s.length >= 5 && new Set(s).size === 1) return true;
  return false;
}

function computeIQRBounds(prices: number[]): { lower: number; upper: number } {
  const sorted = [...prices].sort((a, b) => a - b);
  const n = sorted.length;
  if (n < 4) {
    const median = sorted[Math.floor(n / 2)] || 0;
    return { lower: median * 0.3, upper: median * 2.5 };
  }
  const q1 = sorted[Math.floor(n * 0.25)];
  const q3 = sorted[Math.floor(n * 0.75)];
  const iqr = q3 - q1;
  return {
    lower: Math.max(q1 - 2.5 * iqr, 0),
    upper: q3 + 2.5 * iqr,
  };
}

function fmt(price: number): string {
  return Math.round(price).toLocaleString('tr-TR') + ' TL';
}

interface PriceHistoryChartProps {
  data: PriceHistoryPoint[];
}

export function PriceHistoryChart({ data }: PriceHistoryChartProps) {
  const screenWidth = Dimensions.get('window').width;
  const chartWidth = screenWidth - 80;

  const cleanData = useMemo(() => {
    const valid = data.filter(d => d.price > 0 && !isPlaceholderPrice(d.price));
    if (valid.length < 2) return data;
    const prices = valid.map(d => d.price);
    const { lower, upper } = computeIQRBounds(prices);
    const filtered = valid.filter(d => d.price >= lower && d.price <= upper);
    return filtered.length > 1 ? filtered : valid;
  }, [data]);

  const dataSpanDays = useMemo(() => {
    if (cleanData.length < 2) return 0;
    const dates = cleanData.map(d => new Date(d.recorded_at).getTime());
    return Math.ceil((Math.max(...dates) - Math.min(...dates)) / (1000 * 60 * 60 * 24));
  }, [cleanData]);

  const defaultRange = dataSpanDays <= 90 ? 365 : 180;
  const [rangeDays, setRangeDays] = useState(defaultRange);

  const displayData = useMemo(() => {
    const latest = cleanData.reduce((max, d) => {
      const t = new Date(d.recorded_at).getTime();
      return t > max ? t : max;
    }, 0);
    const cutoff = latest - rangeDays * 24 * 60 * 60 * 1000;
    const inRange = cleanData.filter(d => new Date(d.recorded_at).getTime() >= cutoff);
    const result = inRange.length > 0 ? inRange : cleanData;
    return result.sort((a, b) =>
      new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime()
    );
  }, [cleanData, rangeDays]);

  const chartData = useMemo(() => {
    const maxPoints = 60;
    let points = displayData;
    if (points.length > maxPoints) {
      const step = Math.ceil(points.length / maxPoints);
      points = points.filter((_, i) => i % step === 0 || i === points.length - 1);
    }
    return points.map(d => ({
      value: d.price,
      label: new Date(d.recorded_at).toLocaleDateString('tr-TR', { day: 'numeric', month: 'short' }),
    }));
  }, [displayData]);

  const prices = displayData.map(d => d.price);
  const minPrice = prices.length ? Math.min(...prices) : 0;
  const maxPrice = prices.length ? Math.max(...prices) : 0;
  const yAxisOffset = Math.floor(minPrice * 0.92);

  if (chartData.length < 2) {
    return (
      <View style={{ backgroundColor: CARD, borderRadius: 16, padding: 16, gap: 12 }}>
        <Text style={{ color: WHITE, fontSize: 16, fontFamily: 'Inter_700Bold' }}>
          Fiyat Geçmişi
        </Text>
        <View style={{ alignItems: 'center', paddingVertical: 24, gap: 8 }}>
          <Ionicons name="analytics-outline" size={32} color={MUTED} />
          <Text style={{ color: MUTED, fontSize: 13, fontFamily: 'Inter_400Regular' }}>
            Henüz yeterli fiyat verisi yok
          </Text>
        </View>
      </View>
    );
  }

  const labelStep = Math.max(Math.floor(chartData.length / 5), 1);

  return (
    <View style={{ backgroundColor: CARD, borderRadius: 16, padding: 16, gap: 12 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <Text style={{ color: WHITE, fontSize: 16, fontFamily: 'Inter_700Bold' }}>
          Fiyat Geçmişi
        </Text>
        <View style={{ flexDirection: 'row', gap: 4 }}>
          {RANGES.map(r => (
            <TouchableOpacity
              key={r.label}
              onPress={() => setRangeDays(r.days)}
              style={{
                paddingHorizontal: 8,
                paddingVertical: 4,
                borderRadius: 8,
                backgroundColor: rangeDays === r.days ? BRAND : '#0F172A',
              }}
            >
              <Text style={{
                color: rangeDays === r.days ? WHITE : MUTED,
                fontSize: 11,
                fontFamily: 'Inter_600SemiBold',
              }}>
                {r.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      <View style={{ marginLeft: -16 }}>
        <LineChart
          data={chartData}
          width={chartWidth}
          height={180}
          color={BRAND}
          thickness={2}
          hideDataPoints
          curved
          areaChart
          startFillColor={`${BRAND}30`}
          endFillColor={`${BRAND}05`}
          startOpacity={0.3}
          endOpacity={0.05}
          hideRules
          yAxisColor="transparent"
          xAxisColor="#334155"
          yAxisTextStyle={{ color: MUTED, fontSize: 9 }}
          xAxisLabelTextStyle={{ color: MUTED, fontSize: 8 }}
          noOfSections={4}
          showXAxisIndices={false}
          spacing={Math.max(chartWidth / chartData.length, 8)}
          xAxisLabelTexts={chartData.map((d, i) =>
            i % labelStep === 0 || i === chartData.length - 1 ? d.label : ''
          )}
          maxValue={maxPrice * 1.05 - yAxisOffset}
          yAxisOffset={yAxisOffset}
          pointerConfig={{
            pointerStripColor: '#334155',
            pointerStripWidth: 1,
            pointerColor: BRAND,
            radius: 4,
            pointerLabelWidth: 100,
            pointerLabelHeight: 40,
            pointerLabelComponent: (items: any) => (
              <View style={{
                backgroundColor: '#0F172A',
                borderRadius: 8,
                paddingHorizontal: 8,
                paddingVertical: 4,
                borderWidth: 1,
                borderColor: '#334155',
              }}>
                <Text style={{ color: WHITE, fontSize: 12, fontFamily: 'Inter_700Bold' }}>
                  {fmt(items[0]?.value ?? 0)}
                </Text>
              </View>
            ),
          }}
        />
      </View>

      {/* Summary */}
      <View style={{ flexDirection: 'row', gap: 16, borderTopWidth: 1, borderTopColor: '#334155', paddingTop: 10 }}>
        <View>
          <Text style={{ color: MUTED, fontSize: 10 }}>En Düşük</Text>
          <Text style={{ color: '#22C55E', fontSize: 13, fontFamily: 'Inter_700Bold' }}>{fmt(minPrice)}</Text>
        </View>
        <View>
          <Text style={{ color: MUTED, fontSize: 10 }}>En Yüksek</Text>
          <Text style={{ color: '#EF4444', fontSize: 13, fontFamily: 'Inter_700Bold' }}>{fmt(maxPrice)}</Text>
        </View>
        <View>
          <Text style={{ color: MUTED, fontSize: 10 }}>Veri noktası</Text>
          <Text style={{ color: MUTED, fontSize: 13, fontFamily: 'Inter_600SemiBold' }}>{displayData.length}</Text>
        </View>
      </View>
    </View>
  );
}
