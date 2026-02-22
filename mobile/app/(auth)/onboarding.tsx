import { useState } from 'react';
import { View, Text, ScrollView, Alert, ActivityIndicator, TouchableOpacity } from 'react-native';
import { router } from 'expo-router';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { productsApi } from '@/api/products';
import { useAuthStore } from '@/store/authStore';

export default function OnboardingScreen() {
  const [url, setUrl] = useState('');
  const [targetPrice, setTargetPrice] = useState('');
  const [loading, setLoading] = useState(false);
  const completeOnboarding = useAuthStore((s) => s.completeOnboarding);

  const handleSetAlarm = async () => {
    if (!url.trim()) {
      Alert.alert('Hata', 'Ürün linkini girin');
      return;
    }
    const price = parseFloat(targetPrice.replace(',', '.'));
    if (!targetPrice.trim() || isNaN(price) || price <= 0) {
      Alert.alert('Hata', 'Geçerli bir hedef fiyat girin');
      return;
    }

    setLoading(true);
    try {
      await productsApi.add(url.trim(), price);
      await completeOnboarding();
      router.replace('/(tabs)');
    } catch (e: any) {
      const detail = e.response?.data?.detail ?? 'Alarm kurulamadı. Linki kontrol et.';
      Alert.alert('Hata', typeof detail === 'string' ? detail : 'Alarm kurulamadı');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView
      className="flex-1 bg-background"
      contentContainerStyle={{ flexGrow: 1 }}
      keyboardShouldPersistTaps="handled"
    >
      <View className="flex-1 justify-center px-6 gap-10">
        {/* Header */}
        <View className="gap-3">
          <Text className="text-3xl font-bold text-white">İlk alarmını kur</Text>
          <Text className="text-muted text-base leading-6">
            Prial'ı kullanmaya başlamak için takip etmek istediğin ürünün linkini yapıştır
          </Text>
        </View>

        {/* Form */}
        <View className="gap-4">
          <Input
            label="Ürün Linki"
            value={url}
            onChangeText={setUrl}
            placeholder="https://trendyol.com/..."
            autoCapitalize="none"
            keyboardType="url"
          />
          <Input
            label="Hedef Fiyat (₺)"
            value={targetPrice}
            onChangeText={setTargetPrice}
            placeholder="örn. 1500"
            keyboardType="decimal-pad"
          />
          <Button onPress={handleSetAlarm} loading={loading}>
            Alarm Kur
          </Button>
        </View>
      </View>
    </ScrollView>
  );
}
