import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { Linking } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { PriceText } from '@/components/ui/PriceText';
import { DiscountBadge } from '@/components/ui/Badge';
import { Colors } from '@/constants/colors';
import type { ProductStoreResponse } from '@/types/api';

const STORE_LABELS: Record<string, string> = {
  trendyol: 'Trendyol',
  hepsiburada: 'Hepsiburada',
  amazon: 'Amazon',
  n11: 'N11',
  ciceksepeti: 'Çiçeksepeti',
  mediamarkt: 'MediaMarkt',
  teknosa: 'Teknosa',
  vatan: 'Vatan',
  other: 'Diğer',
};

export function StoreRow({ store }: { store: ProductStoreResponse }) {
  return (
    <View className="flex-row items-center justify-between py-3 border-b border-border">
      <View className="gap-1">
        <Text className="text-white font-medium">{STORE_LABELS[store.store] ?? store.store}</Text>
        <View className="flex-row items-center gap-2">
          <PriceText value={store.current_price} size="sm" />
          {store.discount_percent && <DiscountBadge percent={store.discount_percent} />}
        </View>
        {!store.in_stock && (
          <Text className="text-xs text-warning">Stok dışı</Text>
        )}
      </View>
      <TouchableOpacity
        className="flex-row items-center gap-1 bg-brand/20 rounded-lg px-3 py-2"
        onPress={() => Linking.openURL(store.url)}
      >
        <Text className="text-brand text-sm font-medium">Git</Text>
        <Ionicons name="open-outline" size={14} color={Colors.brand} />
      </TouchableOpacity>
    </View>
  );
}
