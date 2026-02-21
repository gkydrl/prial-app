import { useState } from 'react';
import { View, FlatList, ScrollView, TouchableOpacity, Text } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { SearchBar } from '@/components/discover/SearchBar';
import { CategoryCard } from '@/components/discover/CategoryCard';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useCategories } from '@/hooks/useDiscover';

const TIME_FILTERS = ['1G', '7G', '30G', '3A'];
const SORT_FILTERS = ['En Çok Düşen', 'En Ucuz', 'En Pahalı', 'En Çok Alarmlı'];

export default function DiscoverScreen() {
  const { categories, isLoading } = useCategories();
  const [activeTime, setActiveTime] = useState('1G');
  const [activeSort, setActiveSort] = useState('En Çok Düşen');

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

        {/* Zaman Filtresi */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={{ gap: 8 }}
        >
          {TIME_FILTERS.map((filter) => (
            <TouchableOpacity
              key={filter}
              onPress={() => setActiveTime(filter)}
              style={{
                backgroundColor: activeTime === filter ? '#6C47FF' : 'transparent',
                borderWidth: 1,
                borderColor: activeTime === filter ? '#6C47FF' : '#D1D5DB',
                borderRadius: 20,
                paddingHorizontal: 16,
                paddingVertical: 8,
              }}
            >
              <Text
                style={{
                  color: activeTime === filter ? '#FFFFFF' : '#6B7280',
                  fontWeight: '500',
                  fontSize: 14,
                }}
              >
                {filter}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* Sıralama Filtresi */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={{ gap: 8 }}
        >
          {SORT_FILTERS.map((filter) => (
            <TouchableOpacity
              key={filter}
              onPress={() => setActiveSort(filter)}
              style={{
                backgroundColor: activeSort === filter ? '#6C47FF' : 'transparent',
                borderWidth: 1,
                borderColor: activeSort === filter ? '#6C47FF' : '#D1D5DB',
                borderRadius: 20,
                paddingHorizontal: 16,
                paddingVertical: 8,
              }}
            >
              <Text
                style={{
                  color: activeSort === filter ? '#FFFFFF' : '#6B7280',
                  fontWeight: '500',
                  fontSize: 14,
                }}
              >
                {filter}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

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
