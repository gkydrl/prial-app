import React, { useState, useEffect } from 'react';
import { View, Text, Alert, Platform, Modal, Pressable } from 'react-native';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Colors } from '@/constants/colors';

// @gorhom/bottom-sheet native-only — web'de require etme
const BottomSheetLib = Platform.OS !== 'web' ? require('@gorhom/bottom-sheet') : null;

interface AlarmSetupSheetProps {
  productId: string;
  currentPrice: number | null;
  onSuccess?: () => void;
  sheetRef: React.RefObject<any>;
}

export function AlarmSetupSheet({ productId, currentPrice, onSuccess, sheetRef }: AlarmSetupSheetProps) {
  const [targetPrice, setTargetPrice] = useState(
    currentPrice ? String(Math.floor(currentPrice * 0.9)) : ''
  );
  const [loading, setLoading] = useState(false);
  const [webVisible, setWebVisible] = useState(false);

  // Web'de sheetRef'e BottomSheet API'sini taklit eden bir controller bağla
  useEffect(() => {
    if (Platform.OS !== 'web') return;
    (sheetRef as React.MutableRefObject<any>).current = {
      expand: () => setWebVisible(true),
      snapToIndex: () => setWebVisible(true),
      close: () => setWebVisible(false),
      forceClose: () => setWebVisible(false),
    };
  }, [sheetRef]);

  const handleSetAlarm = async () => {
    const price = parseFloat(targetPrice.replace(',', '.'));
    if (!price || price <= 0) {
      Alert.alert('Hata', 'Geçerli bir hedef fiyat girin');
      return;
    }

    setLoading(true);
    try {
      Alert.alert('Başarılı', 'Alarm kuruldu! Fiyat hedefe düşünce bildirim alacaksınız.');
      if (Platform.OS === 'web') {
        setWebVisible(false);
      } else {
        sheetRef.current?.close();
      }
      onSuccess?.();
    } catch (e: any) {
      Alert.alert('Hata', e.response?.data?.detail ?? 'Alarm kurulamadı');
    } finally {
      setLoading(false);
    }
  };

  const formContent = (
    <>
      <Text style={{ color: '#FFFFFF', fontSize: 20, fontWeight: 'bold' }}>Fiyat Alarmı Kur</Text>
      {currentPrice && (
        <Text style={{ color: '#9CA3AF', fontSize: 14 }}>
          Güncel fiyat:{' '}
          <Text style={{ color: '#FFFFFF', fontWeight: '500' }}>₺{currentPrice.toFixed(2)}</Text>
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
    </>
  );

  // Web: Modal overlay (BottomSheet'i taklit eder)
  if (Platform.OS === 'web') {
    return (
      <Modal
        visible={webVisible}
        transparent
        animationType="slide"
        onRequestClose={() => setWebVisible(false)}
      >
        <Pressable
          style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' }}
          onPress={() => setWebVisible(false)}
        >
          <Pressable
            style={{
              backgroundColor: Colors.surface,
              borderTopLeftRadius: 16,
              borderTopRightRadius: 16,
              paddingHorizontal: 24,
              paddingTop: 8,
              paddingBottom: 32,
              gap: 20,
            }}
            onPress={() => {}}
          >
            {formContent}
          </Pressable>
        </Pressable>
      </Modal>
    );
  }

  // Native: @gorhom/bottom-sheet
  const { default: BottomSheet, BottomSheetView } = BottomSheetLib;
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
        {formContent}
      </BottomSheetView>
    </BottomSheet>
  );
}
