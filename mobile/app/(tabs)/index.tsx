import { useState } from 'react';
import { ScrollView, View, Image, TouchableOpacity, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useHome } from '@/hooks/useHome';
import { SectionHeader } from '@/components/home/SectionHeader';
import { DealCard } from '@/components/home/DealCard';
import { TopDropCard } from '@/components/home/TopDropCard';
import { ProductCard } from '@/components/product/ProductCard';
import { CardSkeletonRow } from '@/components/ui/CardSkeleton';
import { OnboardingModal } from '@/components/home/OnboardingModal';
import { useAuthStore } from '@/store/authStore';

const BG = '#0A1628';

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

      {/* Üst bar: logo + bildirim ikonu */}
      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingHorizontal: 16,
          paddingVertical: 10,
        }}
      >
        <Image
          source={require('../../../assets/images/logo.png')}
          style={{ width: 90, height: 36 }}
          resizeMode="contain"
        />
        <TouchableOpacity
          onPress={() => router.push('/(tabs)/alarms')}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <Ionicons name="notifications-outline" size={22} color="#9CA3AF" />
        </TouchableOpacity>
      </View>

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
        {/* Günün İndirimleri */}
        <View style={{ marginBottom: 24 }}>
          <SectionHeader
            title="Günün İndirimleri"
            subtitle="Bugün en çok indirim yapılan ürünler"
            onSeeAll={() => router.push('/(tabs)/discover')}
          />
          {isLoading ? (
            <CardSkeletonRow count={3} />
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
          {isLoading ? (
            <CardSkeletonRow count={3} />
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
          {isLoading ? (
            <CardSkeletonRow count={3} />
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
