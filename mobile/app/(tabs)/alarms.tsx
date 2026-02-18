import { View, FlatList, RefreshControl, TouchableOpacity, Text, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useState } from 'react';
import { AlarmCard } from '@/components/alarm/AlarmCard';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useAlarms } from '@/hooks/useAlarms';
import type { AlarmStatus } from '@/types/api';

const FILTERS: { label: string; value: AlarmStatus | undefined }[] = [
  { label: 'Tümü', value: undefined },
  { label: 'Aktif', value: 'active' },
  { label: 'Tetiklendi', value: 'triggered' },
  { label: 'Duraklatıldı', value: 'paused' },
];

export default function AlarmsScreen() {
  const [filter, setFilter] = useState<AlarmStatus | undefined>(undefined);
  const { alarms, isLoading, deleteAlarm, refresh } = useAlarms(filter);

  const handleDelete = (id: string) => {
    Alert.alert('Alarmı Sil', 'Bu alarmı silmek istediğinize emin misiniz?', [
      { text: 'Vazgeç', style: 'cancel' },
      { text: 'Sil', style: 'destructive', onPress: () => deleteAlarm(id) },
    ]);
  };

  return (
    <SafeAreaView className="flex-1 bg-background" edges={['top']}>
      <View className="flex-1">
        {/* Header */}
        <View className="px-4 pt-4 pb-3">
          <Text className="text-2xl font-bold text-white">Alarmlarım</Text>
        </View>

        {/* Filtreler */}
        <View className="flex-row px-4 gap-2 mb-3">
          {FILTERS.map((f) => (
            <TouchableOpacity
              key={String(f.value)}
              className={`px-3 py-1.5 rounded-full border ${filter === f.value ? 'bg-brand border-brand' : 'border-border'}`}
              onPress={() => setFilter(f.value)}
            >
              <Text className={`text-sm font-medium ${filter === f.value ? 'text-white' : 'text-muted'}`}>
                {f.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Liste */}
        {isLoading && alarms.length === 0 ? (
          <LoadingSpinner full />
        ) : (
          <FlatList
            data={alarms}
            keyExtractor={(item) => item.id}
            contentContainerStyle={{ paddingHorizontal: 16, gap: 10, paddingBottom: 20 }}
            showsVerticalScrollIndicator={false}
            refreshControl={<RefreshControl refreshing={isLoading} onRefresh={refresh} tintColor="#6C47FF" />}
            renderItem={({ item }) => (
              <AlarmCard
                alarm={item}
                onEdit={() => handleDelete(item.id)}
              />
            )}
            ListEmptyComponent={
              <EmptyState
                icon="notifications-off-outline"
                title="Alarm bulunamadı"
                description="Ürün ekleyerek fiyat alarmı kurabilirsiniz"
              />
            }
          />
        )}
      </View>
    </SafeAreaView>
  );
}
