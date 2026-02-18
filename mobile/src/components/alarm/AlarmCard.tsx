import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { Image } from 'expo-image';
import { router } from 'expo-router';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { PriceText } from '@/components/ui/PriceText';
import { formatDate } from '@/utils/date';
import type { AlarmResponse, AlarmStatus } from '@/types/api';

const STATUS_CONFIG: Record<AlarmStatus, { label: string; color: 'brand' | 'success' | 'muted' | 'danger' }> = {
  active: { label: 'Aktif', color: 'brand' },
  triggered: { label: 'Tetiklendi', color: 'success' },
  paused: { label: 'Duraklat', color: 'muted' },
  deleted: { label: 'Silindi', color: 'danger' },
};

interface AlarmCardProps {
  alarm: AlarmResponse;
  onEdit?: () => void;
}

export function AlarmCard({ alarm, onEdit }: AlarmCardProps) {
  const { label, color } = STATUS_CONFIG[alarm.status] ?? STATUS_CONFIG.active;
  const store = alarm.product_store;
  const product = alarm.product;

  return (
    <Card className="flex-row p-3 gap-3">
      <TouchableOpacity onPress={() => router.push(`/product/${product.id}`)}>
        <Image
          source={{ uri: product.image_url ?? undefined }}
          style={{ width: 72, height: 72, borderRadius: 10 }}
          contentFit="cover"
          placeholder={{ blurhash: 'L6PZfSi_.AyE_3t7t7R**0o#DgR4' }}
        />
      </TouchableOpacity>
      <View className="flex-1 gap-1">
        <View className="flex-row items-start justify-between">
          <Text className="text-white text-sm font-medium flex-1 pr-2" numberOfLines={2}>
            {product.title}
          </Text>
          <Badge label={label} color={color} />
        </View>
        <View className="flex-row items-center gap-3">
          <View>
            <Text className="text-xs text-muted">Hedef</Text>
            <PriceText value={alarm.target_price} size="sm" />
          </View>
          {store?.current_price && (
            <View>
              <Text className="text-xs text-muted">Güncel</Text>
              <PriceText value={store.current_price} size="sm" />
            </View>
          )}
        </View>
        <View className="flex-row items-center justify-between">
          <Text className="text-xs text-muted">{formatDate(alarm.created_at)}</Text>
          {onEdit && (
            <TouchableOpacity onPress={onEdit}>
              <Text className="text-xs text-brand">Düzenle</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>
    </Card>
  );
}
