import { useRef } from 'react';
import { ScrollView, View, Text, TouchableOpacity, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { Image } from 'expo-image';
import type BottomSheet from '@gorhom/bottom-sheet';
import { Ionicons } from '@expo/vector-icons';
import { useProduct } from '@/hooks/useProduct';
import { PriceText } from '@/components/ui/PriceText';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { StoreRow } from '@/components/product/StoreRow';
import { OutOfStockBanner } from '@/components/product/OutOfStockBanner';
import { PriceHistoryChart } from '@/components/product/PriceHistoryChart';
import { AlarmSetupSheet } from '@/components/product/AlarmSetupSheet';
import { Colors } from '@/constants/colors';

export default function ProductDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { product, history, isLoading, error } = useProduct(id);
  const alarmSheetRef = useRef<BottomSheet>(null);

  if (isLoading) return <LoadingSpinner full />;
  if (error || !product) {
    return (
      <View className="flex-1 items-center justify-center bg-background">
        <Text className="text-white">{error ?? 'Ürün bulunamadı'}</Text>
      </View>
    );
  }

  const allOutOfStock = product.stores.every((s) => !s.in_stock);
  const lowestStore = product.stores.reduce<typeof product.stores[0] | null>((min, s) => {
    if (!s.current_price) return min;
    if (!min || !min.current_price) return s;
    return s.current_price < min.current_price ? s : min;
  }, null);

  return (
    <SafeAreaView className="flex-1 bg-background" edges={['top']}>
      {/* Back button */}
      <TouchableOpacity
        className="absolute top-12 left-4 z-10 bg-black/40 rounded-full p-2"
        onPress={() => router.back()}
      >
        <Ionicons name="arrow-back" size={20} color="white" />
      </TouchableOpacity>

      <ScrollView className="flex-1" showsVerticalScrollIndicator={false}>
        {/* Ürün görseli */}
        <Image
          source={{ uri: product.image_url ?? undefined }}
          style={{ width: '100%', height: 280 }}
          contentFit="cover"
          placeholder={{ blurhash: 'L6PZfSi_.AyE_3t7t7R**0o#DgR4' }}
        />

        {/* Stok dışı banner */}
        {allOutOfStock && <OutOfStockBanner />}

        <View className="px-4 pt-4 gap-5">
          {/* Başlık & Fiyat */}
          <View className="gap-2">
            {product.brand && (
              <Text className="text-muted text-sm font-medium uppercase tracking-wider">
                {product.brand}
              </Text>
            )}
            <Text className="text-white text-xl font-bold leading-7">{product.title}</Text>
            <View className="flex-row items-baseline gap-3">
              <PriceText value={lowestStore?.current_price} size="xl" />
              {lowestStore?.original_price && lowestStore.original_price !== lowestStore.current_price && (
                <PriceText value={lowestStore.original_price} size="lg" dimmed />
              )}
            </View>
            {product.lowest_price_ever && (
              <Text className="text-xs text-success">
                En düşük fiyat: {new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' }).format(product.lowest_price_ever)}
              </Text>
            )}
          </View>

          {/* Fiyat Geçmişi Grafiği */}
          <View className="gap-3">
            <Text className="text-white text-base font-semibold">Fiyat Geçmişi</Text>
            <PriceHistoryChart data={history} />
          </View>

          {/* Mağaza Karşılaştırma */}
          <View className="gap-2">
            <Text className="text-white text-base font-semibold">
              Mağazalar ({product.stores.length})
            </Text>
            <View>
              {product.stores.map((store) => (
                <StoreRow key={store.id} store={store} />
              ))}
            </View>
          </View>

          {/* Boşluk (alarm butonu için) */}
          <View className="h-24" />
        </View>
      </ScrollView>

      {/* Alarm Kur butonu */}
      <View className="absolute bottom-0 left-0 right-0 px-4 pb-6 pt-2 bg-background/95">
        <TouchableOpacity
          className="bg-brand rounded-2xl py-4 items-center flex-row justify-center gap-2"
          onPress={() => alarmSheetRef.current?.expand()}
        >
          <Ionicons name="notifications" size={20} color="white" />
          <Text className="text-white font-bold text-base">Fiyat Alarmı Kur</Text>
        </TouchableOpacity>
      </View>

      {/* Alarm kurma sheet */}
      <AlarmSetupSheet
        productId={product.id}
        currentPrice={lowestStore?.current_price ?? null}
        sheetRef={alarmSheetRef}
      />
    </SafeAreaView>
  );
}
