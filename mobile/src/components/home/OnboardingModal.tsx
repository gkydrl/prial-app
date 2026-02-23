import { useState, useEffect, useRef } from 'react';
import {
  Modal,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  Alert,
  ActivityIndicator,
} from 'react-native';
import Slider from '@react-native-community/slider';
import { router } from 'expo-router';
import { productsApi } from '@/api/products';
import { useAuthStore } from '@/store/authStore';
import { fetchProductPreview, type PreviewResult } from '@/utils/productPreview';

interface Props {
  visible: boolean;
  onDismiss: () => void;
}

function formatPrice(price: number): string {
  return price.toLocaleString('tr-TR', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

export function OnboardingModal({ visible, onDismiss }: Props) {
  const [url, setUrl] = useState('');
  const [previewing, setPreviewing] = useState(false);
  const [previewFailed, setPreviewFailed] = useState(false);
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [sliderValue, setSliderValue] = useState(0);
  const [manualPrice, setManualPrice] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const completeOnboarding = useAuthStore((s) => s.completeOnboarding);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);

    setPreview(null);
    setPreviewFailed(false);

    const trimmed = url.trim();
    if (!trimmed || trimmed.length < 10) return;

    debounceRef.current = setTimeout(async () => {
      setPreviewing(true);
      try {
        const result = await fetchProductPreview(trimmed);
        setPreview(result);
        setSliderValue(Math.round(result.current_price * 0.7));
        setPreviewFailed(false);
      } catch {
        setPreview(null);
        setPreviewFailed(true);
      } finally {
        setPreviewing(false);
      }
    }, 800);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [url]);

  const handleSkip = async () => {
    await completeOnboarding();
    onDismiss();
  };

  const targetPrice = preview
    ? sliderValue
    : parseFloat(manualPrice.replace(',', '.'));

  const canSubmit =
    url.trim().length > 10 &&
    !previewing &&
    (preview ? sliderValue > 0 : (!isNaN(targetPrice) && targetPrice > 0));

  const handleSetAlarm = async () => {
    if (!canSubmit) return;

    setSubmitting(true);
    try {
      await productsApi.add(url.trim(), targetPrice);
      await completeOnboarding();
      onDismiss();
      router.push('/(tabs)/alarms');
    } catch (e: any) {
      const detail = e.response?.data?.detail ?? 'Alarm kurulamadı. Linki kontrol et.';
      Alert.alert('Hata', typeof detail === 'string' ? detail : 'Alarm kurulamadı');
    } finally {
      setSubmitting(false);
    }
  };

  const minPrice = preview ? Math.round(preview.current_price * 0.3) : 0;
  const maxPrice = preview ? Math.round(preview.current_price * 0.95) : 0;

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      statusBarTranslucent
      onRequestClose={handleSkip}
    >
      <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' }}>
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
          <View
            style={{
              backgroundColor: '#1A1A1A',
              borderTopLeftRadius: 24,
              borderTopRightRadius: 24,
              padding: 24,
              paddingBottom: 44,
              gap: 20,
            }}
          >
            {/* Handle */}
            <View
              style={{
                width: 40,
                height: 4,
                backgroundColor: '#3A3A3A',
                borderRadius: 2,
                alignSelf: 'center',
              }}
            />

            {/* Header */}
            <View style={{ gap: 6 }}>
              <Text style={{ color: '#FFFFFF', fontSize: 22, fontWeight: '700' }}>
                İlk alarmını kur
              </Text>
              <Text style={{ color: '#9CA3AF', fontSize: 14, lineHeight: 20 }}>
                Takip etmek istediğin ürünün linkini yapıştır
              </Text>
            </View>

            {/* URL Input */}
            <View style={{ gap: 6 }}>
              <Text style={{ color: '#9CA3AF', fontSize: 13, fontWeight: '500' }}>
                Ürün Linki
              </Text>
              <View style={{ position: 'relative' }}>
                <TextInput
                  value={url}
                  onChangeText={setUrl}
                  placeholder="https://trendyol.com/..."
                  placeholderTextColor="#4B5563"
                  autoCapitalize="none"
                  keyboardType="url"
                  style={{
                    backgroundColor: '#262626',
                    borderRadius: 12,
                    paddingHorizontal: 16,
                    paddingRight: previewing ? 44 : 16,
                    paddingVertical: 14,
                    color: '#FFFFFF',
                    fontSize: 15,
                    borderWidth: 1,
                    borderColor: previewing ? '#6C47FF' : '#333333',
                  }}
                />
                {previewing && (
                  <View
                    style={{
                      position: 'absolute',
                      right: 14,
                      top: 0,
                      bottom: 0,
                      justifyContent: 'center',
                    }}
                  >
                    <ActivityIndicator size="small" color="#6C47FF" />
                  </View>
                )}
              </View>
            </View>

            {/* Preview Card */}
            {preview && !previewing && (
              <View
                style={{
                  backgroundColor: '#262626',
                  borderRadius: 14,
                  padding: 16,
                  gap: 4,
                  borderWidth: 1,
                  borderColor: '#333333',
                }}
              >
                <Text
                  style={{ color: '#FFFFFF', fontSize: 14, fontWeight: '600' }}
                  numberOfLines={2}
                >
                  {preview.title}
                </Text>
                <Text style={{ color: '#9CA3AF', fontSize: 13 }}>
                  Mevcut fiyat:{' '}
                  <Text style={{ color: '#6C47FF', fontWeight: '700' }}>
                    {formatPrice(preview.current_price)} ₺
                  </Text>
                </Text>
              </View>
            )}

            {/* Slider (preview başarılıysa) */}
            {preview && !previewing && (
              <View style={{ gap: 8 }}>
                <Slider
                  minimumValue={minPrice}
                  maximumValue={maxPrice}
                  step={1}
                  value={sliderValue}
                  onValueChange={(v) => setSliderValue(Math.round(v))}
                  minimumTrackTintColor="#6C47FF"
                  maximumTrackTintColor="#333333"
                  thumbTintColor="#6C47FF"
                  style={{ width: '100%', height: 40 }}
                />
                <Text style={{ color: '#9CA3AF', fontSize: 14, textAlign: 'center' }}>
                  <Text style={{ color: '#FFFFFF', fontWeight: '700' }}>
                    {formatPrice(sliderValue)} ₺
                  </Text>
                  {' '}altına düşünce bildir
                </Text>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                  <Text style={{ color: '#6B7280', fontSize: 12 }}>{formatPrice(minPrice)} ₺</Text>
                  <Text style={{ color: '#6B7280', fontSize: 12 }}>{formatPrice(maxPrice)} ₺</Text>
                </View>
              </View>
            )}

            {/* Manuel fiyat (preview başarısızsa fallback) */}
            {previewFailed && !previewing && (
              <View style={{ gap: 6 }}>
                <Text style={{ color: '#9CA3AF', fontSize: 13, fontWeight: '500' }}>
                  Hedef Fiyat (₺)
                </Text>
                <TextInput
                  value={manualPrice}
                  onChangeText={setManualPrice}
                  placeholder="örn. 1500"
                  placeholderTextColor="#4B5563"
                  keyboardType="decimal-pad"
                  style={{
                    backgroundColor: '#262626',
                    borderRadius: 12,
                    paddingHorizontal: 16,
                    paddingVertical: 14,
                    color: '#FFFFFF',
                    fontSize: 15,
                    borderWidth: 1,
                    borderColor: '#333333',
                  }}
                />
              </View>
            )}

            {/* Alarm Kur button */}
            <TouchableOpacity
              onPress={handleSetAlarm}
              disabled={submitting || !canSubmit}
              style={{
                backgroundColor: canSubmit ? '#6C47FF' : '#333333',
                borderRadius: 14,
                paddingVertical: 16,
                alignItems: 'center',
              }}
            >
              {submitting ? (
                <ActivityIndicator color="#FFFFFF" />
              ) : (
                <Text
                  style={{
                    color: canSubmit ? '#FFFFFF' : '#6B7280',
                    fontSize: 16,
                    fontWeight: '700',
                  }}
                >
                  Alarm Kur
                </Text>
              )}
            </TouchableOpacity>

            {/* Skip */}
            <TouchableOpacity onPress={handleSkip} style={{ alignItems: 'center' }}>
              <Text style={{ color: '#6B7280', fontSize: 14 }}>Şimdi değil, atla</Text>
            </TouchableOpacity>
          </View>
        </KeyboardAvoidingView>
      </View>
    </Modal>
  );
}
