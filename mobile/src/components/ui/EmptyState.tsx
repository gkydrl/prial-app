import React from 'react';
import { View, Text } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '@/constants/colors';

interface EmptyStateProps {
  icon?: keyof typeof Ionicons.glyphMap;
  title: string;
  description?: string;
}

export function EmptyState({ icon = 'file-tray-outline', title, description }: EmptyStateProps) {
  return (
    <View className="flex-1 items-center justify-center py-20 gap-3">
      <Ionicons name={icon} size={56} color={Colors.muted} />
      <Text className="text-lg font-semibold text-white">{title}</Text>
      {description && <Text className="text-sm text-muted text-center px-8">{description}</Text>}
    </View>
  );
}
