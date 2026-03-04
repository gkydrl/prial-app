import { View, Text, ScrollView, TouchableOpacity, Switch, RefreshControl } from 'react-native';
import { showAlert } from '@/store/alertStore';
import { useState, useEffect } from 'react';
import { homeApi } from '@/api/home';
import { Image } from 'expo-image';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { Swipeable } from 'react-native-gesture-handler';
import { router } from 'expo-router';
import { useAlarms } from '@/hooks/useAlarms';
import { useAuthStore } from '@/store/authStore';
import { SectionHeader } from '@/components/home/SectionHeader';
import { openAlarmSheet } from '@/store/alarmSheetStore';
import type { AlarmResponse, ProductResponse } from '@/types/api';
import Animated from 'react-native-reanimated';
import { useFadeIn } from '@/hooks/useFadeIn';
import { imageSource } from '@/utils/imageSource';


const BG = '#0A1628';
const CARD = '#1E293B';

// ─── Alarm Kartı ─────────────────────────────────────────────────────────────

function AlarmListCard({
  alarm,
  onToggle,
}: {
  alarm: AlarmResponse;
  onToggle: () => void;
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
    <View
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
      <TouchableOpacity activeOpacity={0.85} onPress={() => router.push(`/product/${product.id}`)}>
        <Image
          source={imageSource(product.image_url)}
          style={{ width: 70, height: 70, borderRadius: 12 }}
          contentFit="cover"
          placeholder={{ blurhash: 'L6PZfSi_.AyE_3t7t7R**0o#DgR4' }}
        />
      </TouchableOpacity>

      {/* İçerik */}
      <View style={{ flex: 1, gap: 6 }}>
        {/* Ürün adı + aksiyonlar */}
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
    </View>
  );
}

// ─── Popüler Kart ─────────────────────────────────────────────────────────────

function PopularCard({ product }: { product: ProductResponse }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
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

        {product.alarm_count > 0 && (
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 3 }}>
            <Ionicons name="pricetag-outline" size={11} color="#93C5FD" />
            <Text style={{ color: '#93C5FD', fontSize: 11, fontFamily: 'Inter_600SemiBold' }}>
              {product.alarm_count.toLocaleString('tr-TR')} talep
            </Text>
          </View>
        )}

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
          <TouchableOpacity
            onPress={() => {
              if (!isAuthenticated) {
                router.push('/(auth)/login');
                return;
              }
              openAlarmSheet({
                productId: product.id,
                storeUrl: store?.url ?? null,
                currentPrice: price,
              });
            }}
            activeOpacity={0.8}
            style={{
              width: 32, height: 32, borderRadius: 16,
              backgroundColor: '#1D4ED8',
              justifyContent: 'center', alignItems: 'center',
            }}
          >
            <Ionicons name="add" size={20} color="#FFFFFF" />
          </TouchableOpacity>
        </View>
      </View>
    </TouchableOpacity>
  );
}

// ─── Ana Ekran ────────────────────────────────────────────────────────────────

function GuestWall() {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: BG }} edges={['top']}>
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 32, gap: 16 }}>
        <Ionicons name="pricetag-outline" size={52} color="#1D4ED8" />
        <Text style={{ color: '#FFFFFF', fontSize: 18, fontFamily: 'Inter_700Bold', textAlign: 'center' }}>
          Taleplerinizi görüntüleyin
        </Text>
        <Text style={{ color: '#64748B', fontSize: 14, fontFamily: 'Inter_400Regular', textAlign: 'center', lineHeight: 20 }}>
          Talep oluşturmak ve takip etmek için giriş yapmalısınız.
        </Text>
        <TouchableOpacity
          onPress={() => router.push('/(auth)/login')}
          style={{
            backgroundColor: '#1D4ED8',
            borderRadius: 14,
            paddingVertical: 14,
            paddingHorizontal: 40,
            marginTop: 8,
          }}
        >
          <Text style={{ color: '#FFFFFF', fontSize: 15, fontFamily: 'Inter_700Bold' }}>Giriş Yap</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => router.push('/(auth)/register')}>
          <Text style={{ color: '#64748B', fontSize: 13, fontFamily: 'Inter_400Regular' }}>
            Hesabın yok mu? <Text style={{ color: '#1D4ED8', fontFamily: 'Inter_600SemiBold' }}>Kayıt ol</Text>
          </Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const INITIAL_LIMIT = 4;

export default function AlarmsScreen() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const { alarms, isLoading, updateAlarm, deleteAlarm, refresh } = useAlarms();
  const [showAll, setShowAll] = useState(false);
  const [popularProducts, setPopularProducts] = useState<ProductResponse[]>([]);

  useEffect(() => {
    homeApi.mostAlarmed(20)
      .then((res) => setPopularProducts(res.data.filter((p: ProductResponse) => p.image_url)))
      .catch(() => {});
  }, []);

  if (!isAuthenticated) return <GuestWall />;

  const handleToggle = (alarm: AlarmResponse) => {
    updateAlarm(alarm.id, { status: alarm.status === 'active' ? 'paused' : 'active' });
  };

  const handleClose = (id: string) => {
    showAlert('Talebi Kapat', 'Bu talebi kapatmak istiyor musun?', [
      { text: 'Vazgeç', style: 'cancel' },
      { text: 'Kapat', style: 'destructive', onPress: () => deleteAlarm(id) },
    ]);
  };

  // Triggered ve deleted talepler listede gösterilmez — otomatik kapandı sayılır
  const visibleAlarms = alarms.filter((a) => a.status === 'active' || a.status === 'paused');
  const displayedAlarms = showAll ? visibleAlarms : visibleAlarms.slice(0, INITIAL_LIMIT);
  const hasMore = visibleAlarms.length > INITIAL_LIMIT;
  const hasAlarms = visibleAlarms.length > 0;
  const fadeStyle = useFadeIn();

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: BG }} edges={['top']}>
      <Animated.View style={[{ flex: 1 }, fadeStyle]}>
      {/* Header */}
      <View style={{ paddingHorizontal: 16, paddingVertical: 14, flexDirection: 'row', alignItems: 'center', gap: 8 }}>
        <LinearGradient
          colors={['#0D2060', '#1D4ED8']}
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
            {displayedAlarms.map((alarm) => (
              <Swipeable
                key={alarm.id}
                overshootRight={false}
                renderRightActions={() => (
                  <TouchableOpacity
                    onPress={() => handleClose(alarm.id)}
                    style={{
                      backgroundColor: '#EF4444',
                      justifyContent: 'center',
                      alignItems: 'center',
                      width: 72,
                      borderRadius: 16,
                      marginLeft: 8,
                    }}
                  >
                    <Ionicons name="trash-outline" size={20} color="#FFFFFF" />
                    <Text style={{ color: '#FFFFFF', fontSize: 11, fontFamily: 'Inter_600SemiBold', marginTop: 4 }}>Sil</Text>
                  </TouchableOpacity>
                )}
              >
                <AlarmListCard
                  alarm={alarm}
                  onToggle={() => handleToggle(alarm)}
                />
              </Swipeable>
            ))}
            {hasMore && !showAll && (
              <TouchableOpacity
                onPress={() => setShowAll(true)}
                style={{
                  alignItems: 'center',
                  paddingVertical: 12,
                  borderRadius: 12,
                  borderWidth: 1,
                  borderColor: '#334155',
                }}
              >
                <Text style={{ color: '#1D4ED8', fontSize: 14, fontFamily: 'Inter_600SemiBold' }}>
                  Hepsini Gör ({visibleAlarms.length})
                </Text>
              </TouchableOpacity>
            )}
          </View>
        ) : (
          <View style={{ alignItems: 'center', paddingVertical: 40, paddingHorizontal: 32, gap: 12 }}>
            <Ionicons name="pricetag-outline" size={48} color="#1D4ED8" />
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
              backgroundColor: '#1D4ED8',
              justifyContent: 'center',
              alignItems: 'center',
              shadowColor: '#1D4ED8',
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

        {/* Popüler Talep Edilen Ürünler */}
        {popularProducts.length > 0 && (
          <View style={{ marginBottom: 32 }}>
            <SectionHeader
              title="Popüler Talepler"
              subtitle="En çok talep edilen ürünler"
              onSeeAll={() => router.push('/feed/most-alarmed')}
            />
            <View style={{ paddingHorizontal: 16, gap: 10 }}>
              {popularProducts.map((item) => (
                <PopularCard key={item.id} product={item} />
              ))}
            </View>
          </View>
        )}
      </ScrollView>
      </Animated.View>
    </SafeAreaView>
  );
}
