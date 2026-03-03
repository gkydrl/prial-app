import { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  FlatList,
  ActivityIndicator,
  useWindowDimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { homeApi } from '@/api/home';
import { TopDropCard } from '@/components/home/TopDropCard';
import { ProductCard } from '@/components/product/ProductCard';
import type { TopDropResponse, ProductResponse } from '@/types/api';

const BG = '#0A1628';
const CARD = '#1E293B';
const BRAND = '#6C47FF';

const PERIODS = [
  { label: 'Son 1 Gün', value: '1d' },
  { label: 'Son 1 Hafta', value: '7d' },
  { label: 'Son 1 Ay', value: '30d' },
  { label: 'Son 3 Ay', value: '90d' },
  { label: 'Son 1 Yıl', value: '365d' },
];

const PAGE_CONFIG: Record<string, { title: string; kind: 'drops' | 'alarmed' }> = {
  'daily-deals': { title: 'Bugünün Fırsatları', kind: 'drops' },
  'top-drops': { title: 'En Çok Düşenler', kind: 'drops' },
  'most-alarmed': { title: 'En Çok Talep Edilen', kind: 'alarmed' },
};

export default function FeedScreen() {
  const { type } = useLocalSearchParams<{ type: string }>();
  const config = PAGE_CONFIG[type ?? ''] ?? PAGE_CONFIG['daily-deals'];

  const { width: screenWidth } = useWindowDimensions();
  // 16px padding on each side + 8px gap between two cards
  const cardWidth = Math.floor((screenWidth - 40) / 2);

  const [period, setPeriod] = useState('1d');
  const [drops, setDrops] = useState<TopDropResponse[]>([]);
  const [alarmed, setAlarmed] = useState<ProductResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      if (config.kind === 'alarmed') {
        const res = await homeApi.mostAlarmed(50, period);
        setAlarmed(res.data);
      } else if (type === 'top-drops') {
        const res = await homeApi.topDrops(50, period);
        setDrops(res.data);
      } else {
        const res = await homeApi.dailyDeals(50, period);
        setDrops(res.data);
      }
    } catch {
      setDrops([]);
      setAlarmed([]);
    }
    setIsLoading(false);
  }, [type, period]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const data = (config.kind === 'alarmed' ? alarmed : drops) as (TopDropResponse | ProductResponse)[];

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: BG }} edges={['top']}>
      {/* Header */}
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 16, paddingVertical: 14 }}>
        <TouchableOpacity onPress={() => router.back()} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
          <Ionicons name="arrow-back" size={22} color="#FFFFFF" />
        </TouchableOpacity>
        <Text style={{ color: '#FFFFFF', fontSize: 18, fontFamily: 'Inter_700Bold' }}>
          {config.title}
        </Text>
      </View>

      {/* Dönem filtreleri */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={{ flexGrow: 0 }}
        contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 14, gap: 8, alignItems: 'center' }}
      >
        {PERIODS.map((p) => {
          const active = period === p.value;
          return (
            <TouchableOpacity
              key={p.value}
              onPress={() => setPeriod(p.value)}
              style={{
                paddingHorizontal: 14,
                paddingVertical: 7,
                borderRadius: 20,
                backgroundColor: active ? BRAND : CARD,
                borderWidth: 1,
                borderColor: active ? BRAND : '#334155',
              }}
            >
              <Text
                style={{
                  color: active ? '#FFFFFF' : '#94A3B8',
                  fontSize: 13,
                  fontFamily: active ? 'Inter_600SemiBold' : 'Inter_400Regular',
                }}
              >
                {p.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {/* İçerik */}
      {isLoading ? (
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
          <ActivityIndicator size="large" color={BRAND} />
        </View>
      ) : data.length === 0 ? (
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12 }}>
          <Ionicons name="analytics-outline" size={48} color="#334155" />
          <Text style={{ color: '#64748B', fontSize: 14, fontFamily: 'Inter_400Regular' }}>
            Bu dönemde veri bulunamadı
          </Text>
        </View>
      ) : (
        <FlatList
          style={{ flex: 1 }}
          data={data}
          numColumns={2}
          key="2col"
          keyExtractor={(_, i) => String(i)}
          columnWrapperStyle={{ gap: 8, paddingHorizontal: 16, marginBottom: 8 }}
          contentContainerStyle={{ paddingTop: 4, paddingBottom: 40 }}
          showsVerticalScrollIndicator={false}
          renderItem={({ item }) =>
            config.kind === 'alarmed' ? (
              <ProductCard product={item as ProductResponse} width={cardWidth} />
            ) : (
              <TopDropCard item={item as TopDropResponse} width={cardWidth} badge={type === 'top-drops' ? 'amount' : 'percent'} />
            )
          }
        />
      )}
    </SafeAreaView>
  );
}
