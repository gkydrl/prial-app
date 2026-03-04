import { View, Text, FlatList, TouchableOpacity, useWindowDimensions } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '@/constants/colors';
import { useCategoryProducts } from '@/hooks/useDiscover';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { ProductCard } from '@/components/product/ProductCard';

export default function CategoryProductsScreen() {
  const { slug, title } = useLocalSearchParams<{ slug: string; title?: string }>();
  const { products, isLoading, hasMore, loadMore } = useCategoryProducts(slug);
  const { width } = useWindowDimensions();
  const cardWidth = (width - 16 * 2 - 10) / 2;

  const displayTitle = title ?? slug.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.background }} edges={['top']}>
      {/* Header */}
      <View style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingTop: 16, paddingBottom: 12, gap: 12 }}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={24} color={Colors.textPrimary} />
        </TouchableOpacity>
        <Text style={{ color: '#FFFFFF', fontSize: 20, fontFamily: 'Inter_700Bold', flex: 1 }} numberOfLines={1}>
          {displayTitle}
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
          renderItem={({ item }) => <ProductCard product={item} width={cardWidth} />}
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
