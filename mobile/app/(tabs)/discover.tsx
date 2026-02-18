import { View, FlatList } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { SearchBar } from '@/components/discover/SearchBar';
import { CategoryCard } from '@/components/discover/CategoryCard';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useCategories } from '@/hooks/useDiscover';

export default function DiscoverScreen() {
  const { categories, isLoading } = useCategories();

  return (
    <SafeAreaView className="flex-1 bg-background" edges={['top']}>
      <View className="flex-1 px-4 pt-4 gap-4">
        {/* Arama - tıklanınca search ekranına gider */}
        <SearchBar
          value=""
          onChangeText={() => {}}
          editable={false}
          onFocus={() => router.push('/discover/search')}
        />

        {/* Kategori Grid */}
        {isLoading ? (
          <LoadingSpinner full />
        ) : (
          <FlatList
            data={categories}
            keyExtractor={(item) => item.id}
            numColumns={2}
            showsVerticalScrollIndicator={false}
            renderItem={({ item }) => <CategoryCard category={item} />}
            contentContainerStyle={{ paddingBottom: 20 }}
          />
        )}
      </View>
    </SafeAreaView>
  );
}
