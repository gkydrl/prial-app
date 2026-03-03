import { useState, useEffect, useMemo } from 'react';
import {
  View,
  Text,
  Modal,
  Pressable,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import Slider from '@react-native-community/slider';
import { Ionicons } from '@expo/vector-icons';
import { productsApi } from '@/api/products';
import { alarmsApi } from '@/api/alarms';
import { showAlert } from '@/store/alertStore';
import { useAlarmSheetStore, openAlarmSheet } from '@/store/alarmSheetStore';

const SHEET_BG = '#1E293B';
const BORDER = '#334155';
const BRAND = '#1D4ED8';
const GREEN = '#22C55E';
const MUTED = '#64748B';

function fmt(price: number): string {
  return Math.round(price).toLocaleString('tr-TR') + ' ₺';
}

function sliderStep(p: number): number {
  if (p >= 50_000) return 5000;
  if (p >= 10_000) return 500;
  if (p >= 1_000) return 100;
  return 50;
}

export function GlobalAlarmSheet() {
  const {
    visible,
    productId,
    storeUrl,
    currentPrice,
    existingAlarmId,
    existingTargetPrice,
    close,
  } = useAlarmSheetStore();

  const isUpdateMode = !!existingAlarmId;

  const hasPrice = currentPrice != null && currentPrice > 0;
  const step = useMemo(() => (hasPrice ? sliderStep(currentPrice) : 100), [currentPrice]);
  const minPrice = useMemo(() => (hasPrice ? Math.round(currentPrice * 0.5) : 0), [currentPrice]);
  const maxPrice = useMemo(() => (hasPrice ? Math.round(currentPrice * 0.99) : 10000), [currentPrice]);
  const defaultTarget = useMemo(() => {
    if (isUpdateMode && existingTargetPrice) return existingTargetPrice;
    return hasPrice ? Math.round((currentPrice * 0.9) / step) * step : maxPrice;
  }, [currentPrice, step, isUpdateMode, existingTargetPrice]);

  const [sliderValue, setSliderValue] = useState(defaultTarget);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setSliderValue(defaultTarget);
  }, [defaultTarget]);

  const discountPercent = hasPrice ? Math.round((1 - sliderValue / currentPrice) * 100) : 0;

  const handleSubmit = async () => {
    if (!sliderValue || sliderValue <= 0) {
      showAlert('Hata', 'Geçerli bir hedef fiyat seçin');
      return;
    }
    setLoading(true);
    try {
      if (isUpdateMode) {
        // Güncelleme modu
        await alarmsApi.update(existingAlarmId!, { target_price: sliderValue, status: 'active' });
        close();
        showAlert('Talep Güncellendi 🎉', 'Hedef fiyatınız güncellendi.');
      } else {
        // Yeni talep
        if (!storeUrl) {
          showAlert('Hata', 'Ürün mağaza bilgisi bulunamadı');
          return;
        }
        await productsApi.add(storeUrl, sliderValue);
        close();
        showAlert('Talep Oluşturuldu 🎉', 'Fiyat hedefe ulaşınca sizi bilgilendireceğiz.');
      }
    } catch (e: any) {
      const detail = e.response?.data?.detail;
      if (detail?.code === 'ALARM_EXISTS') {
        // Mevcut talebi güncelleme modunda sheet'i yeniden aç
        close();
        setTimeout(() => {
          openAlarmSheet({
            productId,
            storeUrl,
            currentPrice,
            existingAlarmId: detail.alarm_id,
            existingTargetPrice: detail.target_price,
          });
        }, 300);
        return;
      }
      showAlert('Hata', typeof detail === 'string' ? detail : 'İşlem tamamlanamadı');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={close}>
      <Pressable
        style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.55)', justifyContent: 'flex-end' }}
        onPress={close}
      >
        <Pressable
          style={{
            backgroundColor: SHEET_BG,
            borderTopLeftRadius: 20,
            borderTopRightRadius: 20,
            paddingHorizontal: 24,
            paddingTop: 12,
            paddingBottom: 48,
          }}
          onPress={() => {}}
        >
          {/* Handle */}
          <View
            style={{
              width: 40,
              height: 4,
              backgroundColor: BORDER,
              borderRadius: 2,
              alignSelf: 'center',
              marginBottom: 20,
            }}
          />

          <View style={{ gap: 20 }}>
            {/* Başlık */}
            <View style={{ gap: 4 }}>
              <Text style={{ color: '#FFFFFF', fontSize: 20, fontFamily: 'Inter_700Bold' }}>
                {isUpdateMode ? 'Talebi Güncelle' : 'Talep Et'}
              </Text>
              {isUpdateMode && existingTargetPrice && (
                <Text style={{ color: MUTED, fontSize: 13, fontFamily: 'Inter_400Regular' }}>
                  Mevcut hedefiniz: {fmt(existingTargetPrice)}
                </Text>
              )}
            </View>

            {/* Seçilen fiyat */}
            <View style={{ alignItems: 'center', gap: 4 }}>
              <Text style={{ color: '#FFFFFF', fontSize: 36, fontFamily: 'Inter_700Bold' }}>
                {fmt(sliderValue)}
              </Text>
              {hasPrice && discountPercent > 0 && (
                <View
                  style={{
                    flexDirection: 'row',
                    alignItems: 'center',
                    gap: 4,
                    backgroundColor: `${GREEN}20`,
                    borderRadius: 12,
                    paddingHorizontal: 10,
                    paddingVertical: 4,
                  }}
                >
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
                  minimumTrackTintColor={BRAND}
                  maximumTrackTintColor={BORDER}
                  thumbTintColor={BRAND}
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

            {/* Buton */}
            <TouchableOpacity
              onPress={handleSubmit}
              disabled={loading}
              activeOpacity={0.85}
              style={{
                backgroundColor: BRAND,
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
                  <Ionicons
                    name={isUpdateMode ? 'checkmark-circle-outline' : 'pricetag-outline'}
                    size={18}
                    color="#fff"
                  />
                  <Text style={{ color: '#FFFFFF', fontSize: 16, fontFamily: 'Inter_700Bold' }}>
                    {isUpdateMode ? 'Talebi Güncelle' : 'Talep Oluştur'}
                  </Text>
                </>
              )}
            </TouchableOpacity>
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}
