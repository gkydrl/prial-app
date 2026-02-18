import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { Image } from 'expo-image';
import { router } from 'expo-router';
import { Card } from '@/components/ui/Card';
import { PriceText } from '@/components/ui/PriceText';
import { DiscountBadge } from '@/components/ui/Badge';
import type { ProductStoreResponse } from '@/types/api';

const STORE_LABELS: Record<string, string> = {
  trendyol: 'Trendyol', hepsiburada: 'Hepsiburada', amazon: 'Amazon',
  n11: 'N11', ciceksepeti: 'Çiçeksepeti', mediamarkt: 'MediaMarkt',
  teknosa: 'Teknosa', vatan: 'Vatan', other: 'Diğer',
};

export function DealCard({ store }: { store: ProductStoreResponse }) {
  return (
    <TouchableOpacity
      onPress={() => router.push(`/product/${store.id}`)}
      activeOpacity={0.85}
    >
      <Card className="w-40">
        <View className="h-32 bg-surface items-center justify-center">
          <Text className="text-muted text-xs">{STORE_LABELS[store.store]}</Text>
        </View>
        <View className="p-3 gap-1">
          {store.discount_percent && <DiscountBadge percent={store.discount_percent} />}
          <PriceText value={store.current_price} size="md" />
          {store.original_price && (
            <PriceText value={store.original_price} size="sm" dimmed />
          )}
        </View>
      </Card>
    </TouchableOpacity>
  );
}
