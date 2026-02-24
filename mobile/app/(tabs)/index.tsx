import { useState } from 'react';
import { ScrollView, View, Text, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { useHome } from '@/hooks/useHome';
import { SectionHeader } from '@/components/home/SectionHeader';
import { DealCard } from '@/components/home/DealCard';
import { TopDropCard } from '@/components/home/TopDropCard';
import { ProductCard } from '@/components/product/ProductCard';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { OnboardingModal } from '@/components/home/OnboardingModal';
import { useAuthStore } from '@/store/authStore';

const BG = '#080810';

export default function HomeScreen() {
  const { dailyDeals, topDrops, mostAlarmed, isLoading, refresh } = useHome();
  const hasCompletedOnboarding = useAuthStore((s) => s.hasCompletedOnboarding);
  const [modalDismissed, setModalDismissed] = useState(false);

  const showOnboarding = !hasCompletedOnboarding && !modalDismissed;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: BG }} edges={['top']}>
      <OnboardingModal
        visible={showOnboarding}
        onDismiss={() => setModalDismissed(true)}
      />

      <ScrollView
        style={{ flex: 1 }}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={isLoading}
            onRefresh={refresh}
            tintColor="#6C47FF"
          />
        }
      >
        {/* Header */}
        <View style={{ paddingHorizontal: 16, paddingTop: 16, paddingBottom: 24 }}>
          <Text style={{ color: '#FFFFFF', fontSize: 28, fontFamily: 'Inter_700Bold' }}>
            Prial
          </Text>
          <Text style={{ color: '#6B7280', fontSize: 13, fontFamily: 'Inter_400Regular', marginTop: 4 }}>
            Fiyatlar düşüyor, alarm kuruyoruz
          </Text>
        </View>

        {/* Günün İndirimleri */}
        <View style={{ marginBottom: 24 }}>
          <SectionHeader
            title="Günün İndirimleri"
            subtitle="Bugün en çok indirim yapılan ürünler"
            onSeeAll={() => router.push('/(tabs)/discover')}
          />
          {isLoading && dailyDeals.length === 0 ? (
            <View style={{ height: 220, alignItems: 'center', justifyContent: 'center' }}>
              <LoadingSpinner />
            </View>
          ) : (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={{ paddingHorizontal: 16, gap: 12 }}
            >
              {dailyDeals.map((item) => (
                <DealCard key={item.id} store={item} />
              ))}
            </ScrollView>
          )}
        </View>

        {/* En Çok Düşenler */}
        <View style={{ marginBottom: 24 }}>
          <SectionHeader
            title="En Çok Düşenler"
            subtitle="Son 24 saatte fiyatı en çok gerileyen ürünler"
            onSeeAll={() => router.push('/(tabs)/discover')}
          />
          {isLoading && topDrops.length === 0 ? (
            <View style={{ height: 220, alignItems: 'center', justifyContent: 'center' }}>
              <LoadingSpinner />
            </View>
          ) : (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={{ paddingHorizontal: 16, gap: 12 }}
            >
              {topDrops.map((item, i) => (
                <TopDropCard key={i} item={item} />
              ))}
            </ScrollView>
          )}
        </View>

        {/* En Çok Aranan */}
        <View style={{ marginBottom: 32 }}>
          <SectionHeader
            title="En Çok Aranan"
            subtitle="Kullanıcıların alarm kurduğu popüler ürünler"
            onSeeAll={() => router.push('/(tabs)/discover')}
          />
          {isLoading && mostAlarmed.length === 0 ? (
            <View style={{ height: 220, alignItems: 'center', justifyContent: 'center' }}>
              <LoadingSpinner />
            </View>
          ) : (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={{ paddingHorizontal: 16, gap: 12 }}
            >
              {mostAlarmed.map((item) => (
                <ProductCard key={item.id} product={item} />
              ))}
            </ScrollView>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
