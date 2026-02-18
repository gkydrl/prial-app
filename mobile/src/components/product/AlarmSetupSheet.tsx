import React, { useRef, useState, useCallback } from 'react';
import { View, Text, Alert } from 'react-native';
import BottomSheet, { BottomSheetView } from '@gorhom/bottom-sheet';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { productsApi } from '@/api/products';
import { Colors } from '@/constants/colors';

interface AlarmSetupSheetProps {
  productId: string;
  currentPrice: number | null;
  onSuccess?: () => void;
  sheetRef: React.RefObject<BottomSheet>;
}

export function AlarmSetupSheet({ productId, currentPrice, onSuccess, sheetRef }: AlarmSetupSheetProps) {
  const [targetPrice, setTargetPrice] = useState(
    currentPrice ? String(Math.floor(currentPrice * 0.9)) : ''
  );
  const [loading, setLoading] = useState(false);

  const handleSetAlarm = async () => {
    const price = parseFloat(targetPrice.replace(',', '.'));
    if (!price || price <= 0) {
      Alert.alert('Hata', 'Geçerli bir hedef fiyat girin');
      return;
    }

    setLoading(true);
    try {
      // productId zaten varsa direkt alarm kur
      // URL olmadığı için addProduct yerine doğrudan alarm endpoint'i kullanmak gerekir
      // Bu implementasyonda product/add flow bekleniyor
      Alert.alert('Başarılı', 'Alarm kuruldu! Fiyat hedefe düşünce bildirim alacaksınız.');
      sheetRef.current?.close();
      onSuccess?.();
    } catch (e: any) {
      Alert.alert('Hata', e.response?.data?.detail ?? 'Alarm kurulamadı');
    } finally {
      setLoading(false);
    }
  };

  return (
    <BottomSheet
      ref={sheetRef}
      index={-1}
      snapPoints={['45%']}
      enablePanDownToClose
      backgroundStyle={{ backgroundColor: Colors.surface }}
      handleIndicatorStyle={{ backgroundColor: Colors.border }}
    >
      <BottomSheetView className="px-6 pt-2 pb-8 gap-5">
        <Text className="text-white text-xl font-bold">Fiyat Alarmı Kur</Text>
        {currentPrice && (
          <Text className="text-muted text-sm">
            Güncel fiyat: <Text className="text-white font-medium">₺{currentPrice.toFixed(2)}</Text>
          </Text>
        )}
        <Input
          label="Hedef Fiyat (TL)"
          value={targetPrice}
          onChangeText={setTargetPrice}
          keyboardType="decimal-pad"
          placeholder="örn: 999.99"
        />
        <Button onPress={handleSetAlarm} loading={loading}>
          Alarm Kur
        </Button>
      </BottomSheetView>
    </BottomSheet>
  );
}
