import React from 'react';
import { View, Text } from 'react-native';

interface BadgeProps {
  label: string;
  color?: 'brand' | 'success' | 'danger' | 'warning' | 'muted';
}

const colorClasses: Record<string, string> = {
  brand: 'bg-brand/20 text-brand',
  success: 'bg-success/20 text-success',
  danger: 'bg-danger/20 text-danger',
  warning: 'bg-warning/20 text-warning',
  muted: 'bg-gray-500/20 text-muted',
};

export function Badge({ label, color = 'brand' }: BadgeProps) {
  return (
    <View className={`rounded-full px-2.5 py-0.5 self-start ${colorClasses[color].split(' ')[0]}`}>
      <Text className={`text-xs font-semibold ${colorClasses[color].split(' ')[1]}`}>{label}</Text>
    </View>
  );
}

export function DiscountBadge({ percent }: { percent: number }) {
  return <Badge label={`-%${percent}`} color="danger" />;
}
