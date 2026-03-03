import { useState, useEffect, Fragment } from 'react';
import { ScrollView, View, Text, Image, TouchableOpacity, RefreshControl } from 'react-native';
import { useNotificationStore } from '@/store/notificationStore';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SectionHeader } from '@/components/home/SectionHeader';
import { TopDropCard } from '@/components/home/TopDropCard';
import { ProductCard } from '@/components/product/ProductCard';
import { DailyBanner } from '@/components/home/DailyBanner';
import { OnboardingModal } from '@/components/home/OnboardingModal';
import { useAuthStore } from '@/store/authStore';
import { useHome } from '@/hooks/useHome';
import Animated from 'react-native-reanimated';
import { useFadeIn } from '@/hooks/useFadeIn';

const BG = '#0A1628';

// ─── İstatistik Kartı ─────────────────────────────────────────────────────────

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

const STATS: { icon: IoniconName; target: number; label: string }[] = [
  { icon: 'people-outline', target: 12847, label: 'Kullanıcı' },
  { icon: 'flag-outline', target: 48392, label: 'Aktif Talep' },
  { icon: 'checkmark-circle-outline', target: 3241, label: 'Gerçekleşen' },
];

function StatsCard() {
  const [counts, setCounts] = useState([0, 0, 0]);

  useEffect(() => {
    const DURATION = 1500;
    const FPS = 60;
    const STEP_MS = DURATION / FPS;
    let frame = 0;
    const timer = setInterval(() => {
      frame++;
      const t = Math.min(frame / FPS, 1);
      const ease = 1 - Math.pow(1 - t, 3); // ease-out cubic
      setCounts(STATS.map((s) => Math.round(s.target * ease)));
      if (t >= 1) clearInterval(timer);
    }, STEP_MS);
    return () => clearInterval(timer);
  }, []);

  return (
    <View style={{
      marginHorizontal: 16,
      marginTop: 16,
      marginBottom: 20,
      backgroundColor: '#0F172A',
      borderRadius: 16,
      flexDirection: 'row',
      overflow: 'hidden',
    }}>
      {STATS.map((stat, i) => (
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
          {i < STATS.length - 1 && (
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

// ─── Ana Ekran ────────────────────────────────────────────────────────────────

export default function HomeScreen() {
  const hasCompletedOnboarding = useAuthStore((s) => s.hasCompletedOnboarding);
  const [modalDismissed, setModalDismissed] = useState(false);
  const { dailyDeals, topDrops, mostAlarmed, isLoading, refresh } = useHome();
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
          <RefreshControl refreshing={isLoading} onRefresh={refresh} tintColor="#6C47FF" />
        }
      >
        {/* Günlük Banner */}
        {topDrops.length > 0 && <DailyBanner items={topDrops} />}

        {/* İstatistikler */}
        <StatsCard />

        {/* Bugünün Fırsatları */}
        <View style={{ marginBottom: 24 }}>
          <SectionHeader
            title="Bugünün Fırsatları"
            subtitle="En çok oransal düşüş yaşayan ürünler"
            onSeeAll={() => router.push('/feed/daily-deals')}
          />
          {dailyDeals.length > 0 ? (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={{ paddingHorizontal: 16, gap: 8 }}
            >
              {dailyDeals.map((item, i) => (
                <TopDropCard key={i} item={item} badge="percent" />
              ))}
            </ScrollView>
          ) : (
            !isLoading && <EmptySection message="Henüz indirimli ürün yok" />
          )}
        </View>

        {/* En Çok Düşenler */}
        <View style={{ marginBottom: 24 }}>
          <SectionHeader
            title="En Çok Düşenler"
            subtitle="En çok fiyat düşüşü yaşanan ürünler"
            onSeeAll={() => router.push('/feed/top-drops')}
          />
          {topDrops.length > 0 ? (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={{ paddingHorizontal: 16, gap: 8 }}
            >
              {topDrops.map((item, i) => (
                <TopDropCard key={i} item={item} badge="amount" />
              ))}
            </ScrollView>
          ) : (
            !isLoading && <EmptySection message="Fiyat düşüşü kaydedilmedi" />
          )}
        </View>

        {/* En Çok Talep Edilen */}
        <View style={{ marginBottom: 100 }}>
          <SectionHeader
            title="En Çok Talep Edilen"
            subtitle="Topluluğun en çok beklediği ürünler"
            onSeeAll={() => router.push('/feed/most-alarmed')}
          />
          {mostAlarmed.length > 0 ? (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={{ paddingHorizontal: 16, gap: 8 }}
            >
              {mostAlarmed.map((item) => (
                <ProductCard key={item.id} product={item} />
              ))}
            </ScrollView>
          ) : (
            !isLoading && <EmptySection message="Henüz talep edilen ürün yok" />
          )}
        </View>
      </ScrollView>
      </Animated.View>
    </SafeAreaView>
  );
}
