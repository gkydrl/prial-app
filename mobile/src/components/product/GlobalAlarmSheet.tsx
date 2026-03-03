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
import { useAlarmSheetStore } from '@/store/alarmSheetStore';

const SHEET_BG = '#1E293B';
const BORDER = '#334155';
const BRAND = '#6C47FF';
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
  const { visible, productId, storeUrl, currentPrice, close } = useAlarmSheetStore();

  const hasPrice = currentPrice != null && currentPrice > 0;
  const step = useMemo(() => (hasPrice ? sliderStep(currentPrice) : 100), [currentPrice]);
  const minPrice = useMemo(() => (hasPrice ? Math.round(currentPrice * 0.5) : 0), [currentPrice]);
  const maxPrice = useMemo(() => (hasPrice ? Math.round(currentPrice * 0.99) : 10000), [currentPrice]);
  const defaultTarget = useMemo(
    () => (hasPrice ? Math.round((currentPrice * 0.9) / step) * step : maxPrice),
    [currentPrice, step]
  );

  const [sliderValue, setSliderValue] = useState(defaultTarget);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setSliderValue(defaultTarget);
  }, [defaultTarget]);

  const discountPercent = hasPrice ? Math.round((1 - sliderValue / currentPrice) * 100) : 0;

  const handleSetAlarm = async () => {
    if (!sliderValue || sliderValue <= 0) {
      showAlert('Hata', 'Geçerli bir hedef fiyat seçin');
      return;
    }
    if (!storeUrl) {
      showAlert('Hata', 'Ürün mağaza bilgisi bulunamadı');
      return;
    }
    setLoading(true);
    try {
      await productsApi.add(storeUrl, sliderValue);
      close();
      showAlert('Talep Oluşturuldu 🎉', 'Fiyat hedefe ulaşınca sizi bilgilendireceğiz.');
    } catch (e: any) {
      const detail = e.response?.data?.detail;
      if (detail?.code === 'ALARM_EXISTS') {
        const existing = Math.round(detail.target_price).toLocaleString('tr-TR') + ' ₺';
        const newPrice = Math.round(sliderValue).toLocaleString('tr-TR') + ' ₺';
        close();
        showAlert(
          'Zaten Bir Talebiniz Var',
          `Bu ürün için ${existing} hedef fiyatlı bir talebiniz mevcut. ${newPrice} olarak güncellemek ister misiniz?`,
          [
            { text: 'Vazgeç', style: 'cancel' },
            {
              text: 'Güncelle',
              onPress: async () => {
                try {
                  await alarmsApi.update(detail.alarm_id, { target_price: sliderValue, status: 'active' });
                  showAlert('Talep Güncellendi 🎉', 'Hedef fiyatınız güncellendi.');
                } catch {
                  showAlert('Hata', 'Talep güncellenemedi.');
                }
              },
            },
          ]
        );
        return;
      }
      showAlert('Hata', detail ?? 'Talep oluşturulamadı');
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
            <Text style={{ color: '#FFFFFF', fontSize: 20, fontFamily: 'Inter_700Bold' }}>
              Talep Et
            </Text>

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
              onPress={handleSetAlarm}
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
                  <Ionicons name="pricetag-outline" size={18} color="#fff" />
                  <Text style={{ color: '#FFFFFF', fontSize: 16, fontFamily: 'Inter_700Bold' }}>
                    Talep Oluştur
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
