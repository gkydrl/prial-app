import { useState } from 'react';
import { ScrollView, View, Text, Image, TouchableOpacity, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SectionHeader } from '@/components/home/SectionHeader';
import { TopDropCard } from '@/components/home/TopDropCard';
import { ProductCard } from '@/components/product/ProductCard';
import { OnboardingModal } from '@/components/home/OnboardingModal';
import { useAuthStore } from '@/store/authStore';
import { useHome } from '@/hooks/useHome';

const BG = '#0A1628';

// ─── İstatistik Kutusu ────────────────────────────────────────────────────────

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

function StatBox({ icon, value, label }: { icon: IoniconName; value: string; label: string }) {
  return (
    <View style={{
      flex: 1,
      backgroundColor: '#1E293B',
      borderRadius: 12,
      padding: 12,
      alignItems: 'center',
      gap: 4,
    }}>
      <Ionicons name={icon} size={18} color="#64748B" />
      <Text style={{ color: '#FFFFFF', fontSize: 24, fontFamily: 'Inter_700Bold' }}>{value}</Text>
      <Text style={{ color: '#64748B', fontSize: 11, fontFamily: 'Inter_400Regular' }}>{label}</Text>
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

  const showOnboarding = !hasCompletedOnboarding && !modalDismissed;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: BG }} edges={['top']}>
      <OnboardingModal
        visible={showOnboarding}
        onDismiss={() => setModalDismissed(true)}
      />

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
            onPress={() => router.push('/(tabs)/alarms')}
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
          >
            <Ionicons name="notifications-outline" size={22} color="#9CA3AF" />
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
        {/* İstatistikler */}
        <View style={{ flexDirection: 'row', paddingHorizontal: 16, gap: 8, marginTop: 12, marginBottom: 28 }}>
          <StatBox icon="people-outline" value="12.847" label="Kullanıcı" />
          <StatBox icon="flag-outline" value="48.392" label="Aktif Talep" />
          <StatBox icon="checkmark-circle-outline" value="3.241" label="Gerçekleşen" />
        </View>

        {/* Bugünün Fırsatları */}
        <View style={{ marginBottom: 24 }}>
          <SectionHeader
            title="Bugünün Fırsatları"
            subtitle="En yüksek indirimli ürünler"
            onSeeAll={() => router.push('/(tabs)/discover')}
          />
          {dailyDeals.length > 0 ? (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={{ paddingHorizontal: 16, gap: 12 }}
            >
              {dailyDeals.map((item) => (
                <ProductCard key={item.id} product={item} />
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
            subtitle="Son 24 saatte fiyatı en çok gerileyen ürünler"
            onSeeAll={() => router.push('/(tabs)/discover')}
          />
          {topDrops.length > 0 ? (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={{ paddingHorizontal: 16, gap: 12 }}
            >
              {topDrops.map((item, i) => (
                <TopDropCard key={i} item={item} />
              ))}
            </ScrollView>
          ) : (
            !isLoading && <EmptySection message="Son 24 saatte fiyat düşüşü kaydedilmedi" />
          )}
        </View>

        {/* En Çok Talep Edilen */}
        <View style={{ marginBottom: 32 }}>
          <SectionHeader
            title="En Çok Talep Edilen"
            subtitle="Topluluğun en çok beklediği ürünler"
            onSeeAll={() => router.push('/(tabs)/discover')}
          />
          {mostAlarmed.length > 0 ? (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={{ paddingHorizontal: 16, gap: 12 }}
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
    </SafeAreaView>
  );
}
