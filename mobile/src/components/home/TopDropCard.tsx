import { View, Text, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import type { TopDropResponse } from '@/types/api';

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

export function TopDropCard({ item }: { item: TopDropResponse }) {
  const { store, price_now, price_24h_ago, drop_percent } = item;

  const nowStr = price_now.toLocaleString('tr-TR', { maximumFractionDigits: 0 }) + ' ₺';
  const agoStr = price_24h_ago.toLocaleString('tr-TR', { maximumFractionDigits: 0 }) + ' ₺';

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
      <View
        style={{
          width: '100%',
          height: 130,
          backgroundColor: '#052E16',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 4,
        }}
      >
        <Ionicons name="trending-down" size={28} color="#22C55E" />
        <Text style={{ color: '#22C55E', fontSize: 22, fontFamily: 'Inter_700Bold' }}>
          %{drop_percent.toFixed(1)}
        </Text>
        <Text style={{ color: '#6B7280', fontSize: 11, fontFamily: 'Inter_400Regular' }}>
          24 saatte düştü
        </Text>
      </View>

      <View style={{ flex: 1, padding: 8 }}>
        <Text
          style={{
            color: '#FFFFFF',
            fontSize: 12,
            fontFamily: 'Inter_600SemiBold',
            lineHeight: 16,
            marginBottom: 4,
          }}
          numberOfLines={1}
        >
          {STORE_LABELS[store.store]}
        </Text>

        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <View style={{ gap: 1 }}>
            <Text
              style={{
                color: '#6B7280',
                fontSize: 11,
                fontFamily: 'Inter_400Regular',
                textDecorationLine: 'line-through',
              }}
            >
              {agoStr}
            </Text>
            <Text style={{ color: '#FFFFFF', fontSize: 14, fontFamily: 'Inter_700Bold' }}>
              {nowStr}
            </Text>
          </View>

          <TouchableOpacity hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
            <Ionicons name="notifications-outline" size={16} color="#6C47FF" />
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
}
