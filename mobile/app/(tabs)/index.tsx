import { useState } from 'react';
import { ScrollView, View, Text, FlatList, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useHome } from '@/hooks/useHome';
import { SectionHeader } from '@/components/home/SectionHeader';
import { DealCard } from '@/components/home/DealCard';
import { TopDropCard } from '@/components/home/TopDropCard';
import { ProductCard } from '@/components/product/ProductCard';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { OnboardingModal } from '@/components/home/OnboardingModal';
import { useAuthStore } from '@/store/authStore';

export default function HomeScreen() {
  const { dailyDeals, topDrops, mostAlarmed, isLoading, refresh } = useHome();
  const hasCompletedOnboarding = useAuthStore((s) => s.hasCompletedOnboarding);
  const [modalDismissed, setModalDismissed] = useState(false);

  const showOnboarding = !hasCompletedOnboarding && !modalDismissed;

  return (
    <SafeAreaView className="flex-1 bg-background" edges={['top']}>
      <OnboardingModal
        visible={showOnboarding}
        onDismiss={() => setModalDismissed(true)}
      />
      <ScrollView
        className="flex-1"
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={isLoading} onRefresh={refresh} tintColor="#6C47FF" />}
      >
        {/* Header */}
        <View className="px-4 pt-4 pb-6">
          <Text className="text-3xl font-bold text-white">Prial</Text>
          <Text className="text-muted text-sm mt-1">Fiyatlar düşüyor, alarm kuruyoruz 🔔</Text>
        </View>

        {/* Günün İndirimleri */}
        <View className="mb-6">
          <SectionHeader title="Günün İndirimleri" />
          {isLoading && dailyDeals.length === 0 ? (
            <View className="h-32 items-center justify-center">
              <LoadingSpinner />
            </View>
          ) : (
            <FlatList
              data={dailyDeals}
              horizontal
              showsHorizontalScrollIndicator={false}
              keyExtractor={(item) => item.id}
              contentContainerStyle={{ paddingHorizontal: 16, gap: 12 }}
              renderItem={({ item }) => <DealCard store={item} />}
            />
          )}
        </View>

        {/* En Çok Düşenler */}
        <View className="mb-6">
          <SectionHeader title="En Çok Düşenler" />
          {isLoading && topDrops.length === 0 ? (
            <View className="h-32 items-center justify-center">
              <LoadingSpinner />
            </View>
          ) : (
            <FlatList
              data={topDrops}
              horizontal
              showsHorizontalScrollIndicator={false}
              keyExtractor={(_, i) => String(i)}
              contentContainerStyle={{ paddingHorizontal: 16, gap: 12 }}
              renderItem={({ item }) => <TopDropCard item={item} />}
            />
          )}
        </View>

        {/* En Çok Alarmlı */}
        <View className="mb-6">
          <SectionHeader title="En Çok Aranan" />
          {isLoading && mostAlarmed.length === 0 ? (
            <View className="h-32 items-center justify-center">
              <LoadingSpinner />
            </View>
          ) : (
            <FlatList
              data={mostAlarmed}
              horizontal
              showsHorizontalScrollIndicator={false}
              keyExtractor={(item) => item.id}
              contentContainerStyle={{ paddingHorizontal: 16, gap: 12 }}
              renderItem={({ item }) => <ProductCard product={item} />}
            />
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
