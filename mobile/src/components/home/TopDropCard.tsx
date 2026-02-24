import { View, Text, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import type { TopDropResponse } from '@/types/api';

/** URL'den okunabilir ürün adı türetir */
function nameFromUrl(url: string): string {
  try {
    const segments = new URL(url).pathname.split('/').filter(Boolean);
    // En uzun segment genellikle ürün slug'ıdır
    const slug = segments.sort((a, b) => b.length - a.length)[0] ?? '';
    const cleaned = slug
      .replace(/-p-\d+$/, '')       // Trendyol: -p-146157
      .replace(/-hb-\d+$/, '')      // Hepsiburada: -hb-XXX
      .replace(/-\d+$/, '')         // genel sayısal suffix
      .replace(/-/g, ' ')
      .trim();
    if (!cleaned) return 'Ürün';
    return cleaned.charAt(0).toUpperCase() + cleaned.slice(1, 42);
  } catch {
    return 'Ürün';
  }
}

export function TopDropCard({ item }: { item: TopDropResponse }) {
  const { store, price_now, price_24h_ago, drop_percent } = item;

  const nowStr = price_now.toLocaleString('tr-TR', { maximumFractionDigits: 0 }) + ' ₺';
  const agoStr = price_24h_ago.toLocaleString('tr-TR', { maximumFractionDigits: 0 }) + ' ₺';
  const productName = nameFromUrl(store.url);

  return (
    <View
      style={{
        width: 160,
        height: 200,
        backgroundColor: '#0F172A',
        borderRadius: 12,
        overflow: 'hidden',
      }}
    >
      {/* Görsel alanı — 140px (%65) */}
      <View
        style={{
          width: '100%',
          height: 140,
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

      {/* Yazı alanı — 60px (%35) */}
      <View
        style={{
          height: 60,
          paddingHorizontal: 8,
          paddingVertical: 6,
          justifyContent: 'space-between',
        }}
      >
        <Text
          style={{ color: '#FFFFFF', fontSize: 11, fontFamily: 'Inter_600SemiBold', lineHeight: 15 }}
          numberOfLines={1}
        >
          {productName}
        </Text>

        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
            <Text
              style={{
                color: '#6B7280',
                fontSize: 10,
                fontFamily: 'Inter_400Regular',
                textDecorationLine: 'line-through',
              }}
            >
              {agoStr}
            </Text>
            <Text style={{ color: '#FFFFFF', fontSize: 13, fontFamily: 'Inter_700Bold' }}>
              {nowStr}
            </Text>
          </View>
          <TouchableOpacity hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
            <Ionicons name="notifications-outline" size={15} color="#6C47FF" />
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
}
