import { View, Text, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import type { ProductStoreResponse } from '@/types/api';

const STORE_LABELS: Record<string, string> = {
  trendyol: 'Trendyol',
  hepsiburada: 'Hepsiburada',
  amazon: 'Amazon',
  n11: 'N11',
  ciceksepeti: 'Çiçeksepeti',
  mediamarkt: 'MediaMarkt',
  teknosa: 'Teknosa',
  vatan: 'Vatan',
  other: 'Diğer',
};

const STORE_COLORS: Record<string, string> = {
  trendyol: '#F27A1A',
  hepsiburada: '#FF6000',
  amazon: '#FF9900',
  n11: '#6B21A8',
  ciceksepeti: '#E11D48',
  mediamarkt: '#CC0000',
  teknosa: '#1D4ED8',
  vatan: '#DC2626',
  other: '#334155',
};

export function DealCard({ store }: { store: ProductStoreResponse }) {
  const price = store.current_price;
  const priceStr = price != null ? price.toLocaleString('tr-TR', { maximumFractionDigits: 0 }) + ' ₺' : '-';
  const bgColor = STORE_COLORS[store.store] ?? '#334155';

  return (
    <View
      style={{
        width: 160,
        height: 220,
        backgroundColor: '#0F172A',
        borderRadius: 12,
        overflow: 'hidden',
      }}
    >
      {/* Mağaza rengi alanı */}
      <View
        style={{
          width: '100%',
          height: 110,
          backgroundColor: bgColor,
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Text style={{ color: '#FFFFFF', fontSize: 15, fontFamily: 'Inter_700Bold' }}>
          {STORE_LABELS[store.store]}
        </Text>
      </View>

      {/* İçerik */}
      <View style={{ flex: 1, padding: 10, justifyContent: 'space-between' }}>
        <Text
          style={{ color: '#9CA3AF', fontSize: 11, fontFamily: 'Inter_400Regular' }}
          numberOfLines={2}
        >
          {store.url.replace(/^https?:\/\/(www\.)?/, '').split('/')[0]}
        </Text>

        <View style={{ flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between' }}>
          <View style={{ gap: 4 }}>
            {!!store.discount_percent && (
              <View
                style={{
                  backgroundColor: '#22C55E',
                  borderRadius: 4,
                  paddingHorizontal: 6,
                  paddingVertical: 2,
                  alignSelf: 'flex-start',
                }}
              >
                <Text style={{ color: '#FFFFFF', fontSize: 10, fontFamily: 'Inter_700Bold' }}>
                  %{store.discount_percent}
                </Text>
              </View>
            )}
            <Text style={{ color: '#FFFFFF', fontSize: 14, fontFamily: 'Inter_700Bold' }}>
              {priceStr}
            </Text>
          </View>

          <TouchableOpacity hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
            <Ionicons name="bell-outline" size={18} color="#6C47FF" />
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
}
