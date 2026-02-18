import { View, FlatList, Text } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { SearchBar } from '@/components/discover/SearchBar';
import { ProductCard } from '@/components/product/ProductCard';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { useSearch } from '@/hooks/useDiscover';

export default function SearchScreen() {
  const { query, setQuery, results, isLoading } = useSearch();

  return (
    <SafeAreaView className="flex-1 bg-background" edges={['top']}>
      <View className="flex-1 px-4 pt-4 gap-4">
        {/* Arama kutusu (otomatik focus) */}
        <View className="flex-row items-center gap-3">
          <View className="flex-1">
            <SearchBar value={query} onChangeText={setQuery} />
          </View>
          <Text className="text-brand font-medium" onPress={() => router.back()}>
            İptal
          </Text>
        </View>

        {/* Sonuçlar */}
        {isLoading ? (
          <LoadingSpinner full />
        ) : query.length < 2 ? (
          <EmptyState
            icon="search-outline"
            title="Ürün ara"
            description="Arama yapmak için en az 2 karakter girin"
          />
        ) : results.length === 0 ? (
          <EmptyState
            icon="file-tray-outline"
            title="Sonuç bulunamadı"
            description={`"${query}" için ürün bulunamadı`}
          />
        ) : (
          <FlatList
            data={results}
            keyExtractor={(item) => item.id}
            numColumns={2}
            columnWrapperStyle={{ gap: 10 }}
            contentContainerStyle={{ gap: 10, paddingBottom: 20 }}
            showsVerticalScrollIndicator={false}
            renderItem={({ item }) => <ProductCard product={item} />}
          />
        )}
      </View>
    </SafeAreaView>
  );
}
