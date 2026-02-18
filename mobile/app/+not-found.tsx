import { View, Text } from 'react-native';
import { router } from 'expo-router';
import { Button } from '@/components/ui/Button';

export default function NotFoundScreen() {
  return (
    <View className="flex-1 bg-background items-center justify-center px-8 gap-6">
      <Text className="text-6xl">🔍</Text>
      <Text className="text-white text-2xl font-bold text-center">Sayfa Bulunamadı</Text>
      <Text className="text-muted text-sm text-center">
        Aradığınız sayfa mevcut değil veya kaldırılmış
      </Text>
      <Button onPress={() => router.replace('/(tabs)')}>Ana Sayfaya Dön</Button>
    </View>
  );
}
