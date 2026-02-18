import React from 'react';
import { TouchableOpacity, Text, View } from 'react-native';
import { Image } from 'expo-image';
import { router } from 'expo-router';
import { Card } from '@/components/ui/Card';
import { PriceText } from '@/components/ui/PriceText';
import { DiscountBadge } from '@/components/ui/Badge';
import type { ProductResponse, ProductStoreResponse } from '@/types/api';

interface ProductCardProps {
  product: ProductResponse;
  store?: ProductStoreResponse;
}

export function ProductCard({ product, store }: ProductCardProps) {
  const activeStore = store ?? product.stores[0];

  return (
    <TouchableOpacity
      onPress={() => router.push(`/product/${product.id}`)}
      activeOpacity={0.85}
    >
      <Card className="w-44">
        <Image
          source={{ uri: product.image_url ?? undefined }}
          style={{ width: '100%', height: 140 }}
          contentFit="cover"
          placeholder={{ blurhash: 'L6PZfSi_.AyE_3t7t7R**0o#DgR4' }}
        />
        <View className="p-3 gap-1">
          {activeStore?.discount_percent && (
            <DiscountBadge percent={activeStore.discount_percent} />
          )}
          <Text className="text-white text-sm font-medium" numberOfLines={2}>
            {product.title}
          </Text>
          <PriceText value={activeStore?.current_price} size="md" />
          {activeStore?.original_price && activeStore.original_price !== activeStore.current_price && (
            <PriceText value={activeStore.original_price} size="sm" dimmed />
          )}
        </View>
      </Card>
    </TouchableOpacity>
  );
}
