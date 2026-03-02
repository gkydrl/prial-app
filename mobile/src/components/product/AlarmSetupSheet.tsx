import React, { useState, useEffect, useMemo } from 'react';
import { View, Text, Alert, Platform, Modal, Pressable, TouchableOpacity, ActivityIndicator } from 'react-native';
import Slider from '@react-native-community/slider';
import { Ionicons } from '@expo/vector-icons';
import { productsApi } from '@/api/products';

// @gorhom/bottom-sheet native-only — web'de require etme
const BottomSheetLib = Platform.OS !== 'web' ? require('@gorhom/bottom-sheet') : null;

const SHEET_BG = '#1E293B';
const BORDER = '#334155';
const GREEN = '#22C55E';
const MUTED = '#64748B';

interface AlarmSetupSheetProps {
  productId: string;
  storeUrl: string | null;       // POST /products/add için mağaza URL'si
  currentPrice: number | null;
  onSuccess?: () => void;
  sheetRef: React.RefObject<any>;
}

function fmt(price: number): string {
  return Math.round(price).toLocaleString('tr-TR') + ' ₺';
}

function sliderStep(currentPrice: number): number {
  if (currentPrice >= 50_000) return 5000;
  if (currentPrice >= 10_000) return 500;
  if (currentPrice >= 1_000) return 100;
  return 50;
}

export function AlarmSetupSheet({ productId, storeUrl, currentPrice, onSuccess, sheetRef }: AlarmSetupSheetProps) {
  const hasPrice = currentPrice != null && currentPrice > 0;

  const minPrice = useMemo(() => hasPrice ? Math.round(currentPrice * 0.5) : 0, [currentPrice]);
  const maxPrice = useMemo(() => hasPrice ? Math.round(currentPrice * 0.99) : 10000, [currentPrice]);
  const step = useMemo(() => hasPrice ? sliderStep(currentPrice) : 100, [currentPrice]);
  const defaultTarget = useMemo(() => hasPrice ? Math.round(currentPrice * 0.9 / step) * step : maxPrice, [currentPrice, step]);

  const [sliderValue, setSliderValue] = useState(defaultTarget);
  const [loading, setLoading] = useState(false);
  const [webVisible, setWebVisible] = useState(false);

  // currentPrice değişince slider sıfırla
  useEffect(() => {
    setSliderValue(defaultTarget);
  }, [defaultTarget]);

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

  const discountPercent = hasPrice
    ? Math.round((1 - sliderValue / currentPrice) * 100)
    : 0;

  const handleSetAlarm = async () => {
    if (!sliderValue || sliderValue <= 0) {
      Alert.alert('Hata', 'Geçerli bir hedef fiyat seçin');
      return;
    }
    if (!storeUrl) {
      Alert.alert('Hata', 'Ürün mağaza bilgisi bulunamadı');
      return;
    }
    setLoading(true);
    try {
      // POST /products/add — ürün zaten varsa direkt alarm oluşturur
      await productsApi.add(storeUrl, sliderValue);
      Alert.alert('Talep Oluşturuldu', 'Fiyat hedefe düşünce bildirim alacaksınız.');
      if (Platform.OS === 'web') {
        setWebVisible(false);
      } else {
        sheetRef.current?.close();
      }
      onSuccess?.();
    } catch (e: any) {
      Alert.alert('Hata', e.response?.data?.detail ?? 'Talep oluşturulamadı');
    } finally {
      setLoading(false);
    }
  };

  const formContent = (
    <View style={{ gap: 20 }}>
      {/* Başlık */}
      <Text style={{ color: '#FFFFFF', fontSize: 20, fontFamily: 'Inter_700Bold' }}>
        Talep Et
      </Text>

      {/* Seçilen fiyat göstergesi */}
      <View style={{ alignItems: 'center', gap: 4 }}>
        <Text style={{ color: '#FFFFFF', fontSize: 36, fontFamily: 'Inter_700Bold' }}>
          {fmt(sliderValue)}
        </Text>
        {hasPrice && discountPercent > 0 && (
          <View style={{
            flexDirection: 'row',
            alignItems: 'center',
            gap: 4,
            backgroundColor: `${GREEN}20`,
            borderRadius: 12,
            paddingHorizontal: 10,
            paddingVertical: 4,
          }}>
            <Ionicons name="trending-down" size={13} color={GREEN} />
            <Text style={{ color: GREEN, fontSize: 12, fontFamily: 'Inter_600SemiBold' }}>
              Güncel fiyattan %{discountPercent} daha ucuz
            </Text>
          </View>
        )}
        {hasPrice && discountPercent <= 0 && (
          <Text style={{ color: MUTED, fontSize: 12, fontFamily: 'Inter_400Regular' }}>
            Güncel fiyat: {fmt(currentPrice)}
          </Text>
        )}
      </View>

      {/* Slider */}
      {hasPrice && (
        <View style={{ gap: 6 }}>
          <Slider
            minimumValue={minPrice}
            maximumValue={maxPrice}
            value={sliderValue}
            onValueChange={(v) => setSliderValue(Math.round(v / step) * step)}
            step={step}
            minimumTrackTintColor={GREEN}
            maximumTrackTintColor={BORDER}
            thumbTintColor={GREEN}
            style={{ height: 40 }}
          />
          <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
            <Text style={{ color: MUTED, fontSize: 11, fontFamily: 'Inter_400Regular' }}>
              {fmt(minPrice)}
            </Text>
            <Text style={{ color: MUTED, fontSize: 11, fontFamily: 'Inter_400Regular' }}>
              {fmt(maxPrice)}
            </Text>
          </View>
        </View>
      )}

      {/* Talep Et butonu */}
      <TouchableOpacity
        onPress={handleSetAlarm}
        disabled={loading}
        activeOpacity={0.85}
        style={{
          backgroundColor: GREEN,
          borderRadius: 14,
          paddingVertical: 16,
          alignItems: 'center',
          flexDirection: 'row',
          justifyContent: 'center',
          gap: 8,
          opacity: loading ? 0.7 : 1,
        }}
      >
        {loading ? (
          <ActivityIndicator size="small" color="#fff" />
        ) : (
          <>
            <Ionicons name="pricetag-outline" size={18} color="#fff" />
            <Text style={{ color: '#FFFFFF', fontSize: 16, fontFamily: 'Inter_700Bold' }}>
              Talep Oluştur
            </Text>
          </>
        )}
      </TouchableOpacity>
    </View>
  );

  // Web: Modal overlay
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
              backgroundColor: SHEET_BG,
              borderTopLeftRadius: 20,
              borderTopRightRadius: 20,
              paddingHorizontal: 24,
              paddingTop: 12,
              paddingBottom: 40,
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
      snapPoints={['55%']}
      enablePanDownToClose
      backgroundStyle={{ backgroundColor: SHEET_BG }}
      handleIndicatorStyle={{ backgroundColor: BORDER }}
    >
      <BottomSheetView style={{ paddingHorizontal: 24, paddingTop: 8, paddingBottom: 40 }}>
        {formContent}
      </BottomSheetView>
    </BottomSheet>
  );
}
