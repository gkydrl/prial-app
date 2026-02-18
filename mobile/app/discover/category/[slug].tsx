import { View, Text, FlatList, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '@/constants/colors';
import { useCategoryProducts } from '@/hooks/useDiscover';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { Card } from '@/components/ui/Card';
import { PriceText } from '@/components/ui/PriceText';
import { DiscountBadge } from '@/components/ui/Badge';
import type { ProductStoreResponse } from '@/types/api';

function StoreProductCard({ store }: { store: ProductStoreResponse }) {
  return (
    <Card className="flex-1 p-3 gap-2">
      <View className="h-24 bg-surface rounded-xl items-center justify-center">
        <Text className="text-muted text-xs">{store.store}</Text>
      </View>
      {store.discount_percent && <DiscountBadge percent={store.discount_percent} />}
      <PriceText value={store.current_price} size="md" />
      {store.original_price && store.original_price !== store.current_price && (
        <PriceText value={store.original_price} size="sm" dimmed />
      )}
    </Card>
  );
}

export default function CategoryProductsScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const { products, isLoading, hasMore, loadMore } = useCategoryProducts(slug);

  return (
    <SafeAreaView className="flex-1 bg-background" edges={['top']}>
      {/* Header */}
      <View className="flex-row items-center px-4 pt-4 pb-3 gap-3">
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={24} color={Colors.textPrimary} />
        </TouchableOpacity>
        <Text className="text-white text-xl font-bold flex-1" numberOfLines={1}>
          {slug.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
        </Text>
      </View>

      {isLoading && products.length === 0 ? (
        <LoadingSpinner full />
      ) : (
        <FlatList
          data={products}
          keyExtractor={(item) => item.id}
          numColumns={2}
          columnWrapperStyle={{ gap: 10, paddingHorizontal: 16 }}
          contentContainerStyle={{ gap: 10, paddingBottom: 20 }}
          showsVerticalScrollIndicator={false}
          onEndReached={loadMore}
          onEndReachedThreshold={0.3}
          ListFooterComponent={hasMore && isLoading ? <LoadingSpinner /> : null}
          renderItem={({ item }) => <StoreProductCard store={item} />}
          ListEmptyComponent={
            <EmptyState
              icon="pricetag-outline"
              title="Ürün bulunamadı"
              description="Bu kategoride henüz ürün eklenmemiş"
            />
          }
        />
      )}
    </SafeAreaView>
  );
}
