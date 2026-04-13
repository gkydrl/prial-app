import { View, Text } from 'react-native';
import type { ProductResponse, ProductStoreResponse } from '@/types/api';

const CARD = '#1E293B';
const WHITE = '#FFFFFF';
const MUTED = '#64748B';

interface PriceSummaryProps {
  product: ProductResponse;
  bestPrice: number | null;
  stores: ProductStoreResponse[];
}

function fmt(price: number | null | undefined): string {
  if (price == null) return '-';
  return Math.round(Number(price)).toLocaleString('tr-TR') + ' TL';
}

function Cell({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <View style={{ flex: 1, alignItems: 'center', gap: 4, paddingVertical: 8 }}>
      <Text style={{ color: MUTED, fontSize: 11, fontFamily: 'Inter_400Regular' }}>
        {label}
      </Text>
      <Text style={{ color, fontSize: 16, fontFamily: 'Inter_700Bold' }}>
        {value}
      </Text>
    </View>
  );
}

export function PriceSummary({ product, bestPrice, stores }: PriceSummaryProps) {
  // Sanity check: hatali veri filtresi (web ile ayni)
  const saneL1yLowest = product.l1y_lowest_price && bestPrice
    && product.l1y_lowest_price >= bestPrice * 0.3
    ? product.l1y_lowest_price : null;
  const saneL1yHighest = product.l1y_highest_price && bestPrice
    && product.l1y_highest_price >= bestPrice * 0.3
    ? product.l1y_highest_price : null;
  const saneLowestEver = product.lowest_price_ever && bestPrice
    && product.lowest_price_ever >= bestPrice * 0.1
    ? product.lowest_price_ever : null;

  // En yuksek aktif store fiyati (web ile ayni)
  const activeStorePrices = stores
    .filter(s => s.current_price != null && s.in_stock && s.store !== 'other')
    .map(s => Number(s.current_price));
  const highestPrice = activeStorePrices.length > 0
    ? Math.max(...activeStorePrices)
    : null;
  const showHighest = highestPrice != null && bestPrice != null && highestPrice > bestPrice;

  const hasAny = bestPrice != null || saneL1yLowest != null || saneL1yHighest != null || saneLowestEver != null;
  if (!hasAny) return null;

  return (
    <View style={{ backgroundColor: CARD, borderRadius: 16, padding: 16, gap: 12 }}>
      <Text style={{ color: WHITE, fontSize: 16, fontFamily: 'Inter_700Bold' }}>
        Fiyat Özeti
      </Text>

      <View style={{ gap: 4 }}>
        {/* Row 1 */}
        <View style={{ flexDirection: 'row' }}>
          <Cell label="En Ucuz Şimdi" value={fmt(bestPrice)} color={WHITE} />
          <View style={{ width: 1, backgroundColor: '#334155', marginVertical: 8 }} />
          <Cell label={showHighest ? 'En Yüksek' : '1Y En Düşük'} value={showHighest ? fmt(highestPrice) : fmt(saneL1yLowest)} color={showHighest ? '#F59E0B' : '#22C55E'} />
        </View>

        <View style={{ height: 1, backgroundColor: '#334155' }} />

        {/* Row 2 */}
        <View style={{ flexDirection: 'row' }}>
          <Cell label="1Y En Düşük" value={fmt(saneL1yLowest)} color="#22C55E" />
          <View style={{ width: 1, backgroundColor: '#334155', marginVertical: 8 }} />
          <Cell label="1Y En Yüksek" value={fmt(saneL1yHighest)} color="#EF4444" />
        </View>

        {saneLowestEver != null && (
          <>
            <View style={{ height: 1, backgroundColor: '#334155' }} />
            {/* Row 3 */}
            <View style={{ flexDirection: 'row' }}>
              <Cell label="Tüm Zamanların En Düşüğü" value={fmt(saneLowestEver)} color={MUTED} />
            </View>
          </>
        )}
      </View>
    </View>
  );
}
