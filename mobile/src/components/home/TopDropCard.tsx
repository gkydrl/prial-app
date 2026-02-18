import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { Card } from '@/components/ui/Card';
import { PriceText } from '@/components/ui/PriceText';
import { Colors } from '@/constants/colors';
import { Ionicons } from '@expo/vector-icons';
import type { TopDropResponse } from '@/types/api';

export function TopDropCard({ item }: { item: TopDropResponse }) {
  const { store, price_24h_ago, price_now, drop_percent } = item;

  return (
    <Card className="w-52 p-3 gap-2">
      <View className="flex-row items-center justify-between">
        <Text className="text-white text-sm font-medium flex-1" numberOfLines={1}>
          {store.store.charAt(0).toUpperCase() + store.store.slice(1)}
        </Text>
        <View className="flex-row items-center gap-1">
          <Ionicons name="trending-down" size={16} color={Colors.success} />
          <Text className="text-success text-sm font-bold">%{drop_percent.toFixed(1)}</Text>
        </View>
      </View>
      <View className="flex-row items-center gap-2">
        <PriceText value={price_now} size="md" />
        <PriceText value={price_24h_ago} size="sm" dimmed />
      </View>
      <Text className="text-xs text-muted" numberOfLines={1}>{store.url}</Text>
    </Card>
  );
}
