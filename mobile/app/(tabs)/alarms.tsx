import { View, Text, ScrollView, TouchableOpacity, Switch, RefreshControl, Alert } from 'react-native';
import { Image } from 'expo-image';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { router } from 'expo-router';
import { useAlarms } from '@/hooks/useAlarms';
import { SectionHeader } from '@/components/home/SectionHeader';
import type { AlarmResponse, ProductResponse } from '@/types/api';
import Animated from 'react-native-reanimated';
import { useFadeIn } from '@/hooks/useFadeIn';
import { imageSource } from '@/utils/imageSource';

// ─── Mock Data ────────────────────────────────────────────────────────────────

const MOCK_POPULAR: ProductResponse[] = [
  {
    id: 'mock-1',
    title: 'Apple AirPods Pro (2. Nesil)',
    brand: 'Apple',
    description: null,
    image_url: 'https://picsum.photos/seed/airpods/300/300',
    lowest_price_ever: 3999,
    alarm_count: 1240,
    stores: [{ id: 's1', store: 'trendyol', url: '#', current_price: 4799, original_price: 5999, currency: 'TRY', discount_percent: 20, in_stock: true, last_checked_at: null }],
    created_at: '',
  },
  {
    id: 'mock-2',
    title: 'Samsung Galaxy S24 128 GB',
    brand: 'Samsung',
    description: null,
    image_url: 'https://picsum.photos/seed/galaxy/300/300',
    lowest_price_ever: 22000,
    alarm_count: 980,
    stores: [{ id: 's2', store: 'hepsiburada', url: '#', current_price: 24999, original_price: 27999, currency: 'TRY', discount_percent: 11, in_stock: true, last_checked_at: null }],
    created_at: '',
  },
  {
    id: 'mock-3',
    title: 'Sony WH-1000XM5 Kulaklık',
    brand: 'Sony',
    description: null,
    image_url: 'https://picsum.photos/seed/sony/300/300',
    lowest_price_ever: 5500,
    alarm_count: 876,
    stores: [{ id: 's3', store: 'amazon', url: '#', current_price: 6499, original_price: 7999, currency: 'TRY', discount_percent: 19, in_stock: true, last_checked_at: null }],
    created_at: '',
  },
  {
    id: 'mock-4',
    title: 'Dyson V15 Detect Süpürge',
    brand: 'Dyson',
    description: null,
    image_url: 'https://picsum.photos/seed/dyson/300/300',
    lowest_price_ever: 12000,
    alarm_count: 654,
    stores: [{ id: 's4', store: 'mediamarkt', url: '#', current_price: 14999, original_price: 17999, currency: 'TRY', discount_percent: 17, in_stock: true, last_checked_at: null }],
    created_at: '',
  },
  {
    id: 'mock-5',
    title: 'Logitech MX Master 3S Mouse',
    brand: 'Logitech',
    description: null,
    image_url: 'https://picsum.photos/seed/logitech/300/300',
    lowest_price_ever: 1800,
    alarm_count: 512,
    stores: [{ id: 's5', store: 'teknosa', url: '#', current_price: 2199, original_price: 2799, currency: 'TRY', discount_percent: 21, in_stock: true, last_checked_at: null }],
    created_at: '',
  },
  {
    id: 'mock-6',
    title: 'iPad Air M2 256 GB Wi-Fi',
    brand: 'Apple',
    description: null,
    image_url: 'https://picsum.photos/seed/ipad/300/300',
    lowest_price_ever: 18000,
    alarm_count: 490,
    stores: [{ id: 's6', store: 'vatan', url: '#', current_price: 21999, original_price: null, currency: 'TRY', discount_percent: null, in_stock: true, last_checked_at: null }],
    created_at: '',
  },
  {
    id: 'mock-7',
    title: 'Nike Air Max 270 Erkek Spor Ayakkabı',
    brand: 'Nike',
    description: null,
    image_url: 'https://picsum.photos/seed/nike/300/300',
    lowest_price_ever: 2200,
    alarm_count: 430,
    stores: [{ id: 's7', store: 'trendyol', url: '#', current_price: 2799, original_price: 3499, currency: 'TRY', discount_percent: 20, in_stock: true, last_checked_at: null }],
    created_at: '',
  },
  {
    id: 'mock-8',
    title: 'Philips Airfryer XL HD9270',
    brand: 'Philips',
    description: null,
    image_url: 'https://picsum.photos/seed/philips/300/300',
    lowest_price_ever: 3100,
    alarm_count: 388,
    stores: [{ id: 's8', store: 'hepsiburada', url: '#', current_price: 3799, original_price: 4599, currency: 'TRY', discount_percent: 17, in_stock: true, last_checked_at: null }],
    created_at: '',
  },
  {
    id: 'mock-9',
    title: 'GoPro HERO12 Black Aksiyon Kamerası',
    brand: 'GoPro',
    description: null,
    image_url: 'https://picsum.photos/seed/gopro/300/300',
    lowest_price_ever: 8500,
    alarm_count: 345,
    stores: [{ id: 's9', store: 'amazon', url: '#', current_price: 9999, original_price: 12999, currency: 'TRY', discount_percent: 23, in_stock: true, last_checked_at: null }],
    created_at: '',
  },
  {
    id: 'mock-10',
    title: 'Xiaomi Robot Süpürge S10+',
    brand: 'Xiaomi',
    description: null,
    image_url: 'https://picsum.photos/seed/xiaomi/300/300',
    lowest_price_ever: 7200,
    alarm_count: 312,
    stores: [{ id: 's10', store: 'n11', url: '#', current_price: 8499, original_price: 10999, currency: 'TRY', discount_percent: 23, in_stock: true, last_checked_at: null }],
    created_at: '',
  },
  {
    id: 'mock-11',
    title: 'Kindle Paperwhite 16 GB (11. Nesil)',
    brand: 'Amazon',
    description: null,
    image_url: 'https://picsum.photos/seed/kindle/300/300',
    lowest_price_ever: 2400,
    alarm_count: 278,
    stores: [{ id: 's11', store: 'amazon', url: '#', current_price: 2999, original_price: 3499, currency: 'TRY', discount_percent: 14, in_stock: true, last_checked_at: null }],
    created_at: '',
  },
];

const BG = '#0A1628';
const CARD = '#1E293B';

// ─── Alarm Kartı ─────────────────────────────────────────────────────────────

function AlarmListCard({
  alarm,
  onToggle,
  onDelete,
}: {
  alarm: AlarmResponse;
  onToggle: () => void;
  onDelete: () => void;
}) {
  const product = alarm.product;
  const store = alarm.product_store;
  const currentPrice = store?.current_price ?? null;
  const targetPrice = alarm.target_price;

  const currentNum = currentPrice != null ? Number(currentPrice) : null;
  const targetNum = Number(targetPrice);

  const currentStr = currentNum != null
    ? Math.round(currentNum).toLocaleString('tr-TR') + ' ₺'
    : '-';
  const targetStr = Math.round(targetNum).toLocaleString('tr-TR') + ' ₺';

  // Hedefe yakınlık: 0-1 arası (1 = hedefe ulaşıldı)
  const progress = currentNum != null && currentNum > 0
    ? Math.min(targetNum / currentNum, 1)
    : 0;

  const isActive = alarm.status === 'active';

  return (
    <TouchableOpacity
      activeOpacity={0.85}
      onLongPress={onDelete}
      style={{
        backgroundColor: CARD,
        borderRadius: 16,
        padding: 16,
        flexDirection: 'row',
        gap: 12,
        alignItems: 'center',
      }}
    >
      {/* Ürün görseli */}
      <TouchableOpacity onPress={() => router.push(`/product/${product.id}`)}>
        <Image
          source={imageSource(product.image_url)}
          style={{ width: 70, height: 70, borderRadius: 12 }}
          contentFit="cover"
          placeholder={{ blurhash: 'L6PZfSi_.AyE_3t7t7R**0o#DgR4' }}
        />
      </TouchableOpacity>

      {/* İçerik */}
      <View style={{ flex: 1, gap: 6 }}>
        {/* Ürün adı + toggle */}
        <View style={{ flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
          <Text
            style={{ color: '#FFFFFF', fontSize: 13, fontFamily: 'Inter_600SemiBold', flex: 1 }}
            numberOfLines={2}
          >
            {product.title}
          </Text>
          <Switch
            value={isActive}
            onValueChange={onToggle}
            trackColor={{ false: '#334155', true: '#1D4ED8' }}
            thumbColor="#FFFFFF"
            style={{ transform: [{ scaleX: 0.8 }, { scaleY: 0.8 }] }}
          />
        </View>

        {/* Fiyatlar */}
        <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
          <View>
            <Text style={{ color: '#64748B', fontSize: 10, fontFamily: 'Inter_400Regular' }}>Güncel</Text>
            <Text style={{ color: '#FFFFFF', fontSize: 14, fontFamily: 'Inter_700Bold' }}>{currentStr}</Text>
          </View>
          <View style={{ alignItems: 'flex-end' }}>
            <Text style={{ color: '#64748B', fontSize: 10, fontFamily: 'Inter_400Regular' }}>Talep Edilen</Text>
            <Text style={{ color: '#22C55E', fontSize: 14, fontFamily: 'Inter_700Bold' }}>{targetStr}</Text>
          </View>
        </View>

        {/* Progress bar */}
        <View style={{ height: 8, backgroundColor: '#334155', borderRadius: 4, overflow: 'hidden' }}>
          <View
            style={{
              height: '100%',
              width: `${Math.round(progress * 100)}%`,
              backgroundColor: '#22C55E',
              borderRadius: 4,
            }}
          />
        </View>
      </View>
    </TouchableOpacity>
  );
}

// ─── Popüler Kart ─────────────────────────────────────────────────────────────

function PopularCard({ product }: { product: ProductResponse }) {
  const store = product.stores[0];
  const price = store?.current_price != null ? Number(store.current_price) : null;
  const originalPrice = store?.original_price != null ? Number(store.original_price) : null;
  const discount = store?.discount_percent;

  const priceStr = price != null ? Math.round(price).toLocaleString('tr-TR') + ' ₺' : '-';
  const originalStr = originalPrice != null ? Math.round(originalPrice).toLocaleString('tr-TR') + ' ₺' : null;
  const hasDiscount = originalStr && originalPrice && price && originalPrice > price;

  return (
    <TouchableOpacity
      activeOpacity={0.85}
      onPress={() => router.push(`/product/${product.id}`)}
      style={{
        backgroundColor: CARD,
        borderRadius: 16,
        padding: 16,
        flexDirection: 'row',
        gap: 12,
        alignItems: 'center',
      }}
    >
      <Image
        source={{ uri: product.image_url ?? undefined }}
        style={{ width: 70, height: 70, borderRadius: 12 }}
        contentFit="cover"
        placeholder={{ blurhash: 'L6PZfSi_.AyE_3t7t7R**0o#DgR4' }}
      />

      <View style={{ flex: 1, gap: 6 }}>
        <Text
          style={{ color: '#FFFFFF', fontSize: 13, fontFamily: 'Inter_600SemiBold', lineHeight: 18 }}
          numberOfLines={2}
        >
          {product.title}
        </Text>

        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <View style={{ gap: 2 }}>
            {hasDiscount && (
              <Text style={{ color: '#64748B', fontSize: 12, fontFamily: 'Inter_400Regular', textDecorationLine: 'line-through' }}>
                {originalStr}
              </Text>
            )}
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
              <Text style={{ color: '#FFFFFF', fontSize: 15, fontFamily: 'Inter_700Bold' }}>
                {priceStr}
              </Text>
              {!!discount && (
                <View style={{ backgroundColor: '#22C55E20', borderRadius: 5, paddingHorizontal: 5, paddingVertical: 1 }}>
                  <Text style={{ color: '#22C55E', fontSize: 10, fontFamily: 'Inter_700Bold' }}>-%{discount}</Text>
                </View>
              )}
            </View>
          </View>
          <Ionicons name="pricetag-outline" size={20} color="#6C47FF" />
        </View>
      </View>
    </TouchableOpacity>
  );
}

// ─── Ana Ekran ────────────────────────────────────────────────────────────────

export default function AlarmsScreen() {
  const { alarms, isLoading, updateAlarm, deleteAlarm, refresh } = useAlarms();

  const handleToggle = (alarm: AlarmResponse) => {
    updateAlarm(alarm.id, { status: alarm.status === 'active' ? 'paused' : 'active' });
  };

  const handleDelete = (id: string) => {
    Alert.alert('Talebi Sil', 'Bu talebi silmek istiyor musun?', [
      { text: 'Vazgeç', style: 'cancel' },
      { text: 'Sil', style: 'destructive', onPress: () => deleteAlarm(id) },
    ]);
  };

  const hasAlarms = alarms.length > 0;
  const fadeStyle = useFadeIn();

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: BG }} edges={['top']}>
      <Animated.View style={[{ flex: 1 }, fadeStyle]}>
      {/* Header */}
      <View style={{ paddingHorizontal: 16, paddingVertical: 14, flexDirection: 'row', alignItems: 'center', gap: 8 }}>
        <LinearGradient
          colors={['#1D4ED8', '#059669']}
          start={{ x: 0, y: 0 }}
          end={{ x: 0, y: 1 }}
          style={{ width: 3, height: 40, borderRadius: 2 }}
        />
        <Text style={{ color: '#FFFFFF', fontSize: 20, fontFamily: 'Inter_700Bold' }}>Taleplerim</Text>
      </View>

      <ScrollView
        style={{ flex: 1 }}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl refreshing={isLoading} onRefresh={refresh} tintColor="#1D4ED8" />
        }
      >
        {/* Alarm listesi veya boş durum */}
        {hasAlarms ? (
          <View style={{ paddingHorizontal: 16, gap: 10, marginBottom: 8 }}>
            {alarms.map((alarm) => (
              <AlarmListCard
                key={alarm.id}
                alarm={alarm}
                onToggle={() => handleToggle(alarm)}
                onDelete={() => handleDelete(alarm.id)}
              />
            ))}
          </View>
        ) : (
          <View style={{ alignItems: 'center', paddingVertical: 40, paddingHorizontal: 32, gap: 12 }}>
            <Ionicons name="pricetag-outline" size={48} color="#6C47FF" />
            <Text style={{ color: '#FFFFFF', fontSize: 16, fontFamily: 'Inter_600SemiBold', textAlign: 'center' }}>
              Henüz aktif talebin yok
            </Text>
            <Text style={{ color: '#64748B', fontSize: 13, fontFamily: 'Inter_400Regular', textAlign: 'center' }}>
              Ürün fiyatları düştüğünde seni haberdar edelim
            </Text>
          </View>
        )}

        {/* Yeni talep oluştur butonu */}
        <View style={{ alignItems: 'center', paddingVertical: 20 }}>
          <TouchableOpacity
            onPress={() => router.push('/alarm-search')}
            activeOpacity={0.8}
            style={{
              width: 56,
              height: 56,
              borderRadius: 28,
              backgroundColor: '#6C47FF',
              justifyContent: 'center',
              alignItems: 'center',
              shadowColor: '#6C47FF',
              shadowOffset: { width: 0, height: 4 },
              shadowOpacity: 0.45,
              shadowRadius: 10,
              elevation: 8,
            }}
          >
            <Ionicons name="add" size={28} color="#FFFFFF" />
          </TouchableOpacity>
          <Text style={{ color: '#64748B', fontSize: 11, fontFamily: 'Inter_400Regular', marginTop: 6 }}>
            Yeni talep oluştur
          </Text>
        </View>

        {/* Popüler Takipler */}
        <View style={{ marginBottom: 32 }}>
          <SectionHeader
            title="Popüler Talepler"
            subtitle="En çok talep edilen ürünler"
            onSeeAll={() => router.push('/(tabs)/discover')}
          />
          <View style={{ paddingHorizontal: 16, gap: 10 }}>
            {MOCK_POPULAR.map((item) => (
              <PopularCard key={item.id} product={item} />
            ))}
          </View>
        </View>
      </ScrollView>
      </Animated.View>
    </SafeAreaView>
  );
}
