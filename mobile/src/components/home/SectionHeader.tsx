import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';

interface SectionHeaderProps {
  title: string;
  onSeeAll?: () => void;
}

export function SectionHeader({ title, onSeeAll }: SectionHeaderProps) {
  return (
    <View className="flex-row items-center justify-between px-4 mb-3">
      <Text className="text-white text-lg font-bold">{title}</Text>
      {onSeeAll && (
        <TouchableOpacity onPress={onSeeAll}>
          <Text className="text-brand text-sm">Tümünü Gör</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}
