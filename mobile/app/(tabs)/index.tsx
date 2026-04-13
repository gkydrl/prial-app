import { useState, useEffect, Fragment } from 'react';
import { ScrollView, View, Text, Image, TouchableOpacity, RefreshControl, Dimensions, NativeSyntheticEvent, NativeScrollEvent } from 'react-native';
import { useNotificationStore } from '@/store/notificationStore';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SectionHeader } from '@/components/home/SectionHeader';
import { ProductCard } from '@/components/product/ProductCard';
import { OnboardingModal } from '@/components/home/OnboardingModal';
import { useAuthStore } from '@/store/authStore';
import { useHome } from '@/hooks/useHome';
import { homeApi } from '@/api/home';
import { Image as ExpoImage } from 'expo-image';
import { LinearGradient } from 'expo-linear-gradient';
import { imageSource } from '@/utils/imageSource';
import type { ProductResponse } from '@/types/api';
import Animated from 'react-native-reanimated';
import { useFadeIn } from '@/hooks/useFadeIn';

const BG = '#0A1628';

// ─── İstatistik Kartı ─────────────────────────────────────────────────────────

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

const STAT_META: { icon: IoniconName; label: string }[] = [
  { icon: 'people-outline', label: 'Kullanıcı' },
  { icon: 'flag-outline', label: 'Aktif Talep' },
  { icon: 'checkmark-circle-outline', label: 'Gerçekleşen' },
];

function StatsCard() {
  const [targets, setTargets] = useState([0, 0, 0]);
  const [counts, setCounts] = useState([0, 0, 0]);

  useEffect(() => {
    homeApi.stats().then((res) => {
      const data = res.data;
      setTargets([data.user_count, data.active_alarm_count, data.triggered_count]);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (targets.every((t) => t === 0)) return;
    const DURATION = 1500;
    const FPS = 60;
    const STEP_MS = DURATION / FPS;
    let frame = 0;
    const timer = setInterval(() => {
      frame++;
      const t = Math.min(frame / FPS, 1);
      const ease = 1 - Math.pow(1 - t, 3); // ease-out cubic
      setCounts(targets.map((target) => Math.round(target * ease)));
      if (t >= 1) clearInterval(timer);
    }, STEP_MS);
    return () => clearInterval(timer);
  }, [targets]);

  return (
    <View style={{
      marginHorizontal: 16,
      marginTop: 8,
      marginBottom: 20,
      backgroundColor: '#0F172A',
      borderRadius: 16,
      flexDirection: 'row',
      overflow: 'hidden',
    }}>
      {STAT_META.map((stat, i) => (
        <Fragment key={stat.label}>
          <View style={{ flex: 1, alignItems: 'center', paddingVertical: 14, gap: 3 }}>
            <Ionicons name={stat.icon} size={16} color="#64748B" />
            <Text style={{ color: '#FFFFFF', fontSize: 18, fontFamily: 'Inter_700Bold' }}>
              {counts[i].toLocaleString('tr-TR')}
            </Text>
            <Text style={{ color: '#64748B', fontSize: 10, fontFamily: 'Inter_400Regular' }}>
              {stat.label}
            </Text>
          </View>
          {i < STAT_META.length - 1 && (
            <View style={{ width: 1, backgroundColor: '#334155', marginVertical: 10 }} />
          )}
        </Fragment>
      ))}
    </View>
  );
}

// ─── Boş durum ────────────────────────────────────────────────────────────────

function EmptySection({ message }: { message: string }) {
  return (
    <View style={{ paddingHorizontal: 16, paddingVertical: 24, alignItems: 'center' }}>
      <Text style={{ color: '#64748B', fontSize: 13, fontFamily: 'Inter_400Regular' }}>
        {message}
      </Text>
    </View>
  );
}

// ─── Editörün Seçimleri Banner ────────────────────────────────────────────────

const SCREEN_W = Dimensions.get('window').width;
const BANNER_W = SCREEN_W - 32;

function EditorPicksBanner({ items }: { items: ProductResponse[] }) {
  const [activeIndex, setActiveIndex] = useState(0);

  const handleScroll = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const x = e.nativeEvent.contentOffset.x;
    setActiveIndex(Math.round(x / (BANNER_W + 32)));
  };

  const getBestPrice = (product: ProductResponse): number | null => {
    const prices = product.stores
      .filter(s => s.in_stock && s.current_price != null && s.store !== 'other')
      .map(s => Number(s.current_price));
    return prices.length > 0 ? Math.min(...prices) : null;
  };

  return (
    <View style={{ marginTop: 16, marginBottom: 8 }}>
      <ScrollView
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onScroll={handleScroll}
        scrollEventThrottle={16}
        decelerationRate="fast"
        snapToInterval={BANNER_W + 32}
      >
        {items.map((product, i) => {
          const price = getBestPrice(product);
          return (
            <TouchableOpacity
              key={product.id}
              activeOpacity={0.92}
              onPress={() => router.push(`/product/${product.id}`)}
              style={{ width: BANNER_W, marginHorizontal: 16 }}
            >
              <LinearGradient
                colors={i === 0 ? ['#0D2060', '#1A47C4'] : ['#1A1A2E', '#2D1B69']}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={{ borderRadius: 18, padding: 14, overflow: 'hidden' }}
              >
                <Text style={{ color: '#93C5FD', fontSize: 11, fontFamily: 'Inter_600SemiBold', marginBottom: 8 }}>
                  ✦ Editörün Seçimi
                </Text>
                <View style={{ flexDirection: 'row', gap: 14, alignItems: 'center' }}>
                  <View style={{
                    width: 80, height: 80,
                    backgroundColor: '#FFFFFF',
                    borderRadius: 12,
                    overflow: 'hidden',
                  }}>
                    <ExpoImage
                      source={imageSource(product.image_url)}
                      style={{ width: '100%', height: '100%' }}
                      contentFit="contain"
                    />
                  </View>
                  <View style={{ flex: 1, gap: 6 }}>
                    <Text
                      style={{ color: '#FFFFFF', fontSize: 14, fontFamily: 'Inter_600SemiBold', lineHeight: 19 }}
                      numberOfLines={2}
                    >
                      {product.short_title || product.title}
                    </Text>
                    {price != null && (
                      <Text style={{ color: '#FFFFFF', fontSize: 20, fontFamily: 'Inter_700Bold' }}>
                        {Math.round(price).toLocaleString('tr-TR')} ₺
                      </Text>
                    )}
                    {product.alarm_count > 0 && (
                      <Text style={{ color: '#93C5FD', fontSize: 11, fontFamily: 'Inter_400Regular' }}>
                        {product.alarm_count.toLocaleString('tr-TR')} kişi talep etti
                      </Text>
                    )}
                  </View>
                </View>
              </LinearGradient>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {items.length > 1 && (
        <View style={{ flexDirection: 'row', justifyContent: 'center', gap: 6, marginTop: 10 }}>
          {items.map((_, i) => (
            <View
              key={i}
              style={{
                width: i === activeIndex ? 18 : 6,
                height: 6,
                borderRadius: 3,
                backgroundColor: i === activeIndex ? '#1D4ED8' : '#334155',
              }}
            />
          ))}
        </View>
      )}
    </View>
  );
}

// ─── Ana Ekran ────────────────────────────────────────────────────────────────

export default function HomeScreen() {
  const hasCompletedOnboarding = useAuthStore((s) => s.hasCompletedOnboarding);
  const [modalDismissed, setModalDismissed] = useState(false);
  const { dailyDeals, aiPicks, aiWaitPicks, isLoading, refresh } = useHome();
  const unreadCount = useNotificationStore((s) => s.unreadCount);

  const showOnboarding = !hasCompletedOnboarding && !modalDismissed;
  const fadeStyle = useFadeIn();

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: BG }} edges={['top']}>
      <OnboardingModal
        visible={showOnboarding}
        onDismiss={() => setModalDismissed(true)}
      />
      <Animated.View style={[{ flex: 1 }, fadeStyle]}>
      {/* Üst bar: logo ortada, bildirim sağda */}
      <View style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16 }}>
        <View style={{ flex: 1 }} />
        <Image
          source={require('../../assets/images/logo.png')}
          style={{ height: 40, width: 180 }}
          resizeMode="contain"
        />
        <View style={{ flex: 1, alignItems: 'flex-end' }}>
          <TouchableOpacity
            onPress={() => router.push('/notifications')}
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
          >
            <View style={{ position: 'relative' }}>
              <Ionicons name="notifications-outline" size={22} color="#9CA3AF" />
              {unreadCount > 0 && (
                <View style={{
                  position: 'absolute',
                  top: -3,
                  right: -3,
                  minWidth: 16,
                  height: 16,
                  borderRadius: 8,
                  backgroundColor: '#EF4444',
                  justifyContent: 'center',
                  alignItems: 'center',
                  paddingHorizontal: 3,
                  borderWidth: 1.5,
                  borderColor: '#0A1628',
                }}>
                  <Text style={{ color: '#fff', fontSize: 9, fontFamily: 'Inter_700Bold' }}>
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </Text>
                </View>
              )}
            </View>
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView
        style={{ flex: 1 }}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl refreshing={isLoading} onRefresh={refresh} tintColor="#1D4ED8" />
        }
      >
        {/* Editörün Seçimleri Banner */}
        {aiPicks.length >= 2 && <EditorPicksBanner items={aiPicks.slice(0, 2)} />}

        {/* İstatistikler */}
        <StatsCard />

        {/* Şimdi Almaya Değer — AI Picks */}
        <View style={{ marginBottom: 24 }}>
          <SectionHeader
            title="Şimdi Almaya Değer"
            subtitle="AI önerisiyle en uygun fiyatlı ürünler"
            onSeeAll={() => router.push('/feed/ai-picks')}
          />
          {aiPicks.length > 0 ? (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={{ paddingHorizontal: 16, gap: 8 }}
            >
              {aiPicks.map((item) => (
                <ProductCard key={item.id} product={item} />
              ))}
            </ScrollView>
          ) : (
            !isLoading && <EmptySection message="Henüz öneri yok" />
          )}
        </View>

        {/* Fiyatı Düşecek — AI Wait Picks */}
        <View style={{ marginBottom: 24 }}>
          <SectionHeader
            title="Fiyatı Düşecek"
            subtitle="Beklemenizi önerdiklerimiz"
            onSeeAll={() => router.push('/feed/ai-wait-picks')}
          />
          {aiWaitPicks.length > 0 ? (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={{ paddingHorizontal: 16, gap: 8 }}
            >
              {aiWaitPicks.map((item) => (
                <ProductCard key={item.id} product={item} />
              ))}
            </ScrollView>
          ) : (
            !isLoading && <EmptySection message="Henüz öneri yok" />
          )}
        </View>

        {/* Bottom spacer */}
        <View style={{ height: 100 }} />
      </ScrollView>
      </Animated.View>
    </SafeAreaView>
  );
}
