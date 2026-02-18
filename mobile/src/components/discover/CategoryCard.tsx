import React from 'react';
import { TouchableOpacity, Text, View } from 'react-native';
import { Image } from 'expo-image';
import { router } from 'expo-router';
import type { CategoryResponse } from '@/types/api';

export function CategoryCard({ category }: { category: CategoryResponse }) {
  return (
    <TouchableOpacity
      className="flex-1 m-1.5 rounded-2xl overflow-hidden bg-card"
      style={{ minHeight: 100 }}
      onPress={() => router.push(`/discover/category/${category.slug}`)}
      activeOpacity={0.85}
    >
      {category.image_url ? (
        <Image
          source={{ uri: category.image_url }}
          style={{ width: '100%', height: 70 }}
          contentFit="cover"
        />
      ) : (
        <View className="h-[70px] bg-surface items-center justify-center">
          <Text className="text-4xl">🏷️</Text>
        </View>
      )}
      <View className="p-2">
        <Text className="text-white text-sm font-medium text-center" numberOfLines={2}>
          {category.name}
        </Text>
      </View>
    </TouchableOpacity>
  );
}
