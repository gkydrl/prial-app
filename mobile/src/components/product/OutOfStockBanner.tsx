import React from 'react';
import { View, Text } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '@/constants/colors';

export function OutOfStockBanner() {
  return (
    <View className="flex-row items-center gap-2 bg-warning/10 border border-warning/30 rounded-xl px-4 py-3 mx-4 mb-3">
      <Ionicons name="alert-circle-outline" size={18} color={Colors.warning} />
      <Text className="text-warning text-sm font-medium">Bu ürün şu an stok dışı</Text>
    </View>
  );
}
